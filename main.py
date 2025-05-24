"""
kai_omniseal.py (was main.py logic)
Production-ready Flask API combining:
- get_kai_response()
- Soul signature loader
- System monitor
- Telegram launcher
- Journal watcher
- Railway-compatible Flask web API
"""

from flask import Flask, jsonify, request
from kai_brain_router import get_kai_response
import os, sys, json, psutil, time, logging, threading, subprocess, signal
from datetime import datetime
from functools import wraps
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ==== CONFIG ====
CONFIG_PATH = "soul_signature.json"
JOURNAL_FOLDER = os.path.expanduser("~/Documents/Journal")
KAI_LOG = "kai_system_log.txt"
DISK_WARNING_GB = 10
REQUEST_TIMEOUT = 30
PORT = int(os.getenv("PORT", 8080))

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# ==== LOGGING ====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("kai_flask.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("KaiMainApp")

# ==== STATE ====
kai_config = None
telegram_process = None
observer = None

# ==== UTILITIES ====
def kai_log(msg):
    try:
        with open(KAI_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] {msg}\n")
    except Exception as e:
        logger.error(f"Log write error: {e}")

def load_soul_signature():
    global kai_config
    try:
        with open(CONFIG_PATH, "r") as f:
            kai_config = json.load(f)
            logger.info(f"Soul loaded: {kai_config['name']}")
            return kai_config
    except Exception as e:
        logger.error(f"Failed to load soul: {e}")
        return None

def get_system_status():
    try:
        disk = psutil.disk_usage('/')
        free = round(disk.free / (1024 ** 3), 2)
        status = {
            "cpu": psutil.cpu_percent(),
            "ram": psutil.virtual_memory().percent,
            "disk_free_gb": free,
            "disk_warning": free < DISK_WARNING_GB,
            "timestamp": datetime.now().isoformat()
        }
        if status["disk_warning"]:
            kai_log(f"⚠️ Low disk space: {free} GB free")
        return status
    except Exception as e:
        logger.error(f"System check error: {e}")
        return {}

# ==== JOURNAL WATCH ====
class JournalWatcher(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory: return
        try:
            with open(event.src_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            app.config['LATEST_JOURNAL'] = {
                "file": os.path.basename(event.src_path),
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            kai_log(f"📝 Journal added: {event.src_path}")
        except Exception as e:
            logger.error(f"Journal read error: {e}")

def start_journal_watcher():
    global observer
    if not os.path.exists(JOURNAL_FOLDER):
        os.makedirs(JOURNAL_FOLDER)
    event_handler = JournalWatcher()
    observer = Observer()
    observer.schedule(event_handler, JOURNAL_FOLDER, recursive=False)
    observer.start()
    logger.info(f"Journal watcher started on {JOURNAL_FOLDER}")
    kai_log("📔 Journal watcher activated")

# ==== TELEGRAM ====
def launch_telegram_bot():
    global telegram_process
    if not os.path.exists("kai_telegram.py"):
        logger.warning("kai_telegram.py not found")
        return
    try:
        telegram_process = subprocess.Popen(
            ["python3", "kai_telegram.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        kai_log("📡 Telegram bot launched")
    except Exception as e:
        logger.error(f"Telegram launch failed: {e}")
        kai_log(f"Telegram launch failed: {e}")

# ==== ERROR HANDLER ====
def route_errors(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Route error: {e}", exc_info=True)
            return jsonify({
                "error": "Internal error",
                "message": str(e)
            }), 500
    return decorated

# ==== ROUTES ====
@app.route("/")
def index():
    return jsonify({
        "status": "Kai is online",
        "name": kai_config["name"] if kai_config else "Unloaded",
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": "kai_main",
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route("/api/kai/ask", methods=["POST"])
@route_errors
def ask_kai():
    data = request.get_json()
    if not data or "prompt" not in data:
        return jsonify({"error": "Missing prompt"}), 400
    prompt = data["prompt"]
    tone = data.get("tone", "neutral")

    logger.info(f"Prompt received | Tone: {tone}")
    container = {"response": None, "error": None}

    def process():
        try:
            container["response"] = get_kai_response(prompt, tone)
        except Exception as e:
            container["error"] = str(e)

    t = threading.Thread(target=process)
    t.start()
    t.join(timeout=REQUEST_TIMEOUT)

    if t.is_alive():
        return jsonify({
            "error": "Kai took too long to respond",
            "timeout": REQUEST_TIMEOUT
        }), 504
    if container["error"]:
        raise Exception(container["error"])

    return jsonify({
        "response": container["response"],
        "tone": tone,
        "timestamp": datetime.now().isoformat()
    })

@app.route("/api/system/status")
def system():
    return jsonify(get_system_status())

@app.route("/api/soul/info")
def soul():
    if kai_config:
        return jsonify(kai_config)
    return jsonify({"error": "Soul not loaded"}), 503

@app.route("/api/journal/latest")
def journal():
    journal = app.config.get("LATEST_JOURNAL")
    if not journal:
        return jsonify({"message": "No journal entries yet"}), 404
    return jsonify(journal)

@app.route("/api/telegram/status")
def telegram_status():
    status = "running" if telegram_process and telegram_process.poll() is None else "offline"
    return jsonify({
        "telegram_bot": status,
        "timestamp": datetime.now().isoformat()
    })

# ==== STARTUP + CLEANUP ====
def init_kai():
    load_soul_signature()
    start_journal_watcher()
    launch_telegram_bot()
    kai_log("🛡 Kai initialized")

def shutdown_handler(signum, frame):
    logger.info("Shutting down...")
    if observer:
        observer.stop()
        observer.join()
    if telegram_process:
        telegram_process.terminate()
    kai_log("🧩 Kai shutdown complete")
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

@app.before_first_request
def startup():
    init_kai()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
