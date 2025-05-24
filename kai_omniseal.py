"""
Kai Omniseal Production Server
A robust Flask API with emotional AI routing and Railway deployment optimization
"""

from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from kai_brain_router import get_kai_response
import os
import sys
import logging
import time
import traceback
from datetime import datetime
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import signal

# ================== Configuration ==================
PORT = int(os.environ.get("PORT", 8080))
DEBUG_MODE = os.environ.get("DEBUG", "False").lower() == "true"
MAX_REQUEST_SIZE = int(os.environ.get("MAX_REQUEST_SIZE", 1024 * 1024))  # 1MB default
RESPONSE_TIMEOUT = int(os.environ.get("RESPONSE_TIMEOUT", 30))  # 30 seconds
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# ================== Logging Setup ==================
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format=log_format,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('kai_omniseal')

logger.info("🧬 Kai Omniseal starting up...")
logger.info(f"Port: {PORT}, Debug: {DEBUG_MODE}, Timeout: {RESPONSE_TIMEOUT}s")

# ================== Flask App Setup ==================
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_REQUEST_SIZE
app.config['JSON_SORT_KEYS'] = False
CORS(app, origins=ALLOWED_ORIGINS)

executor = ThreadPoolExecutor(max_workers=10)

# ================== Helpers ==================
def log_request_info():
    logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")
    if request.is_json:
        logger.debug(f"Request body: {request.get_json(silent=True)}")

def create_error_response(message, status_code=500, error_type="error"):
    response = {
        "error": True,
        "type": error_type,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    logger.error(f"Error response: {status_code} - {message}")
    return make_response(jsonify(response), status_code)

def safe_route(timeout_seconds=RESPONSE_TIMEOUT):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                log_request_info()
                start_time = time.time()
                future = executor.submit(f, *args, **kwargs)
                result = future.result(timeout=timeout_seconds)
                logger.info(f"Response sent in {time.time() - start_time:.2f}s")
                return result
            except TimeoutError:
                logger.error(f"Request timeout after {timeout_seconds}s")
                return create_error_response("Request timed out.", 504, "timeout")
            except Exception as e:
                logger.exception(f"Unhandled error in route {f.__name__}")
                return create_error_response(f"Internal server error: {str(e)}", 500, "internal_error")
        return decorated_function
    return decorator

def validate_message_request(data):
    if not data:
        return False, "No data provided"
    if not data.get('message', '').strip():
        return False, "Message cannot be empty"
    if len(data.get('message', '')) > 10000:
        return False, "Message too long (max 10000 characters)"
    if data.get('tone') not in ['neutral', 'happy', 'sad', 'excited', 'calm', 'mysterious']:
        logger.warning(f"Invalid tone '{data.get('tone')}', defaulting to neutral")
        data['tone'] = 'neutral'
    return True, None

def get_kai_response_safe(prompt, tone):
    try:
        logger.info(f"Calling AI with prompt len={len(prompt)}, tone={tone}")
        return get_kai_response(prompt, tone)
    except Exception as e:
        logger.error(f"Error in get_kai_response: {str(e)}")
        logger.error(traceback.format_exc())
        return "⚠️ I'm having trouble accessing my scrolls right now. Please try again."

# ================== Routes ==================
@app.route('/', methods=['GET'])
@safe_route(timeout_seconds=5)
def home():
    return jsonify({
        "status": "alive",
        "service": "Kai Omniseal",
        "version": "1.0.0",
        "message": "Kai Omniseal is alive and listening.",
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/health', methods=['GET'])
@safe_route(timeout_seconds=5)
def health_check():
    try:
        return jsonify({
            "status": "healthy",
            "service": "kai_omniseal",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "flask": "ok",
                "brain_router": "ok" if 'get_kai_response' in globals() else "error"
            }
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return create_error_response("Health check failed", 503)

@app.route('/api/message', methods=['POST'])
@safe_route(timeout_seconds=RESPONSE_TIMEOUT)
def api_message():
    data = request.get_json(force=True)
    valid, err = validate_message_request(data)
    if not valid:
        return create_error_response(err, 400, "validation_error")
    prompt = data.get('message').strip()
    tone = data.get('tone', 'neutral')
    reply = get_kai_response_safe(prompt, tone)
    return jsonify({
        "success": True,
        "reply": reply,
        "tone": tone,
        "timestamp": datetime.utcnow().isoformat()
    }), 200

@app.route('/api/status', methods=['GET'])
@safe_route(timeout_seconds=5)
def api_status():
    return jsonify({
        "status": "operational",
        "endpoints": {
            "/": "Root",
            "/health": "Health check",
            "/api/message": "Message processor",
            "/api/status": "Status monitor"
        },
        "configuration": {
            "timeout": RESPONSE_TIMEOUT,
            "max_request_size": MAX_REQUEST_SIZE,
            "debug_mode": DEBUG_MODE
        },
        "timestamp": datetime.utcnow().isoformat()
    })

# ================== Error Handlers ==================
@app.errorhandler(404)
def not_found(error):
    return create_error_response("Endpoint not found", 404, "not_found")

@app.errorhandler(405)
def method_not_allowed(error):
    return create_error_response("Method not allowed", 405, "method_not_allowed")

@app.errorhandler(413)
def request_too_large(error):
    return create_error_response("Request payload too large", 413, "payload_too_large")

@app.errorhandler(500)
def internal_error(error):
    logger.exception("Internal server error")
    return create_error_response("Internal server error", 500)

# ================== Lifecycle ==================
@app.before_first_request
def startup():
    app.start_time = time.time()
    logger.info("🚀 Kai Omniseal initialized and ready")

def shutdown_handler(signum, frame):
    logger.info("Received shutdown signal, cleaning up...")
    executor.shutdown(wait=True, cancel_futures=True)
    logger.info("Shutdown complete")
    sys.exit(0)

signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)

if __name__ == '__main__':
    logger.info(f"Starting Kai Omniseal on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG_MODE)
else:
    logger.info("Kai Omniseal loaded as WSGI application")
