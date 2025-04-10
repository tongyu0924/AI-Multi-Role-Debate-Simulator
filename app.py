from flask import Flask, request, jsonify, send_from_directory
from transformers import GPTNeoForCausalLM, GPT2Tokenizer
import torch
import os
import re

app = Flask(__name__, static_folder='.', static_url_path='')

# Load GPT-Neo (smallest model suitable for both CPU and GPU)
model_name = "EleutherAI/gpt-neo-125M"  # This is the smallest GPT-Neo model, suitable for CPU
tokenizer = GPT2Tokenizer.from_pretrained(model_name)
model = GPTNeoForCausalLM.from_pretrained(model_name)

# Check if GPU is available, use GPU if available, otherwise use CPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# Chat history initialization
chat_history = {"user": "", "assistant": ""}

# Debate state initialization
roles = ["Pro", "Con"]
debate_history = ""
current_turn = 0
debate_topic = "Artificial intelligence"  # Default debate topic

# Home page route
@app.route("/")
def index():
    return send_from_directory('.', 'index.html')

# ✅ Debate mode (supporting topic input)
@app.route("/debate", methods=["POST"])
def debate():
    global debate_history, current_turn, debate_topic
    data = request.get_json()
    topic = data.get("topic", "").strip()
    role = roles[current_turn]

    # Initialize debate history if a new topic is provided and history is empty
    if topic and debate_history.strip() == "":
        debate_topic = topic
        debate_history = f"Pro: I believe {debate_topic} will benefit society.\nCon:"
    elif debate_history.strip() == "":
        debate_history = f"Pro: I believe {debate_topic} will benefit society.\nCon:"

    # Add current turn role to the prompt
    prompt = debate_history + f"\n{role}:"
    input_ids = tokenizer.encode(prompt, return_tensors="pt", truncation=True, max_length=800)

    # Generate the response
    output = model.generate(
        input_ids.to(device),  # Ensure the input is on GPU or CPU
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
    reply = re.split(r'\n(?:Pro|Con):', reply)[0].strip()

    # Update debate history and switch turns
    debate_history += f"\n{role}: {reply}"
    current_turn = 1 - current_turn

    return jsonify({"role": role, "reply": reply})

# ✅ Chat mode
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    role = data.get("role", "")
    message = data.get("message", "")

    # Validate the input
    if role not in ["user", "assistant"] or not message:
        return jsonify({"error": "Invalid input"}), 400

    # Append the user's message to the chat history
    chat_history[role] += f"{role}: {message}\n"
    full_context = chat_history["user"] + chat_history["assistant"]

    # Tokenize the full context and generate the response
    input_ids = tokenizer.encode(full_context, return_tensors="pt", truncation=True, max_length=800)
    output = model.generate(
        input_ids.to(device),  # Ensure the input is on GPU or CPU
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

    # Update the chat history based on the role
    if role == "user":
        chat_history["assistant"] += f"assistant: {reply}\n"
    else:
        chat_history["user"] += f"user: {reply}\n"

    return jsonify({"reply": reply})

# Reset button (to restart the debate)
@app.route("/reset", methods=["POST"])
def reset():
    global chat_history, debate_history, current_turn
    chat_history = {"user": "", "assistant": ""}
    debate_history = ""
    current_turn = 0
    return jsonify({"status": "reset successful"})

# Start the server
if __name__ == "__main__":
    app.run(debug=True, port=5009)
