import os
import time
import random
import logging
import requests
from flask import Flask, request

# ─────────────────────────────
# APP
# ─────────────────────────────
app = Flask(__name__, template_folder="templates")
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("OpenClawV6")

# ─────────────────────────────
# LANDING
# ─────────────────────────────
@app.route("/")
def home():
    try:
        from flask import render_template
        return render_template("index.html")
    except:
        return "OpenClaw activo"

# ─────────────────────────────
# CONFIG
# ─────────────────────────────
TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

# ─────────────────────────────
# MEMORIA
# ─────────────────────────────
LEADS = {}
LEAD_HISTORY = {}
LEAD_SCORE = {}

# ─────────────────────────────
# TELEGRAM
# ─────────────────────────────
def send(chat_id, text):
    try:
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text
            },
            timeout=10
        )
    except Exception as e:
        log.error(e)

# ─────────────────────────────
# CLASIFICACIÓN
# ─────────────────────────────
def classify(text):

    t = text.lower()

    buyer = [
        "comprar",
        "precio",
        "contratar",
        "cuánto cuesta",
        "quiero automatizar"
    ]

    hot = [
        "negocio",
        "clientes",
        "ventas",
        "dinero",
        "automatizar"
    ]

    warm = [
        "cómo",
        "info",
        "explica",
        "interesado"
    ]

    if any(x in t for x in buyer):
        return "buyer"

    if any(x in t for x in hot):
        return "hot"

    if any(x in t for x in warm):
        return "warm"

    return "cold"

# ─────────────────────────────
# SCORE
# ─────────────────────────────
def update_score(lead_id, mode):

    score = LEAD_SCORE.get(lead_id, 0)

    if mode == "buyer":
        score += 40

    elif mode == "hot":
        score += 25

    elif mode == "warm":
        score += 10

    else:
        score += 3

    LEAD_SCORE[lead_id] = min(score, 100)

    return LEAD_SCORE[lead_id]

def is_ready(lead_id):
    return LEAD_SCORE.get(lead_id, 0) >= 70

# ─────────────────────────────
# IA GROQ
# ─────────────────────────────
def ai_response(text, mode):

    # fallback si no hay API
    if not GROQ_API_KEY:

        if mode == "buyer":
            return (
                "🔥 Te puedo instalar un sistema automático "
                "para conseguir clientes."
            )

        if mode == "hot":
            return (
                "⚡ Este sistema puede automatizar "
                "ventas y captación."
            )

        if mode == "warm":
            return (
                "💡 La automatización puede ayudarte "
                "a escalar tu negocio."
            )

        return "🚀 Descubre automatización con IA."

    try:

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Eres un experto en automatización "
                        "de negocios con inteligencia artificial. "
                        "Tu objetivo es convertir leads en clientes. "
                        "Responde breve, natural, profesional y persuasivo."
                    )
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            "temperature": 0.8,
            "max_tokens": 200
        }

        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=20
        )

        if r.status_code == 200:

            data = r.json()

            return data["choices"][0]["message"]["content"]

        log.error(f"GROQ STATUS: {r.status_code}")
        log.error(r.text)

        return "⚠️ IA temporalmente ocupada."

    except Exception as e:

        log.error(e)

        return "⚠️ Error temporal en IA."

# ─────────────────────────────
# FUNNEL
# ─────────────────────────────
def funnel(lead_id):

    return (
        "👉 https://beacons.ai/aletheiahub.ai?lead="
        + lead_id
    )

# ─────────────────────────────
# CRM
# ─────────────────────────────
def save_lead(lead_id, text, mode):

    LEAD_HISTORY.setdefault(lead_id, []).append({
        "text": text,
        "mode": mode,
        "time": time.time()
    })

    LEAD_HISTORY[lead_id] = LEAD_HISTORY[lead_id][-15:]

# ─────────────────────────────
# WEBHOOK
# ─────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():

    data = request.get_json(silent=True)

    if not data:
        return "ok"

    if "message" not in data:
        return "ok"

    msg = data["message"]

    chat_id = msg["chat"]["id"]

    text = msg.get("text", "").strip()

    if not text:
        return "ok"

    lead_id = str(chat_id)

    # clasificación
    mode = classify(text)

    # score
    score = update_score(lead_id, mode)

    # crm
    save_lead(lead_id, text, mode)

    # respuesta IA
    reply = ai_response(text, mode)

    # cierre inteligente
    if is_ready(lead_id):

        send(
            chat_id,
            (
                "🔥 ESTÁS LISTO PARA AUTOMATIZAR "
                "TU NEGOCIO\n\n"
                "👉 Instalación disponible ahora mismo."
            )
        )

    else:

        send(
            chat_id,
            reply + "\n\n" + funnel(lead_id)
        )

    return "ok"

# ─────────────────────────────
# START
# ─────────────────────────────
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 8080))

    app.run(
        host="0.0.0.0",
        port=port
)
