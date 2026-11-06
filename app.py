"""
app.py
Main Flask application — config, extensions, and blueprint registration.
All actual routes live in routes/auth.py, routes/student.py,
routes/club_head.py, and routes/admin.py.
"""

from flask import Flask
from flask_mail import Mail
import os
import cloudinary
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

import cloudinary.uploader

# ──────────────────────────────────────────────
# Cloudinary config
# ──────────────────────────────────────────────
cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key    = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET"),
)

# ──────────────────────────────────────────────
# Flask app + config
# ──────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-in-production")

app.config["MAIL_SERVER"]   = os.getenv("MAIL_SERVER",   "smtp.gmail.com")
app.config["MAIL_PORT"]     = int(os.getenv("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"]  = True
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = ("CampusPlus", os.getenv("MAIL_USERNAME"))

mail = Mail(app)
app.extensions["mail"] = mail   # so blueprints can access via current_app.extensions["mail"]

# ──────────────────────────────────────────────
# Register blueprints
# ──────────────────────────────────────────────
from routes.auth import auth_bp
from routes.student import student_bp
from routes.club_head import club_head_bp
from routes.admin import admin_bp
from routes.academics import academics_bp

app.register_blueprint(auth_bp)
app.register_blueprint(student_bp)
app.register_blueprint(club_head_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(academics_bp)


if __name__ == "__main__":
    app.run(debug=True)
