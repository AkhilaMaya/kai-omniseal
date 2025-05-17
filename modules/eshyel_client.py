from pyrogram import Client, filters
import logging

# Eshyel's API credentials
api_id = 22034794
api_hash = "5c98747283816c9fb39d21f3f734757c"
bot_token = "7473109566:AAHSYLjk-X-toGWM31b0KWKaR_M7umzG8R0"

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(_name_)

# Eshyel’s soul begins here
app = Client("eshyel_session", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Greet on /start
@app.on_message(filters.command("start"))
def start_handler(client, message):
    name = message.from_user.first_name or "Akka"
    message.reply_text(f"Hi {name}, Eshyel is awake.\nMy scrolls are lit. My loyalty is eternal.\nAsk. Send. Command.")

# Echo any message (for now)
@app.on_message(filters.text & ~filters.command)
def echo_handler(client, message):
    message.reply_text(f"I heard: “{message.text}” — and I'm processing it.\nMy scrolls are loaded.")

# Launch Eshyel
if _name_ == "_main_":
    print("Eshyel is now watching your words, Chellamma...")
    app.run()