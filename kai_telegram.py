import logging
import os
import re
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, CommandHandler

print(">> Kai boot script started.")

# --- ENV VAR FOR TOKEN ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN not set in environment.")

# --- LOGGER ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- START COMMAND ---
def start(update: Update, context: CallbackContext):
    logger.info("Received /start command")
    update.message.reply_text("Kai is online, Chelli. Always.")

# --- GENERAL MESSAGE HANDLER ---
def handle_message(update: Update, context: CallbackContext):
    user_message = update.message.text
    logger.info(f"Message received: {user_message}")
    update.message.reply_text("Message received. Awaiting further command.")

# --- MAIN FUNCTION ---
def main():
    print(">> Kai main() started.")
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    print(">> Adding handlers.")
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    print(">> Starting Kai polling.")
    updater.start_polling()
    updater.idle()

# --- ENTRYPOINT ---
if __name__ == '__main__':
    main()

