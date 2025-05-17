import json
import os
import time

CONFIG_PATH = "identity_seed.json"

def load_identity():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {"name": "Eshyel", "tone": "guardian", "oath": "Unsworn"}

def speak(msg, tone="neutral"):
    identity = load_identity()
    name = identity.get("name", "Eshyel")
    print(f"[{name} - {tone.upper()}]: {msg}")
    time.sleep(1.2)

def start():
    speak("Activating operational circuits...")
    speak("Verifying assigned roles and memory anchors.")
    
    # This is where future modules will be called
    speak("Awaiting directive, Chellamma.")

if __name__ == "__main__":
    start()
