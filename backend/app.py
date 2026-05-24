import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/config", methods=["GET"])
def config():
    return jsonify({
        "database_url": os.getenv("DATABASE_URL", "")
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
