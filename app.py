from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "OpenClaw activo"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    message = data.get("message", "")

    return jsonify({
        "reply": f"OpenClaw recibió: {message}"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
