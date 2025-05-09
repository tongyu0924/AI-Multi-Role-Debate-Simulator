# memory/context_buffer.py

# Global context memory across agents
_long_term_memory = []

def append_to_long_term(entry: str):
    _long_term_memory.append(entry)

def clear_long_term():
    _long_term_memory.clear()

def get_long_term():
    return _long_term_memory

def get_recent_context(role: str, limit: int = 4):
    recent_lines = _long_term_memory[-limit:]
    others = [line for line in recent_lines if not line.startswith(f"{role}:")]
    return "\n".join(others)
