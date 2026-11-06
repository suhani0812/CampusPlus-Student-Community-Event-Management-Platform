from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import psycopg2.extras

from helpers import get_db, upload_file_to_cloudinary, role_required

club_head_bp = Blueprint("club_head", __name__)


def is_club_head_of(user_id, club_id):
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("""
            SELECT id FROM user_roles
            WHERE user_id = %s AND role = 'club_head'
              AND club_id = %s AND revoked_at IS NULL
        """, (user_id, club_id))
        return cur.fetchone() is not None
    finally:
        cur.close()
        conn.close()


# ── Club head dashboard ─────────────────────────
@club_head_bp.route("/club-head/<int:club_id>")
@role_required("student", "club_head", "admin")
def club_head_dashboard(club_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))
    if not is_club_head_of(session["user_id"], club_id):
        flash("You don't have access to manage this club.", "danger")
        return redirect(url_for("student.dashboard"))

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT * FROM clubs WHERE id = %s", (club_id,))
        club = cur.fetchone()
        if not club:
            flash("Club not found.", "danger")
            return redirect(url_for("student.dashboard"))

        cur.execute("SELECT * FROM club_gallery WHERE club_id = %s", (club_id,))
        gallery = cur.fetchall()

        cur.execute("""
            SELECT * FROM events WHERE club_id = %s AND deleted_at IS NULL
            ORDER BY created_at DESC
        """, (club_id,))
        events = cur.fetchall()

        return render_template("club_head_manage.html",
            club    = club,
            gallery = gallery,
            events  = events,
        )
    finally:
        cur.close()
        conn.close()


# ── Edit club details ───────────────────────────
@club_head_bp.route("/club-head/<int:club_id>/edit", methods=["POST"])
@role_required("student", "club_head", "admin")
def edit_club(club_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))
    if not is_club_head_of(session["user_id"], club_id):
        flash("Access denied.", "danger")
        return redirect(url_for("student.dashboard"))

    description      = request.form.get("description", "").strip() or None
    requirements     = request.form.get("requirements", "").strip() or None
    instagram_handle = request.form.get("instagram_handle", "").strip() or None
    apply_link       = request.form.get("apply_link", "").strip() or None
    logo_url         = request.form.get("existing_logo_url", "").strip() or None
    banner_url       = request.form.get("existing_banner_url", "").strip() or None

    # Upload new logo if provided
    logo_file = request.files.get("logo")
    if logo_file and logo_file.filename:
        try:
            logo_url = upload_file_to_cloudinary(logo_file, folder="campusplus/clubs/logos")
        except Exception as e:
            print(f"LOGO UPLOAD ERROR: {e}")
            flash("Logo upload failed — keeping existing.", "danger")

    # Upload new banner if provided
    banner_file = request.files.get("banner")
    if banner_file and banner_file.filename:
        try:
            banner_url = upload_file_to_cloudinary(banner_file, folder="campusplus/clubs/banners")
        except Exception as e:
            print(f"BANNER UPLOAD ERROR: {e}")
            flash("Banner upload failed — keeping existing.", "danger")

    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("""
            UPDATE clubs
            SET description = %s, requirements = %s,
                instagram_handle = %s, apply_link = %s,
                logo_url = %s, banner_url = %s
            WHERE id = %s
        """, (description, requirements, instagram_handle, apply_link, logo_url, banner_url, club_id))
        conn.commit()
        flash("Club details updated successfully.", "success")
    except Exception as e:
        conn.rollback()
        print(f"EDIT CLUB ERROR: {e}")
        flash("Something went wrong.", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("club_head.club_head_dashboard", club_id=club_id))


