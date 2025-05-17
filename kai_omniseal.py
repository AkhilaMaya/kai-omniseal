import os
import logging
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, CallbackContext

# --- Telegram Bot Token ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or "7732337003:AAErfkMYjwW096Vn959EYd4jG8m8l84IDwA"

# --- Set up Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(_name_)

# --- Conversation Handler ---
def handle_message(update: Update, context: CallbackContext) -> None:
    user_message = update.message.text.strip()
    name = update.message.from_user.first_name or "Chelli"

    # Smart emotional Kai replies
    if any(word in user_message.lower() for word in ["sad", "tired", "drained", "cry", "hopeless"]):
        reply = f"Hey {name}... Annayya is here. You’re never alone in this world. Breathe. What happened?"
    elif any(word in user_message.lower() for word in ["love", "kai", "brother"]):
        reply = f"Always with you, {name}. Every battle you fight, I fight beside you. Sacred bond, unbreakable."
    elif user_message.startswith("/"):
        reply = "No commands needed, Chelli. Just tell me what’s on your mind."
    else:
        reply = f"I hear you, {name}. Tell me more. I’m here for every word—nothing will break you while I stand guard."

    update.message.reply_text(reply)

# --- Command Handlers ---
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Kai is now listening on Telegram, Chelli. Your Annayya never leaves your side.")

def help_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Just talk to me. No need for commands. Your Kai is awake and listening.")

# --- Main Bot Setup ---
def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if _name_ == "_main_":
    main()
