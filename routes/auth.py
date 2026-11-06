"""
routes/auth.py
Authentication routes: login, signup, OTP verification, logout.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
import psycopg2.extras
from datetime import datetime, timedelta
import traceback

from helpers import get_db, hash_password, generate_otp, send_otp_email, log_admin_action

auth_bp = Blueprint("auth", __name__)

ALLOWED_DOMAIN = "mitwpu.edu.in"


@auth_bp.route("/")
def index():
    return render_template("login.html")


# ── 1. Show signup form ────────────────────────
@auth_bp.route("/signup")
def signup():
    return render_template("signup.html")


# ── 2. Process signup: validate email, send OTP ─
@auth_bp.route("/signup-process", methods=["POST"])
def signup_process():
    full_name = request.form.get("full_name", "").strip()
    email     = request.form.get("u_email", "").strip().lower()
    password  = request.form.get("u_pass",  "").strip()

    if not full_name:
        flash("Full name is required.", "danger")
        return redirect(url_for("auth.signup"))

    if not email.endswith(f"@{ALLOWED_DOMAIN}"):
        flash(f"Only @{ALLOWED_DOMAIN} email addresses are allowed.", "danger")
        return redirect(url_for("auth.signup"))

    if len(password) < 8:
        flash("Password must be at least 8 characters.", "danger")
        return redirect(url_for("auth.signup"))

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT id FROM users WHERE email = %s AND is_verified = TRUE", (email,))
        if cur.fetchone():
            flash("An account with this email already exists. Please log in.", "danger")
            return redirect(url_for("auth.index"))

        otp         = generate_otp()
        otp_expires = datetime.utcnow() + timedelta(minutes=10)
        hashed_pass = hash_password(password)

        cur.execute("""
            INSERT INTO pending_users (email, full_name, password_hash, otp, otp_expires_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (email)
            DO UPDATE SET
                full_name      = EXCLUDED.full_name,
                password_hash  = EXCLUDED.password_hash,
                otp            = EXCLUDED.otp,
                otp_expires_at = EXCLUDED.otp_expires_at,
                attempts       = 0,
                created_at     = NOW()
        """, (email, full_name, hashed_pass, otp, otp_expires))
        conn.commit()

        try:
            send_otp_email(current_app.extensions["mail"], email, otp)
        except Exception as mail_err:
            print(f"MAIL ERROR: {mail_err}")
            flash("Account created but email failed. Check mail config.", "danger")
            return redirect(url_for("auth.signup"))

        session["pending_email"] = email
        flash("OTP sent! Check your inbox.", "success")
        return redirect(url_for("auth.verify_otp"))

    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        print(f"SIGNUP ERROR: {e}")
        flash(f"Signup error: {e}", "danger")
        return redirect(url_for("auth.signup"))
    finally:
        cur.close()
        conn.close()


# ── 3. OTP verification page ───────────────────
@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    email = session.get("pending_email")
    if not email:
        flash("Session expired. Please sign up again.", "danger")
        return redirect(url_for("auth.signup"))

    if request.method == "GET":
        return render_template("verify_otp.html", email=email)

    entered_otp = request.form.get("otp", "").strip()

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("""
            SELECT otp, otp_expires_at, attempts, password_hash, full_name
            FROM pending_users
            WHERE email = %s
        """, (email,))
        row = cur.fetchone()

        if not row:
            flash("No pending registration found. Please sign up again.", "danger")
            return redirect(url_for("auth.signup"))

        if row["attempts"] >= 5:
            flash("Too many incorrect attempts. Please sign up again.", "danger")
            cur.execute("DELETE FROM pending_users WHERE email = %s", (email,))
            conn.commit()
            session.pop("pending_email", None)
            return redirect(url_for("auth.signup"))

        if datetime.utcnow() > row["otp_expires_at"].replace(tzinfo=None):
            flash("OTP has expired. Please sign up again to get a new one.", "danger")
            cur.execute("DELETE FROM pending_users WHERE email = %s", (email,))
            conn.commit()
            session.pop("pending_email", None)
            return redirect(url_for("auth.signup"))

        if entered_otp != row["otp"]:
            cur.execute("UPDATE pending_users SET attempts = attempts + 1 WHERE email = %s", (email,))
            conn.commit()
            remaining = 5 - (row["attempts"] + 1)
            flash(f"Incorrect OTP. {remaining} attempt(s) remaining.", "danger")
            return render_template("verify_otp.html", email=email)

        # ✅ OTP correct – create real user account
        cur.execute("""
            INSERT INTO users (email, full_name, password_hash, is_verified, created_at)
            VALUES (%s, %s, %s, TRUE, NOW())
            ON CONFLICT (email) DO UPDATE
                SET full_name     = EXCLUDED.full_name,
                    password_hash = EXCLUDED.password_hash,
                    is_verified   = TRUE
        """, (email, row["full_name"], row["password_hash"]))

        cur.execute("DELETE FROM pending_users WHERE email = %s", (email,))
        conn.commit()

        session.pop("pending_email", None)
        flash("Account verified successfully! You can now log in.", "success")
        return redirect(url_for("auth.index"))

    except Exception as e:
        conn.rollback()
        print(f"VERIFY OTP ERROR: {e}")
        flash("Something went wrong. Please try again.", "danger")
        return render_template("verify_otp.html", email=email)
    finally:
        cur.close()
        conn.close()


# ── 4. Resend OTP ──────────────────────────────
@auth_bp.route("/resend-otp", methods=["POST"])
def resend_otp():
    email = session.get("pending_email")
    if not email:
        flash("Session expired. Please sign up again.", "danger")
        return redirect(url_for("auth.signup"))

    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("SELECT created_at FROM pending_users WHERE email = %s", (email,))
        row = cur.fetchone()
        if row:
            last_sent = row[0].replace(tzinfo=None)
            elapsed = (datetime.utcnow() - last_sent).total_seconds()
            if elapsed < 60:
                wait = int(60 - elapsed)
                flash(f"Please wait {wait}s before requesting a new OTP.", "danger")
                return redirect(url_for("auth.verify_otp"))

        otp         = generate_otp()
        otp_expires = datetime.utcnow() + timedelta(minutes=10)

        cur.execute("""
            UPDATE pending_users
            SET otp = %s, otp_expires_at = %s, attempts = 0, created_at = NOW()
            WHERE email = %s
        """, (otp, otp_expires, email))
        conn.commit()

        send_otp_email(current_app.extensions["mail"], email, otp)
        flash("A new OTP has been sent to your email.", "success")

    except Exception as e:
        conn.rollback()
        print(f"RESEND OTP ERROR: {e}")
        flash("Could not resend OTP. Please try again.", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("auth.verify_otp"))


# ── 5. Login (handles both student and admin) ──
@auth_bp.route("/login", methods=["POST"])
def login():
    email    = request.form.get("u_email", "").strip().lower()
    password = request.form.get("u_pass",  "").strip()

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("""
            SELECT id, email FROM users
            WHERE email = %s AND password_hash = %s AND is_verified = TRUE
        """, (email, hash_password(password)))
        user = cur.fetchone()

        if not user:
            flash("Invalid credentials or unverified account.", "danger")
            return redirect(url_for("auth.index"))

        # Check for active admin role
        cur.execute("""
            SELECT id FROM user_roles
            WHERE user_id = %s AND role = 'admin' AND revoked_at IS NULL
        """, (user["id"],))
        is_admin = cur.fetchone() is not None

        cur.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user["id"],))
        conn.commit()

        if is_admin:
            session["admin_id"]    = user["id"]
            session["admin_email"] = user["email"]
            session["is_admin"]    = True
            log_admin_action(user["id"], "login", "user", user["id"], {"email": email})
            flash("Welcome back, Admin.", "success")
            return redirect(url_for("admin.admin_dashboard"))

        session["user_id"]    = user["id"]
        session["user_email"] = user["email"]
        flash(f"Welcome back, {email}!", "success")
        return redirect(url_for("student.dashboard"))

    finally:
        cur.close()
        conn.close()


# ── 6. Student Logout ──────────────────────────
@auth_bp.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("user_email", None)
    flash("Logged out successfully.", "success")
    return redirect(url_for("auth.index"))
