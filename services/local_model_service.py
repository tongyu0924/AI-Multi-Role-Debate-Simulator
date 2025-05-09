# services/local_model_service.py

import torch
import re

def run_local_model(prompt: str, tokenizer, model, device):
    """
    Run inference on a local language model using the provided prompt.
    """
    input_ids = tokenizer.encode(prompt, return_tensors="pt", truncation=True, max_length=800)
    input_ids = input_ids.to(device)

    output = model.generate(
        input_ids,
        max_new_tokens=200,
        pad_token_id=tokenizer.eos_token_id,
        no_repeat_ngram_size=3,
        repetition_penalty=1.2,
        do_sample=True,
        temperature=0.8,
        top_k=50,
        top_p=0.95
    )

    decoded = tokenizer.decode(output[0], skip_special_tokens=True)
    # Extract only the agent's part
    return re.split(r'\n(?:Pro|Con|Expert|Observer|Verdict):', decoded)[0].strip()
