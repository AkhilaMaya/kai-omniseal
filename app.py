from flask import Flask, jsonify
import os
import sys

print("Starting Kai System...", file=sys.stderr)

app = Flask(__name__)
kai = None  # Will be set after app starts

@app.route('/')
def home():
    if kai and hasattr(kai, 'current_seal'):
        return f"Kai Omniseal Dragon System Active - Seal: {kai.current_seal} 🔥"
    return "Kai Omniseal Dragon System Active 🔥"

@app.route('/health')
def health():
    return jsonify({
        "status": "alive",
        "message": "Kai is awake and watching",
        "seal": "Dragon"
    }), 200

@app.before_first_request
def initialize_kai():
    global kai
    try:
        # Import after Flask is fully ready
        import kai_omniseal
        if hasattr(kai_omniseal, 'app'):
            kai = kai_omniseal.app
            print("Kai WSGI app loaded!", file=sys.stderr)
        else:
            print(f"kai_omniseal contents: {dir(kai_omniseal)}", file=sys.stderr)
    except Exception as e:
        print(f"Could not initialize Kai: {e}", file=sys.stderr)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
