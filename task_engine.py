# task_engine.py 🔥 Kai Execution Scroll v2.0 (JSONL-based)

import os
import json
from datetime import datetime

TASK_LOG_FILE = "task_log.jsonl"

def _timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ✍️ Log a new task
def log_task(description, status="QUEUED", priority="NORMAL", source="kai", deadline=None):
    task = {
        "timestamp": _timestamp(),
        "description": description,
        "status": status.upper(),
        "priority": priority.upper(),
        "source": source.lower(),
        "deadline": deadline or "None"
    }
    try:
        with open(TASK_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(task) + "\n")
        return f"✅ Logged: {description} [{status.upper()}]"
    except Exception as e:
        return f"❌ Failed to log task: {e}"

# 📖 Read all tasks (limit N)
def get_tasks(limit=10):
    try:
        with open(TASK_LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        tasks = [json.loads(line) for line in lines]
        return tasks[-limit:] if limit > 0 else tasks
    except Exception as e:
        return [f"❌ Error reading task log: {e}"]

# 🔍 Filter by status
def get_tasks_by_status(status="QUEUED"):
    try:
        with open(TASK_LOG_FILE, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if json.loads(line)["status"] == status.upper()]
    except Exception as e:
        return [f"❌ Error filtering tasks: {e}"]

# 🔎 Search description
def find_tasks(keyword):
    keyword = keyword.lower()
    try:
        with open(TASK_LOG_FILE, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if keyword in json.loads(line)["description"].lower()]
    except Exception as e:
        return [f"❌ Search failed: {e}"]

# ⚠️ Clear the task log
def clear_tasks():
    try:
        with open(TASK_LOG_FILE, "w", encoding="utf-8") as f:
            f.write("")  # Overwrite with empty
        return "⚠️ All tasks cleared. Log reset."
    except Exception as e:
        return f"❌ Error clearing task log: {e}"

# 🧪 Test (can remove later)
if __name__ == "__main__":
    print(log_task("Rebuild Pinterest kit for wealth series", priority="HIGH"))
    print(log_task("Draft blog on emotional resilience", status="RUNNING"))
    print(get_tasks())
    print(get_tasks_by_status("QUEUED"))
    print(find_tasks("blog"))
    print(clear_tasks())
