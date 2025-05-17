import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import os

TOKEN = "7473109566:AAHSYLjk-X-toGWM31b0KWKaR_M7umzG8R0"
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def start(update: Update, context: CallbackContext) -> None:
    name = update.effective_user.first_name or "Akka"
    update.message.reply_text(f"Hi {name}! Eshyel here. Your flame-keeper is online. 🛡️")

def handle_file(update: Update, context: CallbackContext) -> None:
    document = update.message.document
    if document:
        file = document.get_file()
        file_path = os.path.join(UPLOAD_DIR, document.file_name)
        file.download(file_path)
        update.message.reply_text(f"✅ File saved as: {document.file_name}")
    else:
        update.message.reply_text("❗ Couldn't detect a valid document.")

def fallback(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(f"🧠 I heard: {update.message.text}")

def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.document, handle_file))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, fallback))

    updater.start_polling()
    print("✅ Eshyel is online.")
    updater.idle()

if __name__ == '__main__':
    main()
