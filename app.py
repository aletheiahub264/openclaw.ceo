import logging
import os
from collections import deque
from flask import Flask, request
import requests
from supabase import create_client, Client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

app = Flask(__name__)

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

_seen_ids: set = set()
_seen_queue: deque = deque(maxlen=500)


def is_duplicate(update_id: int) -> bool:
    if update_id in _seen_ids:
        return True
    if len(_seen_queue) == 500:
        _seen_ids.discard(_seen_queue[0])
    _seen_queue.append(update_id)
    _seen_ids.add(update_id)
    return False


def detect_mode(text: str) -> str:
    keywords = {"vender", "dinero", "negocio", "cliente", "venta"}
    if any(w in text.lower() for w in keywords):
        return "ceo"
    return "personal"


def send_message(chat_id: int, text: str) -> None:
    try:
        r = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10
        )
        r.raise_for_status()
        log.info(f"Mensaje enviado a {chat_id}")
    except Exception as e:
        log.error(f"Error enviando a Telegram: {e}")


def save_interaction(chat_id: int, message: str, response: str, mode: str) -> None:
    payload = {
        "telegram_id": str(chat_id),
        "message": message,
        "response": response,
        "mode": mode
    }
    log.info(f"Intentando guardar en Supabase: {payload}")
    try:
        result = (
            supabase
            .table("interactions")
            .insert(payload)
            .execute()
        )
        if result.data:
            log.info(f"Guardado en Supabase: {result.data}")
        else:
            log.warning("Insert vacio en Supabase, revisa RLS o permisos")
    except Exception as e:
        log.error(f"Excepcion en Supabase insert: {e}")


@app.route("/")
def home():
    return "OpenClaw activo"


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)
    if not data:
        log.warning("Webhook recibio payload vacio o no-JSON")
        return "ok", 200

    if "message" not in data:
        return "ok", 200

    update_id = data.get("update_id")
    if update_id and is_duplicate(update_id):
        log.info(f"Update duplicado ignorado: {update_id}")
        return "ok", 200

    msg = data["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip()

    if not text:
        log.info("Mensaje sin texto ignorado")
        return "ok", 200

    log.info(f"Mensaje de {chat_id}: {text!r}")

    mode = detect_mode(text)
    response_text = f"[{mode.upper()}] OpenClaw recibio: {text}"

    send_message(chat_id, response_text)
    save_interaction(chat_id, text, response_text, mode)

    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
