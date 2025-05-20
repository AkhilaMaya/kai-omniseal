import os
import openai
import requests

# Load API Keys from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

openai.api_key = OPENAI_API_KEY

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

# Brain Router
def get_kai_response(prompt, tone="neutral"):
    if tone.lower() in ["scroll", "emotional", "healing", "poetic"]:
        return call_claude(prompt)
    else:
        return call_gpt(prompt)
