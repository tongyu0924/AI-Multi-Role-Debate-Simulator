from flask import Flask, request, jsonify, render_template
from config.settings import DEFAULT_MODEL, DEFAULT_MODE, DEFAULT_ROUNDS, OPENAI_API_KEY
from transformers import GPTNeoForCausalLM, GPT2Tokenizer
from services.openai_service import run_openai_chat
from services.local_model_service import run_local_model
from manager.debate_manager import build_agents
from memory.context_buffer import get_long_term
from memory.verdict_memory import verdict_memory
from manager.debate_manager import DebateManager
import torch
import os
from openai import OpenAI
from config import state

# Initialize Flask app with template folder
app = Flask(__name__, static_folder="static", static_url_path="/static", template_folder="templates")

# Runtime config
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
current_model = DEFAULT_MODEL
current_mode = DEFAULT_MODE
state.debate_rounds = DEFAULT_ROUNDS

# Load local model
model_name = "EleutherAI/gpt-neo-125M"
tokenizer = GPT2Tokenizer.from_pretrained(model_name)
local_model = GPTNeoForCausalLM.from_pretrained(model_name)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
local_model.to(device)

# Agents and manager
agents = build_agents(current_model, tokenizer, local_model)
manager = DebateManager(agents)
client = OpenAI(api_key=OPENAI_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Routes
@app.route("/")
def index():
    return render_template("index.html")

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
    if current_mode != "debate":
        return jsonify({"error": "Switch to debate mode first."}), 400

    data = request.get_json()
    topic = data.get("topic", "").strip()
    rounds = data.get("rounds", DEFAULT_ROUNDS)

    if topic:
        manager.topic = topic
        state.debate_rounds = rounds  
        if all(len(agent.history) == 0 for agent in agents):
            manager.reset()

    result = manager.next_turn(openai_client if current_model == "openai" else None)
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
        "long_term_memory": get_long_term(),
        "verdict_memory": verdict_memory
    })

@app.route("/reset", methods=["POST"])
def reset():
    manager.reset()
    return jsonify({"status": "reset successful"})

if __name__ == "__main__":
    app.run(debug=True, port=5009)
