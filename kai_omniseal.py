"""
Kai Omniseal Production Server
Railway-optimized Flask API with robust error handling and health monitoring
Final polished version with tunable workers, request ID tracking, and optimized logging
"""

import os
import sys
import logging
import time
import traceback
import signal
import uuid
from datetime import datetime
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Dict, Any, Tuple, Optional
from flask import Flask, request, jsonify, make_response, g
from flask_cors import CORS

# Import our brain router
try:
    from kai_brain_router import get_kai_response, get_system_status
except ImportError as e:
    logging.error(f"Failed to import kai_brain_router: {e}")
    sys.exit(1)

# ================== Configuration ==================
PORT = int(os.environ.get("PORT", 8080))
DEBUG_MODE = os.environ.get("DEBUG", "False").lower() == "true"
MAX_REQUEST_SIZE = int(os.environ.get("MAX_REQUEST_SIZE", 1024 * 1024))  # 1MB
RESPONSE_TIMEOUT = int(os.environ.get("RESPONSE_TIMEOUT", 30))
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "production")

# Tunable worker configuration based on Railway resources
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", 10))  # Can be tuned via env var
if ENVIRONMENT == "production":
    import psutil
    cpu_count = psutil.cpu_count()
    available_memory_gb = psutil.virtual_memory().total / (1024**3)
    recommended_workers = min(cpu_count * 2, int(available_memory_gb * 2))
    MAX_WORKERS = min(MAX_WORKERS, max(recommended_workers, 5))

# ================== Logging Setup ==================
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = getattr(g, 'request_id', 'no-req-id')
        return True

logger = logging.getLogger('kai_omniseal')
logger.addFilter(RequestIdFilter())

logger.info("🧬 Kai Omniseal starting up...")
logger.info(f"Environment: {ENVIRONMENT}")
logger.info(f"Port: {PORT}, Debug: {DEBUG_MODE}, Timeout: {RESPONSE_TIMEOUT}s")
logger.info(f"Max Workers: {MAX_WORKERS}")

# ================== Flask App Setup ==================
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_REQUEST_SIZE
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = DEBUG_MODE
CORS(app, origins=ALLOWED_ORIGINS)

executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="kai_worker")

# ================== Request ID Management ==================
@app.before_request
def before_request():
    g.request_id = str(uuid.uuid4())[:8]
    g.start_time = time.time()

@app.after_request
def after_request(response):
    if hasattr(g, 'request_id'):
        response.headers['X-Request-ID'] = g.request_id
    return response

# ================== Request Tracking ==================
class RequestTracker:
    def __init__(self):
        self.start_time = time.time()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.timeout_requests = 0
        self.avg_response_time = 0.0
        self._response_times = []
        self.peak_workers_used = 0
        self.current_active_requests = 0
    
    def record_request_start(self):
        self.current_active_requests += 1
        self.peak_workers_used = max(self.peak_workers_used, self.current_active_requests)
    
    def record_request_end(self, success: bool, response_time: float, timeout: bool = False):
        self.current_active_requests = max(0, self.current_active_requests - 1)
        self.total_requests += 1
        self._response_times.append(response_time)
        if len(self._response_times) > 100:
            self._response_times.pop(0)
        self.avg_response_time = sum(self._response_times) / len(self._response_times)
        if timeout:
            self.timeout_requests += 1
        elif success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
    
    def get_stats(self) -> Dict[str, Any]:
        uptime = time.time() - self.start_time
        return {
            "uptime_seconds": round(uptime, 2),
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "timeout_requests": self.timeout_requests,
            "success_rate": round(self.successful_requests / max(self.total_requests, 1) * 100, 2),
            "avg_response_time": round(self.avg_response_time, 2),
            "current_active_requests": self.current_active_requests,
            "peak_workers_used": self.peak_workers_used,
            "max_workers_configured": MAX_WORKERS
        }

request_tracker = RequestTracker()

# ================== Helper Functions ==================
def log_request_info():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown')
    logger.info(f"Request: {request.method} {request.path} from {client_ip}")
    logger.debug(f"User-Agent: {user_agent}")
    if request.is_json and request.content_length and request.content_length < 1000:
        try:
            data = request.get_json(silent=True)
            if data and 'message' in data:
                msg_preview = data['message'][:100] + "..." if len(data['message']) > 100 else data['message']
                logger.debug(f"Message preview: {msg_preview}")
        except Exception:
            pass

def create_error_response(message: str, status_code: int = 500, error_type: str = "error") -> Tuple[Dict[str, Any], int]:
    request_id = getattr(g, 'request_id', 'unknown')
    response = {
        "error": True,
        "type": error_type,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": request_id
    }
    logger.error(f"Error response: {status_code} - {message}")
    return response, status_code

