from flask import Flask, request, jsonify
from kai_brain_router import get_kai_response
import os

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return "Kai Omniseal is alive and listening."

@app.route('/api/message', methods=['POST'])
def api_message():
    data = request.get_json(force=True)
    prompt = data.get('message', '')
    tone = data.get('tone', 'neutral')
    kai_reply = get_kai_response(prompt, tone)
    return jsonify({'reply': kai_reply})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
