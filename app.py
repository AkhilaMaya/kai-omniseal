from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Kai System Starting - Phase 1"

@app.route('/health')
def health():
    return jsonify({"status": "alive", "phase": "initial"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
