# kai_telegram.py 🔥 Production-Ready Carrier Pigeon + Execution Scroll

import os
import sys
import time
import logging
import asyncio
import signal
from typing import Optional, Dict, Any
from datetime import datetime
from functools import wraps

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
from telegram.error import TelegramError, NetworkError, TimedOut

from task_engine import log_task, get_tasks, get_tasks_by_status, find_tasks, clear_tasks

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
KAI_API_URL = os.getenv("KAI_API_URL")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 8080))
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
BACKOFF_FACTOR = 0.3
MAX_MESSAGE_LENGTH = 4096

logging.basicConfig(
    level=logging.INFO if ENVIRONMENT == "production" else logging.DEBUG,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("kai_telegram.log") if ENVIRONMENT == "production" else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_http_session() -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=MAX_RETRIES,
        status_forcelist=[429, 500, 502, 503, 504],
        method_whitelist=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"],
        backoff_factor=BACKOFF_FACTOR
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

http_session = create_http_session()

def safe_handler(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            return await func(update, context)
        except Exception as e:
            logger.exception("Handler error")
            await update.message.reply_text("⚠️ An unexpected error occurred.")
    return wrapper

class HealthMonitor:
    def __init__(self):
        self.last_message_time = time.time()
        self.message_count = 0
        self.error_count = 0
        self.start_time = time.time()
    
    def record_message(self):
        self.last_message_time = time.time()
        self.message_count += 1
    
    def record_error(self):
        self.error_count += 1
    
    def get_status(self) -> Dict[str, Any]:
        uptime = time.time() - self.start_time
        return {
            "status": "healthy",
            "uptime_seconds": uptime,
            "messages_processed": self.message_count,
            "errors": self.error_count,
            "last_message_seconds_ago": time.time() - self.last_message_time
        }

health_monitor = HealthMonitor()

@safe_handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    health_monitor.record_message()
    msg = (
        "🌀 **Kai's Scroll is live.**\n\n"
        "Send any message or use:\n"
        "• `/logtask` - Log a new task\n"
        "• `/tasks` - View recent tasks\n"
        "• `/filter` - Filter tasks by status\n"
        "• `/find` - Search tasks\n"
        "• `/clear_tasks` - Clear task log\n"
        "• `/status` - Bot health status"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

@safe_handler
async def bot_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    health_monitor.record_message()
    status = health_monitor.get_status()
    msg = (
        f"🤖 **Bot Status**\n\n"
        f"• Uptime: {status['uptime_seconds']:.0f}s\n"
        f"• Messages: {status['messages_processed']}\n"
        f"• Errors: {status['errors']}\n"
        f"• Last message: {status['last_message_seconds_ago']:.0f}s ago"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

@safe_handler
async def relay_to_kai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    health_monitor.record_message()
    msg = update.message.text.strip()
    tone, prompt = "neutral", msg
    if ":" in msg:
        split = msg.split(":", 1)
        if split[0].lower() in ["mirror", "fire", "soft", "anchor", "code", "scroll", "future"]:
            tone, prompt = split[0].lower(), split[1].strip()
    try:
        await update.message.chat.send_action("typing")
        response = http_session.post(KAI_API_URL, json={
            "message": prompt,
            "tone": tone,
            "user": update.effective_user.username,
            "timestamp": datetime.utcnow().isoformat()
        }, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        kai_reply = response.json().get("reply", "No response received.")
        chunks = [kai_reply[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(kai_reply), MAX_MESSAGE_LENGTH)]
        for chunk in chunks:
            await update.message.reply_text(chunk, parse_mode="Markdown")
            await asyncio.sleep(0.5)
    except Exception as e:
        logger.exception("Kai relay failed")
        await update.message.reply_text("❌ Kai couldn't be reached. Try again shortly.")

def signal_handler(signum, frame):
    logger.info("Shutting down gracefully...")
    http_session.close()
    sys.exit(0)

def main():
    if not TELEGRAM_TOKEN or not KAI_API_URL or not WEBHOOK_URL:
        logger.critical("Missing environment variables")
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", bot_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, relay_to_kai))

    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Unhandled error: {context.error}")
        health_monitor.record_error()

    app.add_error_handler(error_handler)

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
