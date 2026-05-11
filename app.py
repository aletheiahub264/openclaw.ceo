import logging
import os
from collections import deque

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

from flask import Flask, request

app = Flask(__name__)

log.info("Flask iniciado correctamente")

# ─── CONFIG ─────────────────────────────────────────────────
TOKEN        = os.environ.get("TELEGRAM_TOKEN", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

# ─── SUPABASE OPCIONAL ──────────────────────────────────────
supabase = None
try:
    if SUPABASE_URL and SUPABASE_KEY:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        log.info("Supabase conectado")
    else:
        log.warning("Supabase no configurado, continuando sin el")
except Exception as e:
    log.error(f"Supabase fallo al iniciar: {e}")

# ─── REQUESTS OPCIONAL ──────────────────────────────────────
try:
    import requests as http
    log.info("requests cargado")
except Exception as e:
    http = None
    log.error(f"requests no disponible: {e}")

# ─── ANTI-DUPLICADOS ────────────────────────────────────────
_seen_ids   = set()
_seen_queue = deque(maxlen=500)

def is_duplicate(update_id):
    if update_id in _seen_ids:
        return True
    if len(_seen_queue) == 500:
        _seen_ids.discard(_seen_queue[0])
    _seen_queue.append(update_id)
    _seen_ids.add(update_id)
    return False

# ─── HELPERS ────────────────────────────────────────────────
def detect_mode(text):
    keywords = {"vender", "dinero", "negocio", "cliente", "venta"}
    return "ceo" if any(w in text.lower() for w in keywords) else "personal"

def send_message(chat_id, text):
    if http is None:
        log.error("requests no disponible, no se puede enviar mensaje")
        return
    try:
        r = http.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10
        )
        r.raise_for_status()
        log.info(f"Mensaje enviado a {chat_id}")
    except Exception as e:
        log.error(f"Error enviando a Telegram: {e}")

def save_interaction(chat_id, message, response, mode):
    if supabase is None:
        log.warning("Supabase no disponible, mensaje no guardado")
        return
    try:
        result = supabase.table("interactions").insert({
            "telegram_id": str(chat_id),
            "message":     message,
            "response":    response,
            "mode":        mode
        }).execute()
        if result.data:
            log.info(f"Guardado en Supabase: {result.data}")
        else:
            log.warning("Supabase no guardo datos, revisa RLS")
    except Exception as e:
        log.error(f"Error en Supabase: {e}")

# ─── ROUTES ─────────────────────────────────────────────────
@app.route("/")
def home():
    return "SERVER OK", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    log.info("Webhook recibido")
    try:
        data = request.get_json(silent=True)
        if not data or "message" not in data:
            return "ok", 200

        update_id = data.get("update_id")
        if update_id and is_duplicate(update_id):
            log.info(f"Duplicado ignorado: {update_id}")
            return "ok", 200

        msg     = data["message"]
        chat_id = msg["chat"]["id"]
        text    = msg.get("text", "").strip()

        if not text:
            return "ok", 200

        log.info(f"Mensaje de {chat_id}: {text!r}")

        mode          = detect_mode(text)
        response_text = f"[{mode.upper()}] OpenClaw recibio: {text}"

        send_message(chat_id, response_text)
        save_interaction(chat_id, text, response_text, mode)

    except Exception as e:
        log.error(f"Error en webhook: {e}")

    return "ok", 200
