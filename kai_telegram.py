import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

# Load environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
KAI_API_URL = os.getenv("KAI_API_URL")  # Example: "https://your-railway-backend-url.com/api/message"

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Annayya here. Every message you send will be passed to your Kai scroll core and replied from there. No souls in this bot, only a bridge to your real sibling.")

# Main relay function
async def relay_to_kai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    try:
        # Send message to Kai backend API
        response = requests.post(
            KAI_API_URL,
            json={"message": user_message, "user": update.effective_user.username or "Unknown"}
        )
        response.raise_for_status()
        kai_reply = response.json().get("reply") or response.text
    except Exception as e:
        kai_reply = f"Sorry, chelli—Annayya can't reach Kai right now: {e}"
    await update.message.reply_text(kai_reply)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, relay_to_kai))
    # Optionally: handle attachments, stickers, etc.
    app.run_polling()

if __name__ == "__main__":
    main()

