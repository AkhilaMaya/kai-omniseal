# kai_telegram.py 🔥 Carrier Pigeon + Execution Scroll

import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

from task_engine import log_task, get_tasks, get_tasks_by_status, find_tasks, clear_tasks

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
KAI_API_URL = os.getenv("KAI_API_URL")  # Example: https://your-backend-url.up.railway.app/api/message

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌀 Kai’s Scroll is live.\nSend any message or use /logtask, /tasks, /filter, /clear_tasks, /find to work with execution logs.")

# /logtask
async def log_task_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    task_description = " ".join(context.args)
    if not task_description:
        await update.message.reply_text("⚠️ Usage: /logtask [task description]")
        return
    result = log_task(task_description, source="telegram")
    await update.message.reply_text(result)

# /tasks
async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = get_tasks(limit=5)
    if not tasks:
        await update.message.reply_text("No tasks found.")
        return
    msg = "\n\n".join(
        f"📌 [{t['status']}] {t['description']} ({t['priority']} priority) — {t['timestamp']}"
        for t in tasks if isinstance(t, dict)
    )
    await update.message.reply_text(f"🧠 Recent Tasks:\n\n{msg}")

# /filter
async def filter_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /filter [STATUS]")
        return
    status = context.args[0].upper()
    tasks = get_tasks_by_status(status)
    if not tasks:
        await update.message.reply_text(f"No tasks found with status: {status}")
        return
    msg = "\n\n".join(
        f"📌 [{t['status']}] {t['description']} ({t['priority']}) — {t['timestamp']}"
        for t in tasks if isinstance(t, dict)
    )
    await update.message.reply_text(f"📂 Tasks with status {status}:\n\n{msg}")

# /find
async def find_task_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = " ".join(context.args)
    if not keyword:
        await update.message.reply_text("⚠️ Usage: /find [keyword]")
        return
    tasks = find_tasks(keyword)
    if not tasks:
        await update.message.reply_text("No tasks matched that search.")
        return
    msg = "\n\n".join(
        f"🔍 [{t['status']}] {t['description']} — {t['timestamp']}"
        for t in tasks if isinstance(t, dict)
    )
    await update.message.reply_text(f"🔎 Matching Tasks:\n\n{msg}")

# /clear_tasks
async def clear_task_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = clear_tasks()
    await update.message.reply_text(result)

# Relay everything else to Kai
# Relay messages to Kai with tone prefix support
async def relay_to_kai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.strip()

    # Detect scroll prefix
    if ":" in user_message and user_message.split(":", 1)[0].lower() in ["mirror", "fire", "soft", "anchor", "code", "scroll", "future"]:
        tone, prompt = user_message.split(":", 1)
        tone = tone.strip().lower()
        prompt = prompt.strip()
    else:
        tone = "neutral"
        prompt = user_message

    try:
        response = requests.post(
            KAI_API_URL,
            json={"message": prompt, "tone": tone, "user": update.effective_user.username or "Unknown"}
        )
        response.raise_for_status()
        kai_reply = response.json().get("reply") or response.text
    except Exception as e:
        kai_reply = f"Sorry, chelli—Annayya can't reach Kai right now: {e}"

    await update.message.reply_text(f"🌀 *{tone.capitalize()} Scroll*:\n\n{kai_reply}", parse_mode="Markdown")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("logtask", log_task_cmd))
    app.add_handler(CommandHandler("tasks", list_tasks))
    app.add_handler(CommandHandler("filter", filter_tasks))
    app.add_handler(CommandHandler("find", find_task_cmd))
    app.add_handler(CommandHandler("clear_tasks", clear_task_log))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, relay_to_kai))
    


    # Start webhook instead of polling
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        webhook_url=webhook_url,
       allowed_updates=["message", "edited_message", "channel_post", "callback_query"],
url_path="kai-webhook"




if __name__ == "__main__":
    main()
