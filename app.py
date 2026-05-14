import logging
import os
import random
from collections import deque

from flask import Flask, request

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ─── CONFIG ─────────────────────────────────────────────
TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

PINTEREST_ACCESS_TOKEN = os.environ.get("PINTEREST_ACCESS_TOKEN", "")
PINTEREST_BOARD_ID = os.environ.get("PINTEREST_BOARD_ID", "")
PINTEREST_API = "https://api.pinterest.com/v5"

TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

# ─── DEPENDENCIAS ──────────────────────────────────────
try:
    import requests as http
except:
    http = None

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    from supabase import create_client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── ANTI DUPLICADOS ───────────────────────────────────
_seen = set()
_queue = deque(maxlen=500)

def is_duplicate(uid):
    if uid in _seen:
        return True
    if len(_queue) == 500:
        _seen.discard(_queue[0])
    _queue.append(uid)
    _seen.add(uid)
    return False

# ─── DETECCIÓN ─────────────────────────────────────────
def detect_mode(text):
    text = text.lower()
    keywords = ["vender", "negocio", "dinero", "venta", "cliente", "ingresos"]
    return "ceo" if any(k in text for k in keywords) else "personal"

# ─── MOTOR DE CONTENIDO PRO ────────────────────────────
HOOKS = [
    "¿Quieres automatizar tu negocio con IA y atraer clientes?",
    "Los negocios que usan IA están creciendo más rápido",
    "Esto está cambiando la forma de vender online",
    "La automatización ya no es opcional en 2026"
]

PROBLEMS = [
    "La mayoría de negocios pierde tiempo creando contenido manual.",
    "Gestionar clientes manualmente limita el crecimiento.",
    "Publicar contenido uno a uno ya no escala."
]

SOLUTIONS = [
    "OpenClaw automatiza contenido y captación de clientes.",
    "Sistema de IA que genera y publica contenido automáticamente.",
    "Automatización completa de marketing con inteligencia artificial."
]

def generate_post():
    return (
        "Automatiza tu negocio con IA",
        f"{random.choice(HOOKS)}\n\n"
        f"{random.choice(PROBLEMS)}\n\n"
        f"{random.choice(SOLUTIONS)}\n\n"
        "Empieza aquí 👉 https://beacons.ai/aletheiahub.ai"
    )

# ─── TELEGRAM ──────────────────────────────────────────
def send_message(chat_id, text):
    if http is None:
        return
    try:
        http.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10
        )
    except Exception as e:
        log.error(e)

# ─── SUPABASE TRACKING ────────────────────────────────
def track_post(title, description, mode):
    if supabase is None:
        return
    supabase.table("pinterest_experiments").insert({
        "title": title,
        "description": description,
        "mode": mode,
        "status": "sent"
    }).execute()

# ─── PINTEREST (FUNNEL PRO) ───────────────────────────
def publish_to_pinterest(title, description, image_url):
    if http is None:
        return False

    if not PINTEREST_ACCESS_TOKEN or not PINTEREST_BOARD_ID:
        return False

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

    r = http.post(
        f"{PINTEREST_API}/pins",
        headers=headers,
        json=payload,
        timeout=20
    )

    return r.status_code in [200, 201]

# ─── WEBHOOK ──────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)

    if not data or "message" not in data:
        return "ok"

    uid = data.get("update_id")
    if uid and is_duplicate(uid):
        return "ok"

    msg = data["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip()

    if not text:
        return "ok"

    mode = detect_mode(text)

    response = f"[{mode.upper()}] OpenClaw activo: {text}"
    send_message(chat_id, response)

    # ─── FUNNEL AUTOMÁTICO ───
    if mode == "ceo":

        title, description = generate_post()

        ok = publish_to_pinterest(
            title,
            description,
            "https://images.unsplash.com/photo-1522202176988-66273c2fd55f"
        )

        if ok:
            track_post(title, description, mode)

    return "ok"

# ─── START ─────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
