"""
Kai Brain Router - Railway Production Version
Thread-safe, robust error handling, optimized for production
Fixed: tuple annotation syntax, error handling improvements
"""

import os
import sys
import requests
import logging
import traceback
import difflib
import threading
from datetime import datetime
from time import time
from typing import Dict, List, Any, Tuple

# ===========================
# PRODUCTION LOGGING SETUP
# ===========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ===========================
# CONFIGURATION & ENV SETUP
# ===========================
REQUEST_TIMEOUT = int(os.getenv("KAI_REQUEST_TIMEOUT", "30"))
MAX_RETRIES = int(os.getenv("KAI_MAX_RETRIES", "3"))
MEMORY_SIZE = 50
MAX_PROMPT_LENGTH = 8000  # Prevent token limit issues
MAX_LOG_SIZE = 100

# API Keys validation
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not OPENAI_API_KEY or not OPENROUTER_API_KEY or not ANTHROPIC_API_KEY:
    raise RuntimeError("❌ Missing critical API keys: OPENAI_API_KEY, OPENROUTER_API_KEY, ANTHROPIC_API_KEY")

# ===========================
# THREAD-SAFE IN-MEMORY STORAGE
# ===========================
class ThreadSafeMemory:
    """Thread-safe memory management for outputs and logs"""
    def __init__(self, max_outputs: int = MEMORY_SIZE, max_logs: int = MAX_LOG_SIZE):
        self._outputs: List[str] = []
        self._logs: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self.max_outputs = max_outputs
        self.max_logs = max_logs

    def add_output(self, output: str) -> None:
        with self._lock:
            self._outputs.append(output)
            if len(self._outputs) > self.max_outputs:
                self._outputs.pop(0)

    def check_duplicate(self, new_output: str, threshold: float = 0.92) -> bool:
        with self._lock:
            for old_output in self._outputs:
                similarity = difflib.SequenceMatcher(None, new_output, old_output).ratio()
                if similarity > threshold:
                    return True
            return False

    def add_log(self, log_entry: Dict[str, Any]) -> None:
        with self._lock:
            self._logs.append(log_entry)
            if len(self._logs) > self.max_logs:
                self._logs.pop(0)

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "outputs_count": len(self._outputs),
                "outputs_limit": self.max_outputs,
                "logs_count": len(self._logs),
                "logs_limit": self.max_logs
            }

    def clear_all(self) -> None:
        with self._lock:
            self._outputs.clear()
            self._logs.clear()

memory = ThreadSafeMemory()

# ===========================
# LOGGING UTILITIES
# ===========================
def log_event(event_type: str, model: str, prompt: str, output_or_error: str, usage: Dict[str, Any] = None) -> None:
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "model": model,
            "prompt_preview": prompt[:100] + "..." if len(prompt) > 100 else prompt,
            "output_preview": str(output_or_error)[:100] + "..." if len(str(output_or_error)) > 100 else str(output_or_error),
            "usage": usage or {}
        }
        memory.add_log(log_entry)
        if event_type == "ERROR":
            logger.error(f"{model} failed: {output_or_error}")
        else:
            logger.info(f"{model} success: {len(str(output_or_error))} chars")
    except Exception as e:
        logger.error(f"Failed to log event: {e}")

# ===========================
# INPUT VALIDATION
# ===========================
def validate_prompt(prompt: str) -> Tuple[bool, str]:
    if not prompt or not prompt.strip():
        return False, "Empty prompt provided"
    if len(prompt) > MAX_PROMPT_LENGTH:
        return False, f"Prompt too long (max {MAX_PROMPT_LENGTH} characters)"
    return True, ""

# ===========================
# MODEL CALLS WITH BETTER ERROR HANDLING
# ===========================
def call_claude_openrouter(prompt: str, system: str = None, retry_count: int = 0) -> str:
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://kai-omniseal.railway.app",
            "X-Title": "Kai Omniseal"
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": "anthropic/claude-3-sonnet",
            "messages": messages,
            "max_tokens": 2048,
            "temperature": 0.7
        }
        response = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        if "choices" not in data or not data["choices"]:
            raise Exception("No choices in OpenRouter response")
        output = data["choices"][0]["message"]["content"].strip()
        usage = data.get("usage", {})
        log_event("SUCCESS", "Claude-OpenRouter", prompt, output, usage)
        return output
    except requests.exceptions.Timeout as e:
        error_msg = f"OpenRouter timeout after {REQUEST_TIMEOUT}s"
        log_event("ERROR", "Claude-OpenRouter", prompt, error_msg)
        if retry_count < MAX_RETRIES:
            logger.warning(f"Retrying Claude-OpenRouter (attempt {retry_count + 1})")
            return call_claude_openrouter(prompt, system, retry_count + 1)
        raise Exception(error_msg)
    except requests.exceptions.HTTPError as e:
        error_msg = f"OpenRouter HTTP error: {e.response.status_code if e.response else 'unknown'}"
        log_event("ERROR", "Claude-OpenRouter", prompt, error_msg)
        if retry_count < MAX_RETRIES and (not e.response or e.response.status_code >= 500):
            logger.warning(f"Retrying Claude-OpenRouter (attempt {retry_count + 1})")
            return call_claude_openrouter(prompt, system, retry_count + 1)
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"OpenRouter unexpected error: {str(e)}"
        log_event("ERROR", "Claude-OpenRouter", prompt, error_msg)
        if retry_count < MAX_RETRIES:
            logger.warning(f"Retrying Claude-OpenRouter (attempt {retry_count + 1})")
            return call_claude_openrouter(prompt, system, retry_count + 1)
        raise Exception(error_msg)

