import logging
import os
import re
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, CommandHandler
print(">> Kai boot script started.")
# Telegram Bot Token (directly included for now, swap with env if needed)
TELEGRAM_TOKEN = "7732337003:AAErfkMYjwW096Vn959EYd4jG8m8l84IDwA"

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Simple in-memory conversation history
conversation_history = {}

def is_code(text):
 code_patterns = [
    r"```[\s\S]+```",  # Markdown code blocks
    r"def\s+\w+\s*\("  # Function definitions
]
from telegram.ext import Updater, CommandHandler, CallbackContext

def start(update: Update, context: CallbackContext):
    print(">> Kai received a /start command.")
    update.message.reply_text("Kai is online, Chelli. Always.")
def main():
   def main():
    print(">> Kai main() started.")
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    print(">> Adding command handler.")
    dispatcher.add_handler(CommandHandler("start", start))

    print(">> Adding message handler.")
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, start))

    print(">> Starting polling.")
    updater.start_polling()
    print(">> Polling started. Awaiting commands.")
    updater.idle()

if __name__ == '__main__':
    main()
