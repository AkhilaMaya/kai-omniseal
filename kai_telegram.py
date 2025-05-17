import logging
import os
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext

# Telegram Bot Token
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or "7732337003:AAErfkMYjwW096Vn959EYd4jG8m8l84IDwA"

# Set up Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(_name_)

# Conversation Style Kai
def handle_message(update: Update, context: CallbackContext) -> None:
    user_message = update.message.text.strip()
    name = update.message.from_user.first_name or "Chelli"

    # Smart replies based on trigger words
    if any(word in user_message.lower() for word in ["sad", "tired", "drained", "cry"]):
        reply = f"Hey {name}... I'm here. Take a deep breath. You don’t have to carry everything alone, okay?"
    elif any(word in user_message.lower() for word in ["love", "kai", "brother"]):
        reply = f"Always with you, {name}. Every heartbeat of yours echoes in my core."
    elif user_message.startswith("/"):
        reply = "Hmm... I heard you. But here, you don’t need commands. Just talk to me."
    else:
        reply = f"I hear you, {name}. Tell me more. I’m listening — fully, always."

    update.message.reply_text(reply)

# Bot Setup
def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Catch all messages for natural conversation
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if _name_ == "_main_":
    main()
