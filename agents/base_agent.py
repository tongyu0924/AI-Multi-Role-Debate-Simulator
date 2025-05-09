# agents/base_agent.py
import re
import torch
from memory.context_buffer import get_recent_context
from memory.verdict_memory import add_to_verdict_memory
from services.openai_service import run_openai_chat
from services.local_model_service import run_local_model
from memory.context_buffer import get_long_term, append_to_long_term
from memory.verdict_memory import verdict_memory, add_to_verdict_memory

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class DebateAgent:
    def __init__(self, role_name, instruction, model_type="openai", tokenizer=None, model_instance=None):
        self.role = role_name
        self.instruction = instruction
        self.model_type = model_type
        self.tokenizer = tokenizer
        self.model = model_instance
        self.history = []

    def observe(self, topic, context):
        # Smart Context Management: only recent context, excluding self
        recent_lines = get_long_term()[-4:]
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
            return run_openai_chat(obs["role"], obs["instruction"], obs["topic"], obs["context"], client)
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
        append_to_long_term(f"{self.role}: {action}")
        if self.role != "Verdict":
            add_to_verdict_memory(f"{self.role}: {action}")
        return action

    def step(self, topic, context, client=None):
        obs = self.observe(topic, context)
        action = self.decide_action(obs, client)
        return self.act(action)
    
