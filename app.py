from flask import Flask, request
import requests
from supabase import create_client

app = Flask(__name__)

# 🔥 TELEGRAM
TOKEN = "8748023432:AAHNN7yNo2jmAO4ddRIrAEG4lwaLstuYUoA"
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

# 🔥 SUPABASE
SUPABASE_URL = "https://mcjfaqtrygprcbjkhect.supabase.co"
SUPABASE_KEY = "sb_publishable_0Nqd3lazIAnzIEa1nb6Dxw_SDTT7uR-"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route("/")
def home():
    return "OpenClaw activo"

# 🧠 GUARDAR EN SUPABASE
def save_message(chat_id, message, response, mode):
    supabase.table("interactions").insert({
        "telegram_id": str(chat_id),
        "message": message,
        "response": response,
        "mode": mode
    }).execute()

# 🧠 ROUTER SIMPLE (CEO / PERSONAL)
def detect_mode(text):
    text = text.lower()
    if "dinero" in text or "vender" in text or "negocio" in text:
        return "ceo"
    return "personal"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        mode = detect_mode(text)

        response_text = f"OpenClaw recibió: {text}"

        # 📩 RESPUESTA TELEGRAM
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": response_text
            }
        )

        # 💾 GUARDAR EN SUPABASE (ESTO TE FALTABA)
        save_message(chat_id, text, response_text, mode)

    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
