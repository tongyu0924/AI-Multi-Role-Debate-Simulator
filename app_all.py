from flask import Flask, request, jsonify, send_from_directory
from transformers import GPTNeoForCausalLM, GPT2Tokenizer
from openai import OpenAI
import torch
import os
import re


# Set OpenAI API key
# os.environ["OPENAI_API_KEY"] = "OPENAI_API_KEY"

model_name = "EleutherAI/gpt-neo-125M"
tokenizer = GPT2Tokenizer.from_pretrained(model_name)
local_model = GPTNeoForCausalLM.from_pretrained(model_name)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
local_model.to(device)

openai_api_key = os.environ.get("OPENAI_API_KEY", "")
client = OpenAI(api_key=openai_api_key)

current_model = "openai"
current_mode = "debate"
long_term_memory = []
verdict_memory = []
debate_rounds = 0

class DebateAgent:
    def __init__(self, role_name, instruction, model="openai", tokenizer=None, model_instance=None):
        self.role = role_name
        self.instruction = instruction
        self.model_type = model
        self.tokenizer = tokenizer
        self.model = model_instance
        self.history = []

    def observe(self, topic, context):
        # Smart Context Management: only recent context, excluding self
        recent_lines = long_term_memory[-4:]
        others = "\n".join(line for line in recent_lines if not line.startswith(self.role + ":"))

        full_context = others
        if self.role == "Verdict" and verdict_memory:
            full_context += "\n\n[Additional Notes for Verdict Agent]\n" + "\n".join(verdict_memory)

        return {
            "role": self.role,
            # Team Coordination: encourage interaction with others
            "instruction": self.instruction + " Try to respond to or build on others' remarks if relevant.",
            "topic": topic,
            "context": full_context
        }

    def decide_action(self, obs, client=None):
        if self.model_type == "openai":
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"You are {obs['role']}. Task: {obs['instruction']}. Topic: '{obs['topic']}'. Think internally before answering. Limit to 80 words."
                    },
                    {
                        "role": "user",
                        "content": f"Conversation so far:\n\n{obs['context']}\n\nNow reply as {obs['role']}:"
                    }
                ]
            )
            return response.choices[0].message.content.strip()
        else:
            prompt = obs["context"] + f"\n{obs['role']}:"
            input_ids = self.tokenizer.encode(prompt, return_tensors="pt", truncation=True, max_length=800)
            output = self.model.generate(
                input_ids.to(device),
                max_new_tokens=200,
                pad_token_id=self.tokenizer.eos_token_id,
                no_repeat_ngram_size=3,
                repetition_penalty=1.2,
                do_sample=True,
                temperature=0.8,
                top_k=50,
                top_p=0.95
            )
            decoded = self.tokenizer.decode(output[0], skip_special_tokens=True)
            return re.split(r'\n(?:Pro|Con|Expert|Observer|Verdict):', decoded)[0].strip()

    def act(self, action):
        self.history.append(action)
        long_term_memory.append(f"{self.role}: {action}")
        if self.role != "Verdict":
            verdict_memory.append(f"{self.role}: {action}")
        return action

    def step(self, topic, context, client=None):
        obs = self.observe(topic, context)
        action = self.decide_action(obs, client)
        return self.act(action)

class DebateManager:
    def __init__(self, agents, topic="Artificial Intelligence"):
        self.agents = agents
        self.topic = topic
        self.turn = 0
        self.rounds = 0

    def get_context(self):
        return "\n".join(long_term_memory)

    def next_turn(self, client=None):
        global debate_rounds

        total_turns = debate_rounds * 4  # 4 main agents

        # If all main turns are finished, let Verdict speak once
        if self.rounds >= total_turns:
            verdict_agent = next(a for a in self.agents if a.role == "Verdict")
            if not verdict_agent.history:  # Verdict only speaks once
                context = self.get_context()
                reply = verdict_agent.step(self.topic, context, client)
                return {"role": verdict_agent.role, "reply": reply}
            else:
                return {"role": "", "reply": ""}  # Debate truly ended

        # Get the current agent (skip Verdict)
        current_agent = self.agents[self.turn]
        if current_agent.role == "Verdict":
            self.turn = (self.turn + 1) % len(self.agents)
            current_agent = self.agents[self.turn]
            
        # Perform action
        context = self.get_context()
        reply = current_agent.step(self.topic, context, client)

        # Advance turn and round
        self.turn = (self.turn + 1) % len(self.agents)
        
        if self.rounds >= total_turns:
            self.turn = 4
            current_agent = self.agents[self.turn]
         
        self.rounds += 1

        return {"role": current_agent.role, "reply": reply}

    def reset(self):
        for agent in self.agents:
            agent.history = []
        long_term_memory.clear()
        verdict_memory.clear()
        self.turn = 0
        self.rounds = 0

