# agents/expert.py

from .base_agent import DebateAgent

class ExpertAgent(DebateAgent):
    def __init__(self, role_name, instruction, model_type="openai", tokenizer=None, model_instance=None):
        super().__init__(
            role_name=role_name,
            instruction=instruction,
            model_type=model_type,
            tokenizer=tokenizer,
            model_instance=model_instance
        )
