from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Broadcast Bot is Alive and Running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
