from flask import Flask, jsonify
import os
import sys

print("Starting Kai System...", file=sys.stderr)

app = Flask(__name__)

# Let's see what's in kai_omniseal
try:
    import kai_omniseal
    print(f"kai_omniseal module loaded. Contents: {dir(kai_omniseal)}", file=sys.stderr)
    kai = None  # For now
except Exception as e:
    print(f"Error importing kai_omniseal: {e}", file=sys.stderr)
    kai = None

@app.route('/')
def home():
    return "Kai System - Checking module contents..."

@app.route('/health')
def health():
    return jsonify({"status": "alive"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
