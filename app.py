from flask import Flask, request, jsonify, send_from_directory
from transformers import GPTNeoForCausalLM, GPT2Tokenizer
import torch
import os
import re

app = Flask(__name__, static_folder='.', static_url_path='')

# Load local GPT-Neo model and tokenizer
model_name = "EleutherAI/gpt-neo-125M"
tokenizer = GPT2Tokenizer.from_pretrained(model_name)
model = GPTNeoForCausalLM.from_pretrained(model_name)

# Use GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# Global state variables
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
current_model = "local"

# Use environment variable as default OpenAI key
openai_api_key = os.environ.get("OPENAI_API_KEY", "")

@app.route("/")
def index():
    return send_from_directory('.', 'index.html')

# Set the model (local or openai)
@app.route("/set_model", methods=["POST"])
def set_model():
    global current_model, openai_api_key
    data = request.get_json()
    model = data.get("model", "").strip().lower()
    api_key = data.get("api_key", "").strip()

    if model not in ["local", "openai"]:
        return jsonify({"error": "Invalid model. Choose 'local' or 'openai'."}), 400

    current_model = model
    if model == "openai":
        if api_key:
            openai_api_key = api_key
        elif not openai_api_key:
            return jsonify({"error": "API key is required for OpenAI mode."}), 400

    return jsonify({"status": f"Model set to '{model}'."})

# Switch between 'debate' or 'chat' mode
@app.route("/switch_mode", methods=["POST"])
def switch_mode():
    global current_mode
    data = request.get_json()
    mode = data.get("mode", "").strip().lower()
    if mode not in ["debate", "chat"]:
        return jsonify({"error": "Invalid mode. Please choose either 'debate' or 'chat'."}), 400
    current_mode = mode
    return jsonify({"status": f"Switched to {mode} mode."})

# Debate endpoint
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
            debate_history[r] = [f"{r}: {agent_instructions[r]}"]

    prompt = "\n".join([msg for msgs in debate_history.values() for msg in msgs]) + f"\n{role}:"

    if current_model == "openai":
        import openai
        openai.api_key = openai_api_key
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"You are {role}. {agent_instructions[role]} The topic is: {debate_topic}"},
                {"role": "user", "content": prompt}
            ]
        )
        reply = response.choices[0].message.content.strip()
    else:
        input_ids = tokenizer.encode(prompt, return_tensors="pt", truncation=True, max_length=800)
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
        reply = re.split(r'\n(?:' + '|'.join(roles) + '):', reply)[0].strip()

    debate_history[role].append(f"{role}: {reply}")
    current_turn = (current_turn + 1) % len(roles)

    return jsonify({"role": role, "reply": reply})

# Chat endpoint
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
        import openai
        openai.api_key = openai_api_key
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": message}
            ]
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

# Reset all state
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