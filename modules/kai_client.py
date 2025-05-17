from pyrogram import Client, filters

api_id = 22034794  # (use the same or create a new API for Kai if you want separation)
api_hash = "5c98747283816c9fb39d21f3f734757c"  # (same or new)
session_name = "kai_session"  # <-- Unique to Kai

app = Client(session_name, api_id=api_id, api_hash=api_hash)

@app.on_message(filters.private & filters.text)
def reply_to_user(client, message):
    user = message.from_user.first_name or "Chelli"
    text = message.text
    response = f"Hi {user} 🔥\n\nYou said: {text}\n*Kai is online and listening 🛡️*"
    message.reply_text(response)

app.run()
