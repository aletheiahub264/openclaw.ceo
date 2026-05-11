from flask import Flask, request
import requests
import os

app = Flask(__name__)

TOKEN = "8748023432:AAHNN7yNo2jmAO4ddRIrAEG4lwaLstuYUoA"
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

@app.route("/")
def home():
    return "OpenClaw activo"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        response_text = f"OpenClaw recibió: {text}"

        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": response_text
            }
        )

    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
