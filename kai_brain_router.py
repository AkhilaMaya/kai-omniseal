import os
import openai
import requests
import difflib
import hashlib

# Load API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
openai.api_key = OPENAI_API_KEY

# Simple memory store to compare output repetition
recent_outputs = []

def content_hash(text):
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()

def is_duplicate(new_output, threshold=0.92):
    for old in recent_outputs:
        sim = difflib.SequenceMatcher(None, new_output, old).ratio()
        if sim > threshold:
            return True
    return False

def remember_output(output):
    recent_outputs.append(output)
    if len(recent_outputs) > 25:
        recent_outputs.pop(0)

# Claude via OpenRouter
def call_claude(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer " + OPENROUTER_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "model": "anthropic/claude-3-sonnet",
        "messages": [{"role": "user", "content": prompt}],
        "usage": {"include": True}
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# GPT-4.1 via OpenAI
def call_gpt(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4-0613",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# Kai Hybrid Brain + Content Verifier
def get_kai_response(prompt, tone="neutral"):
    output = None
    if tone.lower() in ["scroll", "emotional", "healing", "poetic"]:
        output = call_claude(prompt)
    else:
        output = call_gpt(prompt)

    if is_duplicate(output):
        return "[REJECTED ⚠️] This response is too similar to a previous one. Rewrite recommended."
    else:
        remember_output(output)
        return output
