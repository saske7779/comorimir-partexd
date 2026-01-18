from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/")
def home():
    return "Sasuke FileBot Web is running 😈"


@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.get("/ping")
def ping():
    # Useful for cron/uptime pings
    return jsonify({"pong": True})
