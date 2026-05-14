import os
import time
import uuid
import random
import logging
from flask import Flask, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("OpenClawV4")

# ─────────────────────────────
# CONFIG
# ─────────────────────────────
TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

PINTEREST_TOKEN = os.environ.get("PINTEREST_ACCESS_TOKEN", "")
PINTEREST_BOARD = os.environ.get("PINTEREST_BOARD_ID", "")
PINTEREST_API = "https://api.pinterest.com/v5"

TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

try:
    import requests as http
except:
    http = None

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        log.error(e)

# ─────────────────────────────
# MEMORIA LOCAL (fallback)
# ─────────────────────────────
LEADS = {}
CONVERSIONS = {}
CLICKS = {}
_seen = set()

# ─────────────────────────────
# UTIL
# ─────────────────────────────
def gen_id():
    return str(uuid.uuid4())

def safe_post(url, **kwargs):
    if http is None:
        return None
    try:
        return http.post(url, timeout=10, **kwargs)
    except:
        return None

# ─────────────────────────────
# TRACKING CORE (CLICKS + CONVERSIONS)
# ─────────────────────────────
def track_click(lead_id):
    CLICKS[lead_id] = CLICKS.get(lead_id, 0) + 1

def track_conversion(lead_id, value=1.0):
    CONVERSIONS[lead_id] = CONVERSIONS.get(lead_id, 0) + value

# ─────────────────────────────
# SCORING REAL (DINERO > INTERÉS)
# ─────────────────────────────
def lead_score(lead_id):
    clicks = CLICKS.get(lead_id, 0)
    conv = CONVERSIONS.get(lead_id, 0)

    return (conv * 10) + clicks

def best_leads():
    return sorted(LEADS.items(), key=lambda x: lead_score(x[0]), reverse=True)

# ─────────────────────────────
# CLASIFICACIÓN
# ─────────────────────────────
def classify(text):
    t = text.lower()
    hot = ["comprar", "precio", "servicio", "automatizar", "negocio", "dinero"]
    warm = ["info", "quiero", "cómo", "interesado"]

    if any(w in t for w in hot):
        return "hot"
    if any(w in t for w in warm):
        return "warm"
    return "cold"

# ─────────────────────────────
# FUNNEL DINÁMICO
# ─────────────────────────────
def funnel(mode, lead_id):
    base_url = "https://beacons.ai/aletheiahub.ai?lead=" + lead_id

    if mode == "hot":
        return f"🔥 Listo para automatizar tu negocio.\n👉 {base_url}"

    if mode == "warm":
        return f"💡 Te muestro cómo conseguir clientes automáticamente.\n👉 {base_url}"

    return f"🚀 Descubre cómo la IA puede ayudarte.\n👉 {base_url}"

# ─────────────────────────────
# CONTENIDO OPTIMIZADO POR DINERO
# ─────────────────────────────
HOOKS = [
    "Negocios están perdiendo clientes por no automatizar",
    "La IA está reemplazando procesos de ventas",
    "Automatizar marketing ya es obligatorio"
]

SOLUTIONS = [
    "Sistema que genera clientes automáticamente",
    "IA que convierte mensajes en ventas",
    "Embudo automático sin intervención humana"
]

def generate_content():
    return (
        "🔥 Automatiza tu negocio con IA\n\n"
        f"{random.choice(HOOKS)}\n\n"
        f"{random.choice(SOLUTIONS)}\n\n"
        "👉 https://beacons.ai/aletheiahub.ai"
    )

# ─────────────────────────────
# TELEGRAM
# ─────────────────────────────
def send(chat_id, text):
    safe_post(
        f"{TELEGRAM_API}/sendMessage",
        json={"chat_id": chat_id, "text": text}
    )

# ─────────────────────────────
# PINTEREST TRAFFIC ENGINE
# ─────────────────────────────
def publish(content):
    if not PINTEREST_TOKEN or not PINTEREST_BOARD:
        return False

    r = safe_post(
        f"{PINTEREST_API}/pins",
        headers={
            "Authorization": f"Bearer {PINTEREST_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "board_id": PINTEREST_BOARD,
            "title": "Automatiza tu negocio con IA",
            "description": content,
            "media_source": {
                "source_type": "image_url",
                "url": "https://images.unsplash.com/photo-1522202176988-66273c2fd55f"
            }
        }
    )

    return r is not None and r.status_code in [200, 201]

# ─────────────────────────────
# DATABASE (SUPABASE OPTIONAL)
# ─────────────────────────────
def save_lead(lead_id, text, mode):
    if supabase:
        try:
            supabase.table("leads").insert({
                "lead_id": lead_id,
                "message": text,
                "mode": mode
            }).execute()
        except:
            pass

def save_metrics():
    if supabase:
        try:
            supabase.table("metrics").insert({
                "clicks": CLICKS,
                "conversions": CONVERSIONS
            }).execute()
        except:
            pass

# ─────────────────────────────
# LEARNING ENGINE (REAL OPTIMIZATION)
# ─────────────────────────────
def best_strategy():
    if not CONVERSIONS:
        return "hot"
    return max(CONVERSIONS, key=CONVERSIONS.get)

# ─────────────────────────────
# WEBHOOK
# ─────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)

    if not data or "message" not in data:
        return "ok"

    msg = data["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip()

    if not text:
        return "ok"

    # ───────────────
    # LEAD ID
    # ───────────────
    lead_id = str(chat_id)

    # ───────────────
    # CLASSIFY
    # ───────────────
    mode = classify(text)

    # ───────────────
    # TRACK LEAD
    # ───────────────
    LEADS[lead_id] = mode
    save_lead(lead_id, text, mode)

    # ───────────────
    # CLICK SIMULATION (REAL WORLD TRACKING REQUIRIRÍA PIXEL)
    # ───────────────
    track_click(lead_id)

    # ───────────────
    # RESPONSE FUNNEL
    # ───────────────
    send(chat_id, funnel(mode, lead_id))

    # ───────────────
    # CONTENT ENGINE
    # ───────────────
    content = generate_content()

    # ───────────────
    # TRAFFIC ENGINE
    # ───────────────
    if mode in ["cold", "warm"]:
        publish(content)

    # ───────────────
    # OPTIMIZATION STEP
    # ───────────────
    save_metrics()

    return "ok"


# ─────────────────────────────
# START
# ─────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
