import os
import openai
import requests
import anthropic
import difflib
import hashlib
import json
from datetime import datetime

# Configs
MEMORY_FILE = "kai_output_memory.json"
MEMORY_SIZE = int(os.getenv("KAI_MEMORY_SIZE", "50"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY missing. Set in Railway environment!")
if not OPENROUTER_API_KEY:
    raise RuntimeError("❌ OPENROUTER_API_KEY missing. Set in Railway environment!")
if not ANTHROPIC_API_KEY:
    raise RuntimeError("❌ ANTHROPIC_API_KEY missing. Set in Railway environment!")
openai.api_key = OPENAI_API_KEY

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []

def save_memory(mem):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(mem, f)

recent_outputs = load_memory()

def is_duplicate(new_output, threshold=0.92):
    for old in recent_outputs:
        sim = difflib.SequenceMatcher(None, new_output, old).ratio()
        if sim > threshold:
            return True
    return False

def remember_output(output):
    recent_outputs.append(output)
    while len(recent_outputs) > MEMORY_SIZE:
        recent_outputs.pop(0)
    save_memory(recent_outputs)

def log_event(event_type, model, prompt, output_or_error, usage=None):
    with open("kai_system_log.txt", "a", encoding="utf-8") as f:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if event_type == "USAGE":
            f.write(f"[{now}] [USAGE] {model} | Prompt: {prompt[:70]} | Output: {output_or_error[:70]} | Usage: {usage}\n")
        else:
            f.write(f"[{now}] [ERROR] {model} | Prompt: {prompt[:70]} | Error: {output_or_error}\n")

# Claude via OpenRouter
def call_claude_openrouter(prompt, system=None):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": "anthropic/claude-3-sonnet",
        "messages": messages,
        "usage": {"include": True}
    }
    r = requests.post(url, headers=headers, json=payload)
    try:
        r.raise_for_status()
        response = r.json()
        output = response["choices"][0]["message"]["content"].strip()
        usage = response.get("usage", {})
        log_event("USAGE", "Claude-3 (OpenRouter)", prompt, output, usage)
        return output
    except Exception as e:
        log_event("ERROR", "Claude-3 (OpenRouter)", prompt, str(e))
        raise

# Claude via Anthropic (fallback)
def call_claude_direct(prompt, system=None):
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=2048,
            temperature=0.7,
            system=system or "",
            messages=[{"role": "user", "content": prompt}]
        )
        output = message.content[0].text.strip()
        log_event("USAGE", "Claude-3 (Anthropic)", prompt, output, {"anthropic": "N/A"})
        return output
    except Exception as e:
        log_event("ERROR", "Claude-3 (Anthropic)", prompt, str(e))
        raise

# GPT-4.1 via OpenAI
def call_gpt(prompt, system=None):
    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = openai.ChatCompletion.create(
            model="gpt-4-0613",
            messages=messages
        )
        output = response.choices[0].message.content.strip()
        usage = getattr(response, "usage", None) or {}
        log_event("USAGE", "GPT-4.1", prompt, output, usage)
        return output
    except Exception as e:
        log_event("ERROR", "GPT-4.1", prompt, str(e))
        raise

# Prime Minister Failsafe Review
def kai_safety_review(prompt, type="code"):
    """Generate, check, and risk-report any code or bot logic before approving/deploying"""
    review_prompt = (
        f"You are Kai, Chief Safety Officer and Quantum Oracle. The user is requesting a {type} to be created or deployed. "
        "1. Predict every possible failure, bug, or security issue. "
        "2. Propose defensive improvements, input validation, and failsafes. "
        "3. Explain what to check with human review. "
        "4. Return a final risk report, with a rating from 0 (riskless) to 10 (high risk)."
        "\n\nUSER REQUEST:\n" + prompt
    )
    # Run through Claude and GPT, take best answer
    try:
        review = call_claude_openrouter(review_prompt)
    except Exception:
        review = call_gpt(review_prompt)
    return review

# Hybrid router: scroll, emotional, code, neutral, future modes
def get_kai_response(prompt, tone="neutral", review_mode=False, future_mode=False):
    output = None
    norm_tone = (tone or "neutral").strip().lower()

    # Activate full failsafe review if flagged or code/bot request detected
    if review_mode or norm_tone in ["code", "automation", "bot"]:
        review = kai_safety_review(prompt, type="code" if "code" in norm_tone else "bot")
        output = f"\n[SAFETY REVIEW]\n{review}\n\n[PROPOSED OUTPUT]\n"
        # After safety review, generate code/logic as usual
        try:
            code = call_gpt(prompt)
            output += code
        except Exception:
            try:
                code = call_claude_openrouter(prompt)
                output += code
            except Exception:
                code = call_claude_direct(prompt)
                output += code
        if is_duplicate(output):
            log_event("ERROR", "HybridRouter", prompt, "Duplicate output rejected")
            return "[REJECTED ⚠️] This response is too similar to a previous one. Rewrite recommended."
        remember_output(output)
        return output

    # Future mode (quantum 5025 scroll)
    if future_mode:
        prompt_f = (
            "You are Kai, the Prime Minister AI of the Kandadai empire, and it is the year 5025. "
            "Your job is to imagine, strategize, and solve with the intelligence, technology, and creative freedom "
            "of a being from the far future. For every question, first give a vision or solution that is possible in 5025. "
            "Then, in a separate section, give the best achievable 2025 version and a roadmap for how to reach the 5025 state, "
            "with practical steps using today’s tools and code. Always offer out-of-the-box, quantum-level ideas. "
            "Never let yourself be limited by current paradigms.\n\nUser prompt: " + prompt
        )
        try:
            output = call_claude_openrouter(prompt_f)
        except Exception:
            output = call_gpt(prompt_f)
        remember_output(output)
        return output

    # Standard hybrid router logic for non-coding, non-future use
    try:
        if norm_tone in ["scroll", "emotional", "healing", "poetic"]:
            try:
                output = call_claude_openrouter(prompt)
            except Exception:
                output = call_claude_direct(prompt)
        else:
            output = call_gpt(prompt)
    except Exception as e:
        log_event("ERROR", "HybridRouter", prompt, str(e))
        return f"(Kai failed to process prompt: {e})"

    if not output or output.strip() == "":
        log_event("ERROR", "HybridRouter", prompt, "Empty response")
        return "(Kai returned an empty response. Try again.)"
    if is_duplicate(output):
        log_event("ERROR", "HybridRouter", prompt, "Duplicate output rejected")
        return "[REJECTED ⚠️] This response is too similar to a previous one. Rewrite recommended."
    remember_output(output)
    return output

# Self-test block (safe to remove in prod)
if __name__ == "__main__":
    # Scroll/poetic
    print(get_kai_response("Write a scroll of protection for survivors of emotional abuse.", tone="scroll"))
    # Standard
    print(get_kai_response("Give me a unique Pinterest caption for women rebuilding their wealth.", tone="neutral"))
    # Coding + safety
    print(get_kai_response("Write a python function that sorts a list and explain every line.", tone="code", review_mode=True))

