# services/openai_service.py

def run_openai_chat(role: str, instruction: str, topic: str, context: str, client):
    """
    Use OpenAI API to generate agent's response in chat format.
    """
    system_prompt = (
        f"You are {role}. Task: {instruction}. Topic: '{topic}'. "
        "Think internally before answering. Limit to 80 words."
    )

    user_prompt = (
        f"Conversation so far:\n\n{context}\n\nNow reply as {role}:"
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    return response.choices[0].message.content.strip()