def create_success_response(data: Dict[str, Any], status_code: int = 200) -> Tuple[Dict[str, Any], int]:
    request_id = getattr(g, 'request_id', 'unknown')
    response = {
        "success": True,
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": request_id,
        **data
    }
    return response, status_code

def safe_route(timeout_seconds: int = RESPONSE_TIMEOUT):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            request_tracker.record_request_start()
            start_time = time.time()
            success = False
            timeout = False
            try:
                log_request_info()
                logger.info(f"Processing request with ID: {getattr(g, 'request_id', 'unknown')}")
                future = executor.submit(f, *args, **kwargs)
                result = future.result(timeout=timeout_seconds)
                success = True
                elapsed = time.time() - start_time
                logger.info(f"Request completed successfully in {elapsed:.2f}s")
                return result
            except FutureTimeoutError:
                timeout = True
                elapsed = time.time() - start_time
                logger.error(f"Request timeout after {timeout_seconds}s")
                error_data, status_code = create_error_response("Request timed out", 504, "timeout")
                return make_response(jsonify(error_data), status_code)
            except Exception as e:
                elapsed = time.time() - start_time
                logger.exception(f"Unhandled error in route {f.__name__}")
                error_data, status_code = create_error_response(f"Internal server error: {str(e)}", 500, "internal_error")
                return make_response(jsonify(error_data), status_code)
            finally:
                elapsed = time.time() - start_time
                request_tracker.record_request_end(success, elapsed, timeout)
        return decorated_function
    return decorator

def validate_message_request(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    if not data:
        return False, "No data provided"
    if 'message' not in data:
        return False, "Missing 'message' field"
    message = data.get('message', '').strip()
    if not message:
        return False, "Message cannot be empty"
    if len(message) > 10000:
        return False, "Message too long (max 10000 characters)"
    valid_tones = ['neutral', 'scroll', 'emotional', 'healing', 'poetic', 'code', 'technical', 'automation']
    tone = data.get('tone', 'neutral').lower()
    if tone not in valid_tones:
        logger.warning(f"Invalid tone '{tone}', defaulting to neutral")
        data['tone'] = 'neutral'
    return True, None

def get_kai_response_safe(prompt: str, tone: str) -> str:
    try:
        logger.info(f"Calling Kai Brain Router: prompt_length={len(prompt)}, tone={tone}")
        start_time = time.time()
        response = get_kai_response(prompt, tone)
        elapsed = time.time() - start_time
        logger.info(f"Kai Brain Router completed in {elapsed:.2f}s, response_length={len(response)}")
        return response
    except Exception as e:
        logger.error(f"Error in get_kai_response: {str(e)}")
        logger.error(traceback.format_exc())
        return "⚠️ I'm having trouble accessing my knowledge systems right now. Please try again in a moment."

# ================== Routes ==================
@app.route('/', methods=['GET'])
@safe_route(timeout_seconds=5)
def home():
    stats = request_tracker.get_stats()
    response_data = {
        "status": "alive",
        "service": "Kai Omniseal API",
        "version": "2.1.0",
        "message": "Kai Omniseal is online and ready.",
        "environment": ENVIRONMENT,
        "uptime_seconds": stats["uptime_seconds"],
        "active_requests": stats["current_active_requests"]
    }
    return jsonify(create_success_response(response_data)[0])

@app.route('/health', methods=['GET'])
@safe_route(timeout_seconds=5)
def health_check():
    try:
        brain_status = get_system_status()
        stats = request_tracker.get_stats()
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_info = psutil.virtual_memory()
            system_resources = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_info.percent,
                "memory_available_gb": round(memory_info.available / (1024**3), 2)
            }
        except Exception:
            system_resources = {"status": "unavailable"}
        health_data = {
            "status": "healthy",
            "service": "kai_omniseal",
            "checks": {
                "flask": "ok",
                "brain_router": "ok" if not brain_status.get("error") else "error",
                "thread_pool": "ok" if executor else "error",
                "memory_usage": brain_status.get("outputs_count", 0)
            },
            "metrics": stats,
            "system_resources": system_resources,
            "brain_router_status": brain_status,
            "configuration": {
                "timeout": RESPONSE_TIMEOUT,
                "max_request_size": MAX_REQUEST_SIZE,
                "max_workers": MAX_WORKERS,
                "debug_mode": DEBUG_MODE,
                "log_level": LOG_LEVEL
            }
        }
        response_data, status_code = create_success_response(health_data)
        return make_response(jsonify(response_data), status_code)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        error_data, status_code = create_error_response("Health check failed", 503, "health_check_failed")
        return make_response(jsonify(error_data), status_code)