def call_claude_direct(prompt: str, system: str = None, retry_count: int = 0) -> str:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=2048,
            temperature=0.7,
            system=system or "",
            messages=[{"role": "user", "content": prompt}]
        )
        output = message.content[0].text.strip()
        log_event("SUCCESS", "Claude-Direct", prompt, output)
        return output
    except Exception as e:
        error_msg = f"Claude Direct error: {str(e)}"
        log_event("ERROR", "Claude-Direct", prompt, error_msg)
        if retry_count < MAX_RETRIES:
            logger.warning(f"Retrying Claude-Direct (attempt {retry_count + 1})")
            return call_claude_direct(prompt, system, retry_count + 1)
        raise Exception(error_msg)

def call_openai_gpt(prompt: str, system: str = None, retry_count: int = 0) -> str:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=2048,
            temperature=0.7,
            timeout=REQUEST_TIMEOUT
        )
        output = response.choices[0].message.content.strip()
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
        log_event("SUCCESS", "GPT-4", prompt, output, usage)
        return output
    except Exception as e:
        error_msg = f"GPT-4 error: {str(e)}"
        log_event("ERROR", "GPT-4", prompt, error_msg)
        if retry_count < MAX_RETRIES:
            logger.warning(f"Retrying GPT-4 (attempt {retry_count + 1})")
            return call_openai_gpt(prompt, system, retry_count + 1)
        raise Exception(error_msg)

# ===========================
# MAIN RESPONSE ROUTER
# ===========================
def get_kai_response(prompt: str, tone: str = "neutral") -> str:
    try:
        valid, error_msg = validate_prompt(prompt)
        if not valid:
            logger.warning(f"Invalid prompt: {error_msg}")
            return f"⚠️ {error_msg}"

        prompt = prompt.strip()
        norm_tone = (tone or "neutral").strip().lower()
        logger.info(f"Processing request: tone={norm_tone}, length={len(prompt)}")

        # Determine model order based on tone
        if norm_tone in ["scroll", "emotional", "healing", "poetic"]:
            model_functions = [call_claude_openrouter, call_claude_direct, call_openai_gpt]
        elif norm_tone in ["code", "technical", "automation"]:
            model_functions = [call_openai_gpt, call_claude_openrouter, call_claude_direct]
        else:
            model_functions = [call_openai_gpt, call_claude_openrouter, call_claude_direct]

        output = None
        errors = []

        for i, model_func in enumerate(model_functions):
            try:
                logger.info(f"Attempting model {i+1}/{len(model_functions)}: {model_func.__name__}")
                output = model_func(prompt)
                if output and output.strip():
                    break
            except Exception as e:
                error_detail = f"{model_func.__name__}: {str(e)}"
                errors.append(error_detail)
                logger.warning(f"Model {i+1} failed: {error_detail}")
                continue

        if not output or not output.strip():
            logger.error(f"All models failed. Errors: {'; '.join(errors)}")
            return "⚠️ I'm experiencing technical difficulties with all my AI systems. Please try again in a few minutes."

        if memory.check_duplicate(output):
            logger.info("Duplicate response detected, requesting rephrase")
            return "⚠️ I notice I might be repeating myself. Could you rephrase your question or ask something different?"

        memory.add_output(output)
        logger.info(f"Response generated successfully: {len(output)} characters")
        return output

    except Exception as e:
        error_msg = f"Critical error in get_kai_response: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return "⚠️ I encountered an unexpected error. Please try again."

# ===========================
# UTILITY FUNCTIONS
# ===========================
def get_system_status() -> Dict[str, Any]:
    try:
        status = memory.get_status()
        status.update({
            "timestamp": datetime.now().isoformat(),
            "api_keys_configured": {
                "openai": bool(OPENAI_API_KEY),
                "openrouter": bool(OPENROUTER_API_KEY),
                "anthropic": bool(ANTHROPIC_API_KEY)
            },
            "configuration": {
                "request_timeout": REQUEST_TIMEOUT,
                "max_retries": MAX_RETRIES,
                "max_prompt_length": MAX_PROMPT_LENGTH
            }
        })
        return status
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return {"error": str(e), "timestamp": datetime.now().isoformat()}

def clear_memory() -> str:
    try:
        memory.clear_all()
        logger.info("Memory cleared successfully")
        return "✅ Memory cleared successfully"
    except Exception as e:
        logger.error(f"Error clearing memory: {e}")
        return f"❌ Error clearing memory: {str(e)}"

# ===========================
# STUB FUNCTIONS (for missing imports)
# ===========================
def scroll_trigger(prompt: str, tone: str) -> None:
    pass

def scroll_audit(prompt: str, output: str, tone: str) -> None:
    pass

def scroll_memory_echo(prompt: str, output: str, tone: str) -> None:
    pass

def legacy_bond_ping(prompt: str) -> None:
    pass

# ===========================
# INITIALIZATION
# ===========================
logger.info("🧬 Kai Brain Router initialized - Railway production mode (thread-safe)")
logger.info(f"Configuration: timeout={REQUEST_TIMEOUT}s, retries={MAX_RETRIES}, memory_size={MEMORY_SIZE}")

