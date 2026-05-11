from flask import Flask, request
import requests
from supabase import create_client
from collections import deque
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 🔵 TELEGRAM
TOKEN = "8748023432:AAHNN7yNo2jmAO4ddRIrAEG4lwaLstuYUoA"
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

# 🟢 SUPABASE
SUPABASE_URL = "https://mcjfaqtrygprcbjkhect.supabase.co"
SUPABASE_KEY = "sb_publishable_0Nqd3lazIAnzIEa1nb6Dxw_SDTT7uR"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🔥 ANTI DUPLICADOS — deque con límite para evitar memory leak
MAX_PROCESSED = 1000
processed_ids = deque(maxlen=MAX_PROCESSED)
processed_ids_set = set()

def is_duplicate(update_id):
    if update_id in processed_ids_set:
        return True
    # Si el deque está lleno, eliminar el más antiguo del set también
    if len(processed_ids) == MAX_PROCESSED:
        oldest = processed_ids[0]
        processed_ids_set.discard(oldest)
    processed_ids.append(update_id)
    processed_ids_set.add(update_id)
    return False

@app.route("/")
def home():
    return "OpenClaw activo"

# 💾 GUARDAR EN SUPABASE
def save_message(chat_id, message, response, mode):
    try:
        supabase.table("interactions").insert({
            "telegram_id": str(chat_id),
            "message": message,
            "response": response,
            "mode": mode
        }).execute()
    except Exception as e:
        logger.error(f"Error Supabase: {e}")

# 📩 ENVIAR A TELEGRAM — con timeout
def send_telegram_message(chat_id, text):
    try:
        resp = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10  # ✅ Evita que el webhook se cuelgue
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error enviando a Telegram: {e}")

# 🧠 DETECTOR DE MODO
def detect_mode(text):
    text_lower = text.lower()
    if any(word in text_lower for word in ["vender", "dinero", "negocio"]):
        return "ceo"
    return "personal"

# 🤖 GENERAR RESPUESTA SEGÚN MODO
def generate_response(text, mode):
    if not text:
        return None  # ✅ No responder a mensajes sin texto
    if mode == "ceo":
        return f"[Modo CEO] Analizando tu consulta de negocio: {text}"
    return f"OpenClaw recibió: {text}"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)  # ✅ silent=True evita error 400 si el body no es JSON

    if not data or "message" not in data:
        return "ok"

    # 🔥 ANTI DUPLICADOS
    update_id = data.get("update_id")
    if update_id and is_duplicate(update_id):
        return "ok"

    message = data["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    # ✅ Ignorar mensajes sin texto (fotos, stickers, etc.)
    if not text:
        return "ok"

    mode = detect_mode(text)
    response_text = generate_response(text, mode)

    if response_text:
        send_telegram_message(chat_id, response_text)
        save_message(chat_id, text, response_text, mode)

    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
