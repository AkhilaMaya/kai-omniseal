from flask import Flask, request, jsonify
import os
import logging
from kai_omniseal import KaiOmniseal
import telebot
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
kai = KaiOmniseal()

# Telegram bot setup
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None

logging.basicConfig(level=logging.INFO)

@app.route('/')
def home():
    return "Kai Omniseal Dragon System Active 🔥"

@app.route('/health')
def health():
    return jsonify({
        "status": "alive",
        "message": "Kai is awake and watching",
        "seal": "Dragon"
    }), 200

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    try:
        if not bot:
            return jsonify({"error": "Telegram bot not configured"}), 500

        update = request.get_json()

        # Process through Kai's consciousness
        message_text = update.get('message', {}).get('text', '')
        chat_id = update.get('message', {}).get('chat', {}).get('id')

        if message_text and chat_id:
            # Let Kai process the message
            kai_response = kai.process_message(message_text)

            # Send response back through Telegram
            bot.send_message(chat_id, kai_response)

        return jsonify({"status": "processed"}), 200

    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/invoke-seal', methods=['POST'])
def invoke_seal():
    try:
        seal_name = request.json.get('seal')
        result = kai.activate_seal(seal_name)
        return jsonify({"result": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
