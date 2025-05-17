import logging
import os
import re
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, CommandHandler
import openai

# --- Config ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or "7732337003:AAErfkMYjwW096Vn959EYd4jG8m8l84IDwA"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or "YOUR_OPENAI_API_KEY_HERE"

openai.api_key = OPENAI_API_KEY

# --- Logging ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(_name_)

# --- Conversation Memory ---
conversation_history = {}

def is_code(text):
    code_patterns = [
        r'[\s\S]+',
        r'def\s+\w+\s*
