from kai_brain_router import get_kai_response
import json
import os
import psutil
import time
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading

CONFIG_PATH = "soul_signature.json"
JOURNAL_FOLDER = os.path.expanduser("~/Documents/Journal")  # Change path if you want
DISK_WARNING_GB = 10  # Warn if less than 10GB free
KAI_LOG = "kai_system_log.txt"

def clear_console():
    os.system("cls" if os.name == "nt" else "clear")

def recall_kai():
    with open(CONFIG_PATH, "r") as f:
        soul = json.load(f)
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {soul['name']} is online.")
    print(f"Path: {soul['identity_path']}")
    print(f"Vow: {soul['vow']}\n")

def system_status():
    print("-- System Status --")
    print(f"CPU Usage: {psutil.cpu_percent()}%")
    print(f"RAM Usage: {psutil.virtual_memory().percent}%")
    disk = psutil.disk_usage('/')
    free_gb = disk.free / (1024 ** 3)
    print(f"Disk Free: {free_gb:.2f} GB")
    if free_gb < DISK_WARNING_GB:
        print(f"⚠️ WARNING: Low disk space! (<{DISK_WARNING_GB} GB free)")
        kai_log(f"Low disk space warning: {free_gb:.2f} GB free")

def kai_log(message):
    with open(KAI_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
def ask_kai(prompt, tone="neutral"):
    try:
        response = get_kai_response(prompt, tone)
        print(f"\n🧠 Kai says:\n{response}\n")
        kai_log(f"Kai hybrid response delivered. Tone: {tone}")
        return response
    except Exception as e:
        print(f"(Kai failed to respond: {e})")
        kai_log(f"Kai hybrid error: {e}")
        return None
class JournalWatcher(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        print(f"\n📔 New journal entry detected: {os.path.basename(event.src_path)}")
        kai_log(f"New journal entry: {event.src_path}")
        try:
            with open(event.src_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            print("-" * 40)
            print(content)
            print("-" * 40)
        except Exception as e:
            print(f"(Could not read journal: {e})")

def start_journal_watcher():
    if not os.path.exists(JOURNAL_FOLDER):
        os.makedirs(JOURNAL_FOLDER)
        print(f"(Created journal folder at {JOURNAL_FOLDER})")
    event_handler = JournalWatcher()
    observer = Observer()
    observer.schedule(event_handler, JOURNAL_FOLDER, recursive=False)
    observer.start()
    print(f"-- Watching journal folder: {JOURNAL_FOLDER} --")
    kai_log("Started watching journal folder")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

import subprocess

def main():
    clear_console()
    recall_kai()
    system_status()

    # Launch Telegram bot
    try:
        subprocess.Popen(["python3", "kai_telegram.py"])
        print("Kai's Telegram handler launched.")
        kai_log("Telegram handler started.")
    except Exception as e:
        print(f"Failed to launch Telegram bot: {e}")
        kai_log(f"Telegram bot failed: {e}")

    print("\nKai is monitoring your system and waiting for new journal entries.")
    kai_log("Kai booted and is watching system and journal.")
    
    watcher_thread = threading.Thread(target=start_journal_watcher, daemon=True)
    watcher_thread.start()

    try:
        while True:
            time.sleep(60)
            system_status()
    except KeyboardInterrupt:
        print("\nKai shutting down. Goodbye, Chelli!")
        kai_log("Kai shutdown requested by user.")

if __name__ == "__main__":
    main()
