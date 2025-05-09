# manager/debate_manager.py

from memory.context_buffer import get_long_term, clear_long_term
from memory.verdict_memory import verdict_memory
from agents.pro_role import ProAgent
from agents.con_role import ConAgent
from agents.expert import ExpertAgent
from agents.observer import ObserverAgent
from agents.verdict import VerdictAgent
from config import state

agent_instructions = {
    "Pro": "Argue in favor of the topic, presenting supporting evidence and reasoning.",
    "Con": "Argue against the topic, highlighting risks, flaws, or counterexamples.",
    "Expert": "Offer neutral, technical, or factual insights to deepen the discussion without taking sides.",
    "Observer": "Summarize, reflect, or critique the ongoing debate, often adding meta-level commentary.",
    "Verdict": "Summarize the overall debate and provide a final verdict. Consider all sides and reasoning provided."
}


def build_agents(model_type, tokenizer, local_model, openai_client=None):
    return [
        ProAgent("Pro", agent_instructions["Pro"], model_type=model_type, tokenizer=tokenizer, model_instance=local_model),
        ConAgent("Con", agent_instructions["Con"], model_type=model_type, tokenizer=tokenizer, model_instance=local_model),
        ExpertAgent("Expert", agent_instructions["Expert"], model_type=model_type, tokenizer=tokenizer, model_instance=local_model),
        ObserverAgent("Observer", agent_instructions["Observer"], model_type=model_type, tokenizer=tokenizer, model_instance=local_model),
        VerdictAgent("Verdict", agent_instructions["Verdict"], model_type=model_type, tokenizer=tokenizer, model_instance=local_model),
    ]

class DebateManager:
    def __init__(self, agents, topic="Artificial Intelligence"):
        self.agents = agents
        self.topic = topic
        self.turn = 0
        self.rounds = 0

    def get_context(self):
        return "\n".join(get_long_term())

    def next_turn(self, client=None):
        total_turns = state.debate_rounds * 4  # 4 main agents

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
        clear_long_term()
        verdict_memory.clear()
        self.turn = 0
        self.rounds = 0