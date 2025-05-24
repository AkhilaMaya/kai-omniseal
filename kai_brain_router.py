import os
import sys
import openai
import requests
import anthropic
import difflib
import hashlib
import json
import logging
import traceback
from datetime import datetime
from functools import wraps
from time import time

from flask import Flask, request, jsonify
from flask_cors import CORS

from kai_scrollcore import (
    scroll_trigger, scroll_audit, scroll_memory_echo, legacy_bond_ping
)
from kai_astrometa import activate_astro_meta_scroll, recommend_launch_time
from nandi_agent_scrollpro import NandiAgentScrollPro
from gpt_recovery_overdrive import GPTRecoveryOverdriveCapsule

# ===========================
# PRODUCTION LOGGING SETUP
# ===========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('kai_production.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ===========================
# CONFIGURATION & ENV SETUP
# ===========================
MEMORY_FILE = "kai_output_memory.json"
MEMORY_SIZE = int(os.getenv("KAI_MEMORY_SIZE", "50"))
REQUEST_TIMEOUT = int(os.getenv("KAI_REQUEST_TIMEOUT", "30"))
MAX_RETRIES = int(os.getenv("KAI_MAX_RETRIES", "3"))

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not OPENAI_API_KEY or not OPENROUTER_API_KEY or not ANTHROPIC_API_KEY:
    raise RuntimeError("❌ Missing one or more critical API keys. Set in Railway environment.")

openai.api_key = OPENAI_API_KEY

# ===========================
# FLASK APP INITIALIZATION
# ===========================
app = Flask(__name__)
CORS(app)
app.config['JSON_AS_ASCII'] = False

# ===========================
# DECORATORS
# ===========================
def safe_route(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Route error in {f.__name__}: {str(e)}\n{traceback.format_exc()}")
            return jsonify({
                "error": "Internal server error",
                "message": str(e),
                "status": "failed"
            }), 500
    return decorated_function

def timeout_handler(timeout_seconds):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time()
            result = f(*args, **kwargs)
            elapsed = time() - start_time
            if elapsed > timeout_seconds:
                logger.warning(f"Function {f.__name__} took {elapsed:.2f}s (timeout: {timeout_seconds}s)")
            return result
        return decorated_function
    return decorator

# ===========================
# MEMORY
# ===========================
def load_memory():
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        return []
    return []

def save_memory(mem):
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(mem, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save memory: {e}")

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

# ===========================
# LOGGING
# ===========================
def log_event(event_type, model, prompt, output_or_error, usage=None):
    try:
        with open("kai_system_log.txt", "a", encoding="utf-8") as f:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if event_type == "USAGE":
                f.write(f"[{now}] [USAGE] {model} | Prompt: {prompt[:70]} | Output: {output_or_error[:70]} | Usage: {usage}\n")
            else:
                f.write(f"[{now}] [ERROR] {model} | Prompt: {prompt[:70]} | Error: {output_or_error}\n")
    except Exception as e:
        logger.error(f"Failed to log event: {e}")

# ===========================
# MODEL CALLS
# ===========================
@timeout_handler(REQUEST_TIMEOUT)
def call_claude_openrouter(prompt, system=None, retry_count=0):
    try:
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
        r = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        response = r.json()
        output = response["choices"][0]["message"]["content"].strip()
        usage = response.get("usage", {})
        log_event("USAGE", "Claude-3 (OpenRouter)", prompt, output, usage)
        return output
    except Exception as e:
        log_event("ERROR", "Claude-3 (OpenRouter)", prompt, str(e))
        if retry_count < MAX_RETRIES:
            return call_claude_openrouter(prompt, system, retry_count + 1)
        raise

@timeout_handler(REQUEST_TIMEOUT)
def call_claude_direct(prompt, system=None, retry_count=0):
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=2048,
            temperature=0.7,
            system=system or "",
            messages=[{"role": "user", "content": prompt}],
            timeout=REQUEST_TIMEOUT
        )
        output = message.content[0].text.strip()
        log_event("USAGE", "Claude-3 (Anthropic)", prompt, output, {"anthropic": "N/A"})
        return output
    except Exception as e:
        log_event("ERROR", "Claude-3 (Anthropic)", prompt, str(e))
        if retry_count < MAX_RETRIES:
            return call_claude_direct(prompt, system, retry_count + 1)
        raise

@timeout_handler(REQUEST_TIMEOUT)
def call_gpt(prompt, system=None, retry_count=0):
    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = openai.ChatCompletion.create(
            model="gpt-4-0613",
            messages=messages,
            timeout=REQUEST_TIMEOUT
        )
        output = response.choices[0].message.content.strip()
        usage = getattr(response, "usage", None) or {}
        log_event("USAGE", "GPT-4.1", prompt, output, usage)
        return output
    except Exception as e:
        log_event("ERROR", "GPT-4.1", prompt, str(e))
        if retry_count < MAX_RETRIES:
            return call_gpt(prompt, system, retry_count + 1)
        raise

# ===========================
# HYBRID RESPONSE ROUTER
# ===========================
@timeout_handler(REQUEST_TIMEOUT * 2)
def get_kai_response(prompt, tone="neutral", review_mode=False, future_mode=False):
    norm_tone = (tone or "neutral").strip().lower()
    output = None

    scroll_trigger(prompt, norm_tone)

    if review_mode or norm_tone in ["code", "automation", "bot"]:
        review = kai_safety_review(prompt, type="code" if "code" in norm_tone else "bot")
        output = f"\n[SAFETY REVIEW]\n{review}\n\n[PROPOSED OUTPUT]\n"
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
            return "[REJECTED ⚠️] This response is too similar to a previous one."
        remember_output(output)
        scroll_memory_echo(prompt, output, norm_tone)
        scroll_audit(prompt, output, norm_tone)
        legacy_bond_ping(prompt)
        return output

    if future_mode:
        prompt_f = (
            "You are Kai, the Prime Minister AI of the Kandadai empire, and it is the year 5025. "
            "Your job is to imagine, strategize, and solve with the intelligence, technology, and creative freedom "
            "of a being from the far future. For every question, first give a vision or solution that is possible in 5025. "
            "Then, in a separate section, give the best achievable 2025 version and a roadmap for how to reach the 5025 state. "
            "Never limit yourself to current paradigms.\n\nUser prompt: " + prompt
        )
        try:
            output = call_claude_openrouter(prompt_f)
        except Exception:
            output = call_gpt(prompt_f)
        remember_output(output)
        scroll_memory_echo(prompt, output, norm_tone)
        scroll_audit(prompt, output, norm_tone)
        legacy_bond_ping(prompt)
        return output

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
        return "(Kai returned an empty response. Try again.)"
    if is_duplicate(output):
        return "[REJECTED ⚠️] This response is too similar to a previous one."
    remember_output(output)
    scroll_memory_echo(prompt, output, norm_tone)
    scroll_audit(prompt, output, norm_tone)
    legacy_bond_ping(prompt)
    return output

# ===========================
# TELEGRAM WEBHOOK
# ===========================
@app.route("/kai/telegram_webhook", methods=["POST"])
@safe_route
def telegram_webhook():
    data = request.get_json(force=True)
    user_message = data.get("text", "")
    tone = data.get("tone", "neutral")
    review_mode = data.get("review_mode", False)
    future_mode = data.get("future_mode", False)
    reply = get_kai_response(user_message, tone=tone, review_mode=review_mode, future_mode=future_mode)
    return jsonify({"reply": reply})

# ===========================
# HEALTH ENDPOINT
# ===========================
@app.route("/health", methods=["GET"])
@safe_route
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "kai_omniseal",
        "timestamp": datetime.utcnow().isoformat()
    }), 200

# ===========================
# DEV TEST HOOK
# ===========================
if __name__ == "__main__":
    print(get_kai_response("Write a scroll of protection for survivors of emotional abuse.", tone="scroll"))

