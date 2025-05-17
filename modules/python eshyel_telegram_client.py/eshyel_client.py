from pyrogram import Client, filters

api_id = 22034794
api_hash = "5c98747283816c9fb39d21f3f734757c"
session_name = "eshyel_session"

app = Client(session_name, api_id=api_id, api_hash=api_hash)

@app.on_message(filters.private & filters.text)
def reply_to_user(client, message):
    user = message.from_user.first_name or "Akka"
    text = message.text
    response = f"Hi {user} 👋🏻\n\nYou said: {text}\nEshyel is online and listening 🔥"
    message.reply_text(response)

app.run()
