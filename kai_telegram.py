import logging
import os
import re
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, CommandHandler

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