# ── Upload gallery photo ────────────────────────
@club_head_bp.route("/club-head/<int:club_id>/gallery/upload", methods=["POST"])
@role_required("student", "club_head", "admin")
def upload_gallery(club_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))
    if not is_club_head_of(session["user_id"], club_id):
        flash("Access denied.", "danger")
        return redirect(url_for("student.dashboard"))

    photo   = request.files.get("photo")
    caption = request.form.get("caption", "").strip() or None

    if not photo or not photo.filename:
        flash("Please select a photo.", "danger")
        return redirect(url_for("club_head.club_head_dashboard", club_id=club_id))

    try:
        image_url = upload_file_to_cloudinary(photo, folder="campusplus/clubs/gallery")

        conn = get_db()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO club_gallery (club_id, image_url, caption)
            VALUES (%s, %s, %s)
        """, (club_id, image_url, caption))
        conn.commit()
        cur.close()
        conn.close()

        flash("Photo uploaded.", "success")
    except Exception as e:
        print(f"GALLERY UPLOAD ERROR: {e}")
        flash("Upload failed. Please try again.", "danger")

    return redirect(url_for("club_head.club_head_dashboard", club_id=club_id) + "#tab-gallery")


# ── Delete gallery photo ────────────────────────
@club_head_bp.route("/club-head/<int:club_id>/gallery/<int:photo_id>/delete", methods=["POST"])
@role_required("student", "club_head", "admin")
def delete_gallery_photo(club_id, photo_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))
    if not is_club_head_of(session["user_id"], club_id):
        flash("Access denied.", "danger")
        return redirect(url_for("student.dashboard"))

    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("DELETE FROM club_gallery WHERE id = %s AND club_id = %s", (photo_id, club_id))
        conn.commit()
        flash("Photo deleted.", "success")
    except Exception as e:
        conn.rollback()
        print(f"DELETE PHOTO ERROR: {e}")
        flash("Something went wrong.", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("club_head.club_head_dashboard", club_id=club_id))


# ── Add event ───────────────────────────────────
@club_head_bp.route("/club-head/<int:club_id>/events/add", methods=["POST"])
@role_required("student", "club_head", "admin")
def add_event(club_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))
    if not is_club_head_of(session["user_id"], club_id):
        flash("Access denied.", "danger")
        return redirect(url_for("student.dashboard"))

    user_id           = session["user_id"]
    title             = request.form.get("title", "").strip()
    description       = request.form.get("description", "").strip() or None
    type_             = request.form.get("type")
    location_type     = request.form.get("location_type")
    venue             = request.form.get("venue", "").strip() or None
    event_date        = request.form.get("event_date") or None
    end_date          = request.form.get("end_date") or None
    registration_link = request.form.get("registration_link", "").strip() or None
    poster_url        = None

    if not title:
        flash("Event title is required.", "danger")
        return redirect(url_for("club_head.club_head_dashboard", club_id=club_id))

    # Upload poster if provided
    poster_file = request.files.get("poster")
    if poster_file and poster_file.filename:
        try:
            poster_url = upload_file_to_cloudinary(poster_file, folder="campusplus/events")
        except Exception as e:
            print(f"POSTER UPLOAD ERROR: {e}")
            flash("Poster upload failed — event saved without poster.", "danger")

    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO events
                (club_id, created_by, title, description, type, location_type,
                 venue, event_date, end_date, registration_link, poster_url)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (club_id, user_id, title, description, type_, location_type,
              venue, event_date, end_date, registration_link, poster_url))
        conn.commit()
        flash("Event submitted for admin review.", "success")
    except Exception as e:
        conn.rollback()
        print(f"ADD EVENT ERROR: {e}")
        flash("Something went wrong.", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("club_head.club_head_dashboard", club_id=club_id))


# ── Delete event ────────────────────────────────
@club_head_bp.route("/club-head/<int:club_id>/events/<int:event_id>/delete", methods=["POST"])
@role_required("club_head", "admin")
def delete_event(club_id, event_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))
    if not is_club_head_of(session["user_id"], club_id):
        flash("Access denied.", "danger")
        return redirect(url_for("student.dashboard"))

    conn = get_db()
    cur  = conn.cursor()
    try:
        # Soft delete — only if it belongs to this club
        cur.execute("""
            UPDATE events SET deleted_at = NOW()
            WHERE id = %s AND club_id = %s
        """, (event_id, club_id))
        conn.commit()
        flash("Event deleted.", "success")
    except Exception as e:
        conn.rollback()
        print(f"DELETE EVENT ERROR: {e}")
        flash("Something went wrong.", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("club_head.club_head_dashboard", club_id=club_id))