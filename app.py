from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "OpenClaw activo"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    message = data.get("message", "")

    response = {
        "reply": f"OpenClaw recibió: {message}"
    }

    return jsonify(response), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
