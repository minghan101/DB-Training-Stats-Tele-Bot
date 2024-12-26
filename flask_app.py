from flask import Flask, request
from telegram.ext import Application
from env import API_KEY

app = Flask(__name__)

# Your bot setup
application = Application.builder().token(API_KEY).build()

@app.route(f"/{API_KEY}", methods=["POST"])
def webhook():
    update = request.get_json(force=True)
    application.update_queue.put_nowait(update)
    return "OK"

if __name__ == "__main__":
    app.run()
