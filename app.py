from flask import Flask, request, jsonify, send_from_directory
from transformers import GPTNeoForCausalLM, GPT2Tokenizer
import torch
import os
import re

from openai import OpenAI

# Set OpenAI API key
os.environ["OPENAI_API_KEY"] = "OPENAI_API_KEY"

app = Flask(__name__, static_folder='static', static_url_path='/static')

@app.route("/main.js")
def serve_main_js():
    return send_from_directory(os.getcwd(), "main.js")

# Load local GPT-Neo model
model_name = "EleutherAI/gpt-neo-125M"
tokenizer = GPT2Tokenizer.from_pretrained(model_name)
model = GPTNeoForCausalLM.from_pretrained(model_name)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# App state
chat_history = {"user": "", "assistant": ""}
roles = ["Pro", "Con", "Expert", "Observer"]
agent_instructions = {
    "Pro": "You argue strongly in favor of the topic.",
    "Con": "You argue strongly against the topic.",
    "Expert": "You provide a neutral and analytical perspective.",
    "Observer": "You summarize or raise questions based on the ongoing debate."
}
debate_history = {role: [] for role in roles}
current_turn = 0
debate_topic = "Artificial intelligence"
current_mode = "debate"
current_model = "openai"

openai_api_key = os.environ.get("OPENAI_API_KEY", "")
client = OpenAI(api_key=openai_api_key)

@app.route("/")
def index():
    return send_from_directory(os.getcwd(), "index.html")

@app.route("/set_model", methods=["POST"])
def set_model():
    global current_model, openai_api_key, client
    data = request.get_json()
    model = data.get("model", "").strip().lower()
    api_key = data.get("api_key", "").strip()

    if model not in ["local", "openai"]:
        return jsonify({"error": "Invalid model. Choose 'local' or 'openai'."}), 400

    current_model = model
    if model == "openai":
        if api_key:
            openai_api_key = api_key
            client = OpenAI(api_key=api_key)
        elif not openai_api_key:
            return jsonify({"error": "API key is required for OpenAI mode."}), 400

    return jsonify({"status": f"Model set to '{model}'."})

@app.route("/switch_mode", methods=["POST"])
def switch_mode():
    global current_mode
    data = request.get_json()
    mode = data.get("mode", "").strip().lower()
    if mode not in ["debate", "chat"]:
        return jsonify({"error": "Invalid mode. Choose 'debate' or 'chat'."}), 400
    current_mode = mode
    return jsonify({"status": f"Switched to {mode} mode."})

@app.route("/debate", methods=["POST"])
def debate():
    global debate_history, current_turn, debate_topic
    if current_mode != "debate":
        return jsonify({"error": "Please switch to Debate Mode first."}), 400

    data = request.get_json()
    topic = data.get("topic", "").strip()
    role = roles[current_turn]

    if topic and all(len(debate_history[r]) == 0 for r in roles):
        debate_topic = topic
        for r in roles:
            debate_history[r] = []

    formatted_history = "\n".join([
        f"{r}: {msg}" for r in roles for msg in debate_history[r]
    ])

    if current_model == "openai":
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    # CoT prompt: This sentence encourages the model to internally reason before generating an answer (implicit Chain-of-Thought).
                    "content": f"You are playing the role of {role}. Your task: {agent_instructions[role]} Stay in character. The debate topic is: '{debate_topic}'. Think through your reasoning internally before responding. Then write your reply in 3–4 short sentences, under 80 words. Be focused, clear, and avoid examples or repetition."
                },
                {
                    "role": "user",
                    "content": f"Here is the conversation so far:\n\n{formatted_history}\n\nNow continue as {role}:"
                }
            ]
        )
        reply = response.choices[0].message.content.strip()
    else:
        prompt = formatted_history + f"\n{role}:"
        input_ids = tokenizer.encode(prompt, return_tensors="pt", truncation=True, max_length=800)
        output = model.generate(
            input_ids.to(device),
            max_new_tokens=200,
            pad_token_id=tokenizer.eos_token_id,
            no_repeat_ngram_size=3,
            repetition_penalty=1.2,
            do_sample=True,
            temperature=0.8,
            top_k=50,
            top_p=0.95
        )
        decoded_output = tokenizer.decode(output[0], skip_special_tokens=True)
        reply = decoded_output[len(tokenizer.decode(input_ids[0], skip_special_tokens=True)):].strip()
        reply = re.split(r'\n(?:' + '|'.join(roles) + '):', reply)[0].strip()

    debate_history[role].append(reply)
    current_turn = (current_turn + 1) % len(roles)
    return jsonify({"role": role, "reply": reply})

@app.route("/chat", methods=["POST"])
def chat():
    if current_mode != "chat":
        return jsonify({"error": "Please switch to Chat Mode first."}), 400

    data = request.get_json()
    role = data.get("role", "")
    message = data.get("message", "")
    if role not in ["user", "assistant"] or not message:
        return jsonify({"error": "Invalid input"}), 400

    chat_history[role] += f"{role}: {message}\n"
    full_context = chat_history["user"] + chat_history["assistant"]

    if current_model == "openai":
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": message}]
        )
        reply = response.choices[0].message.content.strip()
    else:
        input_ids = tokenizer.encode(full_context, return_tensors="pt", truncation=True, max_length=800)
        output = model.generate(
            input_ids.to(device),
            max_new_tokens=60,
            pad_token_id=tokenizer.eos_token_id,
            no_repeat_ngram_size=3,
            repetition_penalty=1.2,
            do_sample=True,
            temperature=0.8,
            top_k=50,
            top_p=0.95
        )
        decoded_output = tokenizer.decode(output[0], skip_special_tokens=True)
        reply = decoded_output[len(tokenizer.decode(input_ids[0], skip_special_tokens=True)):].strip()
        reply = reply.split("\n")[0].strip()

    if role == "user":
        chat_history["assistant"] += f"assistant: {reply}\n"
    else:
        chat_history["user"] += f"user: {reply}\n"

    return jsonify({"reply": reply})

@app.route("/history/<role>", methods=["GET"])
def get_history(role):
    role = role.capitalize()
    if role not in debate_history:
        return jsonify({"error": "Invalid role"}), 400
    return jsonify({"role": role, "history": debate_history[role]})

@app.route("/reset", methods=["POST"])
def reset():
    global chat_history, debate_history, current_turn, current_mode
    chat_history = {"user": "", "assistant": ""}
    debate_history = {role: [] for role in roles}
    current_turn = 0
    current_mode = "debate"
    return jsonify({"status": "reset successful"})

if __name__ == "__main__":
    app.run(debug=True, port=5009)
