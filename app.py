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

PINTEREST_ACCESS_TOKEN = os.environ.get("PINTEREST_ACCESS_TOKEN", "")
PINTEREST_BOARD_ID     = os.environ.get("PINTEREST_BOARD_ID", "")
PINTEREST_API          = "https://api.pinterest.com/v5"

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
        log.error("requests no disponible")
        return

    try:
        r = http.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text
            },
            timeout=10
        )

        r.raise_for_status()

        log.info(f"Mensaje enviado a {chat_id}")

    except Exception as e:
        log.error(f"Telegram error: {e}")

def save_interaction(chat_id, message, response, mode):
    if supabase is None:
        log.warning("Supabase no disponible")
        return

    try:
        result = supabase.table("interactions").insert({
            "telegram_id": str(chat_id),
            "message": message,
            "response": response,
            "mode": mode
        }).execute()

        if result.data:
            log.info("Interaccion guardada")

    except Exception as e:
        log.error(f"Supabase error: {e}")

# ─── PINTEREST ──────────────────────────────────────────────
def publish_to_pinterest(title, description, image_url):
    if http is None:
        log.error("requests no disponible")
        return

    if not PINTEREST_ACCESS_TOKEN:
        log.warning("Pinterest token no configurado")
        return

    if not PINTEREST_BOARD_ID:
        log.warning("Pinterest board id no configurado")
        return

    headers = {
        "Authorization": f"Bearer {PINTEREST_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "board_id": PINTEREST_BOARD_ID,
        "title": title,
        "description": description,
        "media_source": {
            "source_type": "image_url",
            "url": image_url
        }
    }

    try:
        r = http.post(
            f"{PINTEREST_API}/pins",
            headers=headers,
            json=payload,
            timeout=20
        )

        log.info(f"Pinterest response: {r.text}")

        if r.status_code in [200, 201]:
            log.info("Pin publicado correctamente")
        else:
            log.error(f"Pinterest error {r.status_code}")

    except Exception as e:
        log.error(f"Pinterest fallo: {e}")

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

        msg = data["message"]

        chat_id = msg["chat"]["id"]
        text = msg.get("text", "").strip()

        if not text:
            return "ok", 200

        log.info(f"Mensaje de {chat_id}: {text}")

        mode = detect_mode(text)

        response_text = f"[{mode.upper()}] OpenClaw recibio: {text}"

        send_message(chat_id, response_text)

        save_interaction(
            chat_id,
            text,
            response_text,
            mode
        )

        # ─── AUTO PUBLICACION PINTEREST ───
        if mode == "ceo":

            pinterest_title = f"OpenClaw AI | {text[:60]}"

            pinterest_description = (
                f"{text}\n\n"
                f"Automatizado con OpenClaw AI"
            )

            sample_image = (
                "https://images.unsplash.com/photo-1522202176988-66273c2fd55f"
            )

            publish_to_pinterest(
                pinterest_title,
                pinterest_description,
                sample_image
            )

    except Exception as e:
        log.error(f"Webhook error: {e}")

    return "ok", 200

# ─── START ──────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