agent_instructions = {
    "Pro": "Argue in favor of the topic, presenting supporting evidence and reasoning.",
    "Con": "Argue against the topic, highlighting risks, flaws, or counterexamples.",
    "Expert": "Offer neutral, technical, or factual insights to deepen the discussion without taking sides.",
    "Observer": "Summarize, reflect, or critique the ongoing debate, often adding meta-level commentary.",
    "Verdict": "Summarize the overall debate and provide a final verdict. Consider all sides and reasoning provided."
}

agents = [
    DebateAgent("Pro", agent_instructions["Pro"], model=current_model, tokenizer=tokenizer, model_instance=local_model),
    DebateAgent("Con", agent_instructions["Con"], model=current_model, tokenizer=tokenizer, model_instance=local_model),
    DebateAgent("Expert", agent_instructions["Expert"], model=current_model, tokenizer=tokenizer, model_instance=local_model),
    DebateAgent("Observer", agent_instructions["Observer"], model=current_model, tokenizer=tokenizer, model_instance=local_model),
    DebateAgent("Verdict", agent_instructions["Verdict"], model=current_model, tokenizer=tokenizer, model_instance=local_model),
]
manager = DebateManager(agents)

@app.route("/")
def index():
    return send_from_directory(os.getcwd(), "index.html")

@app.route("/main.js")
def serve_main_js():
    return send_from_directory(os.getcwd(), "main.js")

@app.route("/set_model", methods=["POST"])
def set_model():
    global current_model, client
    data = request.get_json()
    model = data.get("model", "").strip().lower()
    api_key = data.get("api_key", "").strip()
    if model not in ["local", "openai"]:
        return jsonify({"error": "Invalid model."}), 400
    current_model = model
    for agent in agents:
        agent.model_type = model
    if model == "openai" and api_key:
        client = OpenAI(api_key=api_key)
    return jsonify({"status": f"Model set to '{model}'"})

@app.route("/switch_mode", methods=["POST"])
def switch_mode():
    global current_mode
    mode = request.get_json().get("mode", "").strip().lower()
    if mode not in ["debate", "chat"]:
        return jsonify({"error": "Invalid mode."}), 400
    current_mode = mode
    return jsonify({"status": f"Switched to {mode} mode."})

@app.route("/debate", methods=["POST"])
def debate():
    global debate_rounds
    if current_mode != "debate":
        return jsonify({"error": "Switch to debate mode first."}), 400

    data = request.get_json()
    topic = data.get("topic", "").strip()
    rounds = data.get("rounds", 6)

    if topic and all(len(agent.history) == 0 for agent in agents):
        manager.topic = topic
        manager.reset()
        debate_rounds = rounds

    result = manager.next_turn(client if current_model == "openai" else None)
    return jsonify(result)

@app.route("/history/<role>", methods=["GET"])
def get_history(role):
    for agent in agents:
        if agent.role.lower() == role.lower():
            return jsonify({"role": agent.role, "history": agent.history})
    return jsonify({"error": "Invalid role"}), 400

@app.route("/memory", methods=["GET"])
def get_memory():
    return jsonify({
        "long_term_memory": long_term_memory,
        "verdict_memory": verdict_memory
    })

@app.route("/reset", methods=["POST"])
def reset():
    manager.reset()
    return jsonify({"status": "reset successful"})

if __name__ == "__main__":
    app.run(debug=True, port=5009)
