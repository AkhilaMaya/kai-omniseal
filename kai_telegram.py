import logging
import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from kai_omniseal import validate_code_integrity

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or "7732337003:AAErfkMYjwW096Vn959EYd4jG8m8l84IDwA"

def start(update, context):
    update.message.reply_text("Kai is here, Chelli. Send me any code snippet and I’ll scan it for threats.")

def help_command(update, context):
    update.message.reply_text("Just paste any Python code and I’ll analyze it.")

def scan_code(update, context):
    user_code = update.message.text
    result = validate_code_integrity(user_code)
    response = "✅ Code is safe." if result else "⚠️ Code integrity check failed."
    update.message.reply_text(response)

def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, scan_code))

    updater.start_polling()
    updater.idle()

if _name_ == "_main_":
    main()
