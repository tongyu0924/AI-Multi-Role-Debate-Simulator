# memory/verdict_memory.py

verdict_memory = []

def add_to_verdict_memory(text: str):
    """
    Add a statement to verdict memory.
    """
    verdict_memory.append(text)

def reset_verdict_memory():
    """
    Clear verdict memory.
    """
    verdict_memory.clear()
