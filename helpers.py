"""
helpers.py
Shared utility functions used across all route blueprints
(auth, student, club_head, admin).
"""

import os
import random
import string
import hashlib
import json
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
from flask import request, redirect, url_for, session
from functools import wraps
from flask_mail import Message

import cloudinary
import cloudinary.uploader


# ──────────────────────────────────────────────
# DB connection
# ──────────────────────────────────────────────
def get_db():
    return psycopg2.connect(
        host     = os.getenv("DB_HOST",     "localhost"),
        dbname   = os.getenv("DB_NAME",     "campusplus"),
        user     = os.getenv("DB_USER",     "postgres"),
        password = os.getenv("DB_PASSWORD", ""),
        port     = os.getenv("DB_PORT",     "5432"),
    )


# ──────────────────────────────────────────────
# Auth helpers
# ──────────────────────────────────────────────
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


# ──────────────────────────────────────────────
# Email helper (needs `mail` object passed in from app.py)
# ──────────────────────────────────────────────
def send_otp_email(mail, to_email: str, otp: str):
    msg = Message(
        subject="CampusPlus – Your Verification Code",
        recipients=[to_email],
    )
    msg.html = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;padding:32px;
                border:1px solid #e0e0e0;border-radius:12px;">
        <h2 style="color:#4f46e5;margin-bottom:4px;">CampusPlus</h2>
        <p style="color:#555;margin-top:0;">MIT-WPU Campus Network</p>
        <hr style="border:none;border-top:1px solid #eee;margin:20px 0;">
        <p style="font-size:15px;color:#333;">
            Use the code below to verify your account.
            It expires in <strong>10 minutes</strong>.
        </p>
        <div style="text-align:center;margin:28px 0;">
            <span style="font-size:36px;font-weight:700;letter-spacing:10px;
                         color:#4f46e5;background:#f0f0ff;padding:12px 24px;
                         border-radius:8px;">{otp}</span>
        </div>
        <p style="font-size:13px;color:#888;">
            If you did not request this, you can safely ignore this email.
        </p>

        
    </div>
    """
    mail.send(msg)


# ──────────────────────────────────────────────
# Cloudinary upload helper
# ──────────────────────────────────────────────
def upload_file_to_cloudinary(file, folder="campusplus"):
    """
    Accepts a Flask file object, uploads to Cloudinary.
    Returns the secure URL string.
    """
    filename = file.filename.lower()
    if filename.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
        resource_type = "image"
    else:
        resource_type = "raw"   # PDFs, PPTs, DOCX, etc.

    result = cloudinary.uploader.upload(
        file,
        folder          = folder,
        resource_type   = resource_type,
        use_filename    = True,
        unique_filename = True,
    )
    return result["secure_url"]


# ──────────────────────────────────────────────
# Admin action logger — used by admin.py and club_head.py
# ──────────────────────────────────────────────
def log_admin_action(admin_id, action, target_type, target_id, details=None, status="success"):
    """
    Writes an entry to admin_logs.
    admin_id can be None (e.g. failed login attempt with unknown user).
    details should be a dict — gets JSON-encoded automatically.
    """
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO admin_logs (admin_id, action, target_type, target_id, details, status, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            admin_id, action, target_type, target_id,
            json.dumps(details) if details else None,
            status,
            request.remote_addr if request else None
        ))
        conn.commit()
    except Exception as e:
        print(f"LOG ERROR: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_id = session.get("user_id") or session.get("admin_id")
            if not user_id:
                return redirect(url_for("auth.index"))

            if "admin" in allowed_roles and session.get("is_admin"):
                return f(*args, **kwargs)

            user_roles = session.get("roles")
            if user_roles is None:
                conn = get_db()
                cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                try:
                    cur.execute(
                        "SELECT role FROM user_roles WHERE user_id = %s AND revoked_at IS NULL",
                        (user_id,)
                    )
                    user_roles = [row["role"] for row in cur.fetchall()]
                    session["roles"] = user_roles
                finally:
                    cur.close()
                    conn.close()

            if not any(role in user_roles for role in allowed_roles):
                return redirect(url_for("auth.index"))

            return f(*args, **kwargs)

        return wrapper
    return decorator
