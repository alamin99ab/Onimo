from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
from dotenv import load_dotenv
import os
from utils import register_routes

load_dotenv()
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app, default_limits=["10 per minute"])

register_routes(app)

@app.route("/health")
def health():
    return "Onimo AI (Upgraded) ✅ Flask + Limiter + Logging + .env Ready"

if __name__ == "__main__":
    app.run(debug=True)