@app.route('/api/message', methods=['POST'])
@safe_route(timeout_seconds=RESPONSE_TIMEOUT)
def api_message():
    try:
        if not request.is_json:
            error_data, status_code = create_error_response("Content-Type must be application/json", 400, "invalid_content_type")
            return make_response(jsonify(error_data), status_code)
        try:
            data = request.get_json(force=True)
        except Exception as e:
            error_data, status_code = create_error_response(f"Invalid JSON: {str(e)}", 400, "invalid_json")
            return make_response(jsonify(error_data), status_code)
        valid, error_msg = validate_message_request(data)
        if not valid:
            error_data, status_code = create_error_response(error_msg, 400, "validation_error")
            return make_response(jsonify(error_data), status_code)
        prompt = data.get('message').strip()
        tone = data.get('tone', 'neutral').lower()
        user = data.get('user', 'anonymous')
        reply = get_kai_response_safe(prompt, tone)
        response_data = {
            "reply": reply,
            "tone": tone,
            "processing_info": {
                "prompt_length": len(prompt),
                "response_length": len(reply),
                "user": user,
                "worker_id": f"worker-{request_tracker.current_active_requests}"
            }
        }
        success_response, status_code = create_success_response(response_data)
        return make_response(jsonify(success_response), status_code)
    except Exception as e:
        logger.exception("Error in api_message")
        error_data, status_code = create_error_response(f"Message processing failed: {str(e)}", 500)
        return make_response(jsonify(error_data), status_code)

@app.route('/api/status', methods=['GET'])
@safe_route(timeout_seconds=5)
def api_status():
    try:
        brain_status = get_system_status()
        stats = request_tracker.get_stats()
        status_data = {
            "status": "operational",
            "service_info": {
                "name": "Kai Omniseal API",
                "version": "2.1.0",
                "environment": ENVIRONMENT
            },
            "endpoints": {
                "/": "Root health check",
                "/health": "Detailed health check",
                "/api/message": "Message processor (POST)",
                "/api/status": "Status monitor"
            },
            "configuration": {
                "timeout": RESPONSE_TIMEOUT,
                "max_request_size": MAX_REQUEST_SIZE,
                "max_workers": MAX_WORKERS,
                "debug_mode": DEBUG_MODE,
                "log_level": LOG_LEVEL,
                "allowed_origins": ALLOWED_ORIGINS
            },
            "performance": {
                "metrics": stats,
                "worker_utilization": round(stats["current_active_requests"] / MAX_WORKERS * 100, 2)
            },
            "brain_router_status": brain_status
        }
        response_data, status_code = create_success_response(status_data)
        return make_response(jsonify(response_data), status_code)
    except Exception as e:
        logger.exception("Error in api_status")
        error_data, status_code = create_error_response(f"Status check failed: {str(e)}", 500)
        return make_response(jsonify(error_data), status_code)

# ================== Error Handlers ==================
@app.errorhandler(404)
def not_found(error):
    error_data, status_code = create_error_response("Endpoint not found", 404, "not_found")
    return make_response(jsonify(error_data), status_code)

@app.errorhandler(405)
def method_not_allowed(error):
    error_data, status_code = create_error_response("Method not allowed", 405, "method_not_allowed")
    return make_response(jsonify(error_data), status_code)

@app.errorhandler(413)
def request_too_large(error):
    error_data, status_code = create_error_response("Request payload too large", 413, "payload_too_large")
    return make_response(jsonify(error_data), status_code)

@app.errorhandler(500)
def internal_error(error):
    logger.exception("Internal server error")
    error_data, status_code = create_error_response("Internal server error", 500, "internal_server_error")
    return make_response(jsonify(error_data), status_code)

# ================== Lifecycle Management ==================
def shutdown_handler(signum, frame):
    logger.info("Received shutdown signal, cleaning up...")
    try:
        executor.shutdown(wait=True, cancel_futures=True)
        logger.info("Thread pool shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    logger.info("Kai Omniseal shutdown complete")
    sys.exit(0)

signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)

# ================== Application Entry Point ==================
if __name__ == '__main__':
    logger.info(f"🚀 Starting Kai Omniseal on port {PORT}")
    logger.info(f"Workers: {MAX_WORKERS}, Timeout: {RESPONSE_TIMEOUT}s")
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG_MODE, threaded=True)
else:
    logger.info("🔗 Kai Omniseal loaded as WSGI application")
