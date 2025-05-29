from flask import Flask, jsonify
import os
import sys

print("Starting Kai System...", file=sys.stderr)

try:
    from kai_omniseal import KaiOmniseal
    kai = KaiOmniseal()
    print("Kai Omniseal loaded successfully!", file=sys.stderr)
except Exception as e:
    print(f"Error loading Kai: {e}", file=sys.stderr)
    kai = None

app = Flask(__name__)

@app.route('/')
def home():
    if kai:
        return f"Kai Omniseal Dragon System Active - Seal: {kai.current_seal} 🔥"
    return "Kai System Starting..."

@app.route('/health')
def health():
    return jsonify({
        "status": "alive", 
        "kai_loaded": kai is not None
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
