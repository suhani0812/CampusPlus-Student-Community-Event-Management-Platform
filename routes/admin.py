"""
routes/admin.py
Admin panel routes: dashboard + all moderation/management pages.
Built incrementally — role-requests, content moderation, clubs,
courses, users, companies, logs
"""

import psycopg2.extras
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response
from helpers import get_db, log_admin_action, role_required, upload_file_to_cloudinary
import csv
import io
import json as json_lib
from urllib.parse import urlencode

admin_bp = Blueprint("admin", __name__)


# ── Admin: Dashboard ────────────────────────────
@admin_bp.route("/admin/dashboard")
@role_required("admin")
def admin_dashboard():
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT COUNT(*) FROM role_requests WHERE status = 'pending'")
        pending_role_requests = cur.fetchone()[0]

        cur.execute("""
            SELECT
              (SELECT COUNT(*) FROM academic_content WHERE status='pending' AND deleted_at IS NULL) +
              (SELECT COUNT(*) FROM events            WHERE status='pending' AND deleted_at IS NULL) +
              (SELECT COUNT(*) FROM accommodations     WHERE status='pending' AND deleted_at IS NULL) +
              (SELECT COUNT(*) FROM placement_drives   WHERE status='pending' AND deleted_at IS NULL)
            AS total
        """)
        pending_content = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM users WHERE is_verified = TRUE")
        total_users = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM clubs")
        total_clubs = cur.fetchone()[0]

        return render_template("admin_dashboard.html",
            pending_role_requests = pending_role_requests,
            pending_content       = pending_content,
            total_users           = total_users,
            total_clubs           = total_clubs,
        )
    finally:
        cur.close()
        conn.close()


# ── Admin: Logout ───────────────────────────────
@admin_bp.route("/admin/logout")
@role_required("admin")
def admin_logout():
    session.pop("admin_id", None)
    session.pop("admin_email", None)
    session.pop("is_admin", None)
    flash("Logged out of admin panel.", "success")
    return redirect(url_for("auth.index"))


# ── Admin: Role Requests ────────────────────────
@admin_bp.route("/admin/role-requests")
@role_required("admin")
def role_requests():
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("""
            SELECT rr.id, rr.requested_role, rr.reason, rr.requested_at,
                   u.email, c.name AS club_name
            FROM role_requests rr
            JOIN users u ON u.id = rr.user_id
            LEFT JOIN clubs c ON c.id = rr.club_id
            WHERE rr.status = 'pending'
            ORDER BY rr.requested_at ASC
        """)
        pending_requests = cur.fetchall()

        cur.execute("""
            SELECT rr.id, rr.requested_role, rr.status, rr.reviewed_at,
                   u.email, c.name AS club_name
            FROM role_requests rr
            JOIN users u ON u.id = rr.user_id
            LEFT JOIN clubs c ON c.id = rr.club_id
            WHERE rr.status != 'pending'
            ORDER BY rr.reviewed_at DESC
            LIMIT 50
        """)
        history_requests = cur.fetchall()

        return render_template("admin_role_requests.html",
            pending_requests  = pending_requests,
            history_requests  = history_requests,
            pending_count     = len(pending_requests),
        )
    finally:
        cur.close()
        conn.close()


# ── Admin: Approve a role request ───────────────
@admin_bp.route("/admin/role-requests/<int:request_id>/approve", methods=["POST"])
@role_required("admin")
def approve_role_request(request_id):
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    admin_id = session["admin_id"]
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("""
            SELECT user_id, requested_role, club_id
            FROM role_requests WHERE id = %s AND status = 'pending'
        """, (request_id,))
        req = cur.fetchone()

        if not req:
            flash("Request not found or already reviewed.", "danger")
            return redirect(url_for("admin.role_requests"))

        # Grant the role
        cur.execute("""
            INSERT INTO user_roles (user_id, role, club_id, assigned_by)
            VALUES (%s, %s, %s, %s)
        """, (req["user_id"], req["requested_role"], req["club_id"], admin_id))

        # Mark request approved
        cur.execute("""
            UPDATE role_requests
            SET status = 'approved', reviewed_by = %s, reviewed_at = NOW()
            WHERE id = %s
        """, (admin_id, request_id))
        conn.commit()

        log_admin_action(admin_id, "approve", "role_request", request_id, {
            "user_id": req["user_id"],
            "role": req["requested_role"],
        })

        flash("Role request approved.", "success")
        return redirect(url_for("admin.role_requests"))

    except Exception as e:
        conn.rollback()
        print(f"APPROVE ROLE ERROR: {e}")
        log_admin_action(admin_id, "approve", "role_request", request_id, {"error": str(e)}, status="fail")
        flash("Something went wrong.", "danger")
        return redirect(url_for("admin.role_requests"))
    finally:
        cur.close()
        conn.close()


# ── Admin: Deny a role request ──────────────────
@admin_bp.route("/admin/role-requests/<int:request_id>/deny", methods=["POST"])
@role_required("admin")
def deny_role_request(request_id):
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    admin_id = session["admin_id"]
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("""
            UPDATE role_requests
            SET status = 'denied', reviewed_by = %s, reviewed_at = NOW()
            WHERE id = %s AND status = 'pending'
        """, (admin_id, request_id))
        conn.commit()

        log_admin_action(admin_id, "deny", "role_request", request_id)

        flash("Role request denied.", "success")
        return redirect(url_for("admin.role_requests"))

    except Exception as e:
        conn.rollback()
        print(f"DENY ROLE ERROR: {e}")
        log_admin_action(admin_id, "deny", "role_request", request_id, {"error": str(e)}, status="fail")
        flash("Something went wrong.", "danger")
        return redirect(url_for("admin.role_requests"))
    finally:
        cur.close()
        conn.close()

# ── Admin: Content Moderation ───────────────────
@admin_bp.route("/admin/content")
@role_required("admin")
def content_moderation():
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("""
            SELECT ac.id, ac.type, ac.title, ac.tags, ac.created_at,
                   s.name AS subject_name, c.name AS course_name, u.email AS uploaded_by_email
            FROM academic_content ac
            LEFT JOIN subjects s ON s.id = ac.subject_id
            LEFT JOIN courses c  ON c.id = ac.course_id
            JOIN users u ON u.id = ac.uploaded_by
            WHERE ac.status = 'pending' AND ac.deleted_at IS NULL
            ORDER BY ac.created_at ASC
        """)
        academic_content = cur.fetchall()

        cur.execute("""
            SELECT e.id, e.title, e.type, e.location_type, e.venue, e.event_date, e.poster_url,
                   cl.name AS club_name, u.email AS created_by_email
            FROM events e
            JOIN clubs cl ON cl.id = e.club_id
            JOIN users u  ON u.id = e.created_by
            WHERE e.status = 'pending' AND e.deleted_at IS NULL
            ORDER BY e.created_at ASC
        """)
        events = cur.fetchall()

        cur.execute("""
            SELECT a.id, a.type, a.title, a.address, a.rent, a.location_url, a.created_at,
                   u.email AS listed_by_email
            FROM accommodations a
            JOIN users u ON u.id = a.listed_by
            WHERE a.status = 'pending' AND a.deleted_at IS NULL
            ORDER BY a.created_at ASC
        """)
        accommodations = cur.fetchall()

        cur.execute("""
            SELECT pd.id, pd.role_title, pd.package_lpa, pd.drive_date, pd.jd_file_url,
                   co.name AS company_name, u.email AS added_by_email
            FROM placement_drives pd
            JOIN companies co ON co.id = pd.company_id
            JOIN users u ON u.id = pd.added_by
            WHERE pd.status = 'pending' AND pd.deleted_at IS NULL
            ORDER BY pd.created_at ASC
        """)
        placements = cur.fetchall()

        total_pending = len(academic_content) + len(events) + len(accommodations) + len(placements)

        return render_template("admin_content.html",
            academic_content = academic_content,
            events           = events,
            accommodations   = accommodations,
            placements       = placements,
            total_pending    = total_pending,
        )
    finally:
        cur.close()
        conn.close()


# ── Admin: Approve/Deny content (generic handler) ───────────────
# target_type: note | event | accommodation | placement
# table_map links the URL keyword to the actual DB table
_CONTENT_TABLE_MAP = {
    "note":          "academic_content",
    "event":         "events",
    "accommodation": "accommodations",
    "placement":     "placement_drives",
}

# log target_type must match admin_logs CHECK constraint;
# academic_content rows are logged using their actual type (note/pyq/project)
def _resolve_log_target_type(content_kind, item_id):
    if content_kind != "note":
        return content_kind
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("SELECT type FROM academic_content WHERE id = %s", (item_id,))
        row = cur.fetchone()
        return row[0] if row else "note"   # 'notes' | 'pyq' | 'project'
    finally:
        cur.close()
        conn.close()


@admin_bp.route("/admin/content/<content_kind>/<int:item_id>/approve", methods=["POST"])
@role_required("admin")
def approve_content(content_kind, item_id):
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    table = _CONTENT_TABLE_MAP.get(content_kind)
    if not table:
        flash("Invalid content type.", "danger")
        return redirect(url_for("admin.content_moderation"))

    admin_id = session["admin_id"]
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute(f"UPDATE {table} SET status = 'approved' WHERE id = %s AND status = 'pending'", (item_id,))
        conn.commit()

        log_target = _resolve_log_target_type(content_kind, item_id)
        log_admin_action(admin_id, "approve", log_target, item_id)

        flash("Content approved.", "success")
    except Exception as e:
        conn.rollback()
        print(f"APPROVE CONTENT ERROR: {e}")
        log_admin_action(admin_id, "approve", content_kind, item_id, {"error": str(e)}, status="fail")
        flash("Something went wrong.", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("admin.content_moderation"))


@admin_bp.route("/admin/content/<content_kind>/<int:item_id>/deny", methods=["POST"])
@role_required("admin")
def deny_content(content_kind, item_id):
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    table = _CONTENT_TABLE_MAP.get(content_kind)
    if not table:
        flash("Invalid content type.", "danger")
        return redirect(url_for("admin.content_moderation"))

    admin_id = session["admin_id"]
    conn = get_db()
    cur  = conn.cursor()
    try:
        log_target = _resolve_log_target_type(content_kind, item_id)

        # Denied content is soft-deleted (status + deleted_at) per the agreed flow
        cur.execute(f"""
            UPDATE {table}
            SET status = 'denied', deleted_at = NOW()
            WHERE id = %s AND status = 'pending'
        """, (item_id,))
        conn.commit()

        log_admin_action(admin_id, "deny", log_target, item_id)

        flash("Content denied and removed.", "success")
    except Exception as e:
        conn.rollback()
        print(f"DENY CONTENT ERROR: {e}")
        log_admin_action(admin_id, "deny", content_kind, item_id, {"error": str(e)}, status="fail")
        flash("Something went wrong.", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("admin.content_moderation"))

# ── Admin: Clubs ─────────────────────────────────
@admin_bp.route("/admin/clubs")
@role_required("admin")
def manage_clubs():
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT * FROM clubs ORDER BY name")
        clubs = [dict(row) for row in cur.fetchall()]
        return render_template("admin_clubs.html", clubs=clubs)
    finally:
        cur.close()
        conn.close()


@admin_bp.route("/admin/clubs/add", methods=["POST"])
@role_required("admin")
def add_club():
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    admin_id = session["admin_id"]
    name             = request.form.get("name", "").strip()
    category         = request.form.get("category", "other")
    description      = request.form.get("description", "").strip() or None
    requirements     = request.form.get("requirements", "").strip() or None
    instagram_handle = request.form.get("instagram_handle", "").strip() or None
    apply_link       = request.form.get("apply_link", "").strip() or None

    if not name:
        flash("Club name is required.", "danger")
        return redirect(url_for("admin.manage_clubs"))

    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO clubs (name, category, description, requirements, instagram_handle, apply_link)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (name, category, description, requirements, instagram_handle, apply_link))
        new_id = cur.fetchone()[0]
        conn.commit()

        log_admin_action(admin_id, "add", "club", new_id, {"name": name})
        flash(f"Club '{name}' added.", "success")
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        flash("A club with this name already exists.", "danger")
    except Exception as e:
        conn.rollback()
        print(f"ADD CLUB ERROR: {e}")
        log_admin_action(admin_id, "add", "club", None, {"name": name, "error": str(e)}, status="fail")
        flash("Something went wrong.", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("admin.manage_clubs"))


@admin_bp.route("/admin/clubs/<int:club_id>/edit", methods=["POST"])
@role_required("admin")
def edit_club(club_id):
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    admin_id = session["admin_id"]
    name             = request.form.get("name", "").strip()
    category         = request.form.get("category", "other")
    description      = request.form.get("description", "").strip() or None
    requirements     = request.form.get("requirements", "").strip() or None
    instagram_handle = request.form.get("instagram_handle", "").strip() or None
    apply_link       = request.form.get("apply_link", "").strip() or None

    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("""
            UPDATE clubs
            SET name = %s, category = %s, description = %s,
                requirements = %s, instagram_handle = %s, apply_link = %s
            WHERE id = %s
        """, (name, category, description, requirements, instagram_handle, apply_link, club_id))
        conn.commit()

        log_admin_action(admin_id, "edit", "club", club_id, {"name": name})
        flash(f"Club '{name}' updated.", "success")
    except Exception as e:
        conn.rollback()
        print(f"EDIT CLUB ERROR: {e}")
        log_admin_action(admin_id, "edit", "club", club_id, {"error": str(e)}, status="fail")
        flash("Something went wrong.", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("admin.manage_clubs"))


@admin_bp.route("/admin/clubs/<int:club_id>/delete", methods=["POST"])
@role_required("admin")
def delete_club(club_id):
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    admin_id = session["admin_id"]
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("SELECT name FROM clubs WHERE id = %s", (club_id,))
        row = cur.fetchone()
        club_name = row[0] if row else "Unknown"

        cur.execute("DELETE FROM clubs WHERE id = %s", (club_id,))
        conn.commit()

        log_admin_action(admin_id, "delete", "club", club_id, {"name": club_name})
        flash(f"Club '{club_name}' deleted.", "success")
    except Exception as e:
        conn.rollback()
        print(f"DELETE CLUB ERROR: {e}")
        log_admin_action(admin_id, "delete", "club", club_id, {"error": str(e)}, status="fail")
        flash("Something went wrong.", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("admin.manage_clubs"))

# ── Admin: Courses & Subjects ───────────────────
import re

def _slugify(name):
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


@admin_bp.route("/admin/courses")
@role_required("admin")
def manage_courses():
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT * FROM courses ORDER BY name")
        courses = [dict(row) for row in cur.fetchall()]

        cur.execute("SELECT * FROM subjects ORDER BY name")
        all_subjects = [dict(row) for row in cur.fetchall()]

        # Attach linked subjects to each course
        for course in courses:
            cur.execute("""
                SELECT s.id, s.name FROM subjects s
                JOIN course_subjects cs ON cs.subject_id = s.id
                WHERE cs.course_id = %s
                ORDER BY s.name
            """, (course["id"],))
            linked = [dict(row) for row in cur.fetchall()]
            course["subjects"] = linked
            course["subject_ids"] = [s["id"] for s in linked]

        return render_template("admin_courses.html", courses=courses, all_subjects=all_subjects)
    finally:
        cur.close()
        conn.close()


@admin_bp.route("/admin/courses/add", methods=["POST"])
@role_required("admin")
def add_course():
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    admin_id = session["admin_id"]
    name = request.form.get("name", "").strip()
    if not name:
        flash("Course name is required.", "danger")
        return redirect(url_for("admin.manage_courses"))

    slug = _slugify(name)
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("INSERT INTO courses (name, slug) VALUES (%s, %s) RETURNING id", (name, slug))
        new_id = cur.fetchone()[0]
        conn.commit()
        log_admin_action(admin_id, "add", "course", new_id, {"name": name})
        flash(f"Course '{name}' added.", "success")
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        flash("A course with this name already exists.", "danger")
    except Exception as e:
        conn.rollback()
        print(f"ADD COURSE ERROR: {e}")
        log_admin_action(admin_id, "add", "course", None, {"error": str(e)}, status="fail")
        flash("Something went wrong.", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("admin.manage_courses"))


@admin_bp.route("/admin/courses/<int:course_id>/edit", methods=["POST"])
@role_required("admin")
def edit_course(course_id):
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    admin_id = session["admin_id"]
    name = request.form.get("name", "").strip()
    slug = _slugify(name)

    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("UPDATE courses SET name = %s, slug = %s WHERE id = %s", (name, slug, course_id))
        conn.commit()
        log_admin_action(admin_id, "edit", "course", course_id, {"name": name})
        flash(f"Course updated.", "success")
    except Exception as e:
        conn.rollback()
        print(f"EDIT COURSE ERROR: {e}")
        log_admin_action(admin_id, "edit", "course", course_id, {"error": str(e)}, status="fail")
        flash("Something went wrong.", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("admin.manage_courses"))


@admin_bp.route("/admin/courses/<int:course_id>/delete", methods=["POST"])
@role_required("admin")
def delete_course(course_id):
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    admin_id = session["admin_id"]
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("SELECT name FROM courses WHERE id = %s", (course_id,))
        row = cur.fetchone()
        course_name = row[0] if row else "Unknown"

        cur.execute("DELETE FROM courses WHERE id = %s", (course_id,))
        conn.commit()
        log_admin_action(admin_id, "delete", "course", course_id, {"name": course_name})
        flash(f"Course '{course_name}' deleted.", "success")
    except Exception as e:
        conn.rollback()
        print(f"DELETE COURSE ERROR: {e}")
        log_admin_action(admin_id, "delete", "course", course_id, {"error": str(e)}, status="fail")
        flash("Something went wrong.", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("admin.manage_courses"))


# ── Link an existing subject to a course ────────
@admin_bp.route("/admin/courses/<int:course_id>/subjects/link", methods=["POST"])
@role_required("admin")
def link_subject(course_id):
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    admin_id   = session["admin_id"]
    subject_id = request.form.get("subject_id")

    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO course_subjects (course_id, subject_id)
            VALUES (%s, %s) ON CONFLICT DO NOTHING
        """, (course_id, subject_id))
        conn.commit()
        log_admin_action(admin_id, "edit", "subject", subject_id, {"linked_to_course": course_id})
        flash("Subject linked.", "success")
    except Exception as e:
        conn.rollback()
        print(f"LINK SUBJECT ERROR: {e}")
        flash("Something went wrong.", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("admin.manage_courses"))


# ── Create a brand new subject and link it ──────
@admin_bp.route("/admin/courses/<int:course_id>/subjects/create", methods=["POST"])
@role_required("admin")
def create_and_link_subject(course_id):
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    admin_id     = session["admin_id"]
    subject_name = request.form.get("subject_name", "").strip()

    if not subject_name:
        flash("Subject name is required.", "danger")
        return redirect(url_for("admin.manage_courses"))

    conn = get_db()
    cur  = conn.cursor()
    try:
        # Insert subject (or get existing id if name already exists)
        cur.execute("""
            INSERT INTO subjects (name) VALUES (%s)
            ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
        """, (subject_name,))
        subject_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO course_subjects (course_id, subject_id)
            VALUES (%s, %s) ON CONFLICT DO NOTHING
        """, (course_id, subject_id))
        conn.commit()

        log_admin_action(admin_id, "add", "subject", subject_id, {"name": subject_name, "course_id": course_id})
        flash(f"Subject '{subject_name}' created and linked.", "success")
    except Exception as e:
        conn.rollback()
        print(f"CREATE SUBJECT ERROR: {e}")
        log_admin_action(admin_id, "add", "subject", None, {"error": str(e)}, status="fail")
        flash("Something went wrong.", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("admin.manage_courses"))


# ── Unlink a subject from a course (doesn't delete the subject itself) ──
@admin_bp.route("/admin/courses/<int:course_id>/subjects/<int:subject_id>/unlink", methods=["POST"])
@role_required("admin")
def unlink_subject(course_id, subject_id):
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    admin_id = session["admin_id"]
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("""
            DELETE FROM course_subjects WHERE course_id = %s AND subject_id = %s
        """, (course_id, subject_id))
        conn.commit()
        log_admin_action(admin_id, "edit", "subject", subject_id, {"unlinked_from_course": course_id})
        flash("Subject unlinked from course.", "success")
    except Exception as e:
        conn.rollback()
        print(f"UNLINK SUBJECT ERROR: {e}")
        flash("Something went wrong.", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("admin.manage_courses"))

# ── Admin: Users ────────────────────────────────
@admin_bp.route("/admin/users")
@role_required("admin")
def manage_users():
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    search = request.args.get("search", "").strip()
    role_filter = request.args.get("role", "").strip()

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        # Load all verified users; the page filters this list instantly as the admin types.
        query = """
            SELECT u.id, u.email, u.full_name, u.created_at, u.last_login
            FROM users u
            WHERE u.is_verified = TRUE
            ORDER BY u.created_at DESC
        """

        cur.execute(query)
        users = cur.fetchall()

        roles_by_user = {}
        if users:
            user_ids = [u["id"] for u in users]
            # Fetch active roles with club name if club head
            cur.execute("""
                SELECT ur.id as role_id, ur.user_id, ur.role, ur.club_id, c.name as club_name
                FROM user_roles ur
                LEFT JOIN clubs c ON c.id = ur.club_id
                WHERE ur.user_id IN %s AND ur.revoked_at IS NULL
                ORDER BY ur.assigned_at DESC
            """, (tuple(user_ids),))
            roles_list = cur.fetchall()

            for r in roles_list:
                uid = r["user_id"]
                if uid not in roles_by_user:
                    roles_by_user[uid] = []
                roles_by_user[uid].append(r)

        undo_role_id = session.pop("undo_revoke_role_id", None)
        undo_role_name = session.pop("undo_revoke_role_name", None)
        undo_user_email = session.pop("undo_revoke_user_email", None)

        return render_template("admin_users.html",
            users           = users,
            roles_by_user   = roles_by_user,
            search          = search,
            role_filter     = role_filter,
            undo_role_id    = undo_role_id,
            undo_role_name  = undo_role_name,
            undo_user_email = undo_user_email
        )
    finally:
        cur.close()
        conn.close()


@admin_bp.route("/admin/users/roles/<int:role_id>/revoke", methods=["POST"])
@role_required("admin")
def revoke_user_role(role_id):
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    admin_id = session["admin_id"]
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        # Check if the active role exists and get user details
        cur.execute("""
            SELECT ur.user_id, ur.role, ur.club_id, u.email
            FROM user_roles ur
            JOIN users u ON u.id = ur.user_id
            WHERE ur.id = %s AND ur.revoked_at IS NULL
        """, (role_id,))
        role_info = cur.fetchone()

        if not role_info:
            flash("Active role not found.", "danger")
            return redirect(url_for("admin.manage_users"))

        # Update revoked_at
        cur.execute("""
            UPDATE user_roles
            SET revoked_at = NOW()
            WHERE id = %s
        """, (role_id,))
        conn.commit()

        # Log admin action
        log_admin_action(admin_id, "revoke", "user", role_info["user_id"], {
            "user_email": role_info["email"],
            "role": role_info["role"],
            "club_id": role_info["club_id"]
        })

        # Save to session for undo functionality
        session["undo_revoke_role_id"] = role_id
        session["undo_revoke_role_name"] = role_info["role"]
        session["undo_revoke_user_email"] = role_info["email"]

        flash(f"Role '{role_info['role'].replace('_', ' ').title()}' revoked for {role_info['email']}.", "success")
    except Exception as e:
        conn.rollback()
        print(f"REVOKE ROLE ERROR: {e}")
        flash("Something went wrong.", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("admin.manage_users"))


@admin_bp.route("/admin/users/roles/<int:role_id>/restore", methods=["POST"])
@role_required("admin")
def restore_user_role(role_id):
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    admin_id = session["admin_id"]
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        # Check if role exists and was revoked
        cur.execute("""
            SELECT ur.user_id, ur.role, u.email
            FROM user_roles ur
            JOIN users u ON u.id = ur.user_id
            WHERE ur.id = %s AND ur.revoked_at IS NOT NULL
        """, (role_id,))
        role_info = cur.fetchone()

        if not role_info:
            flash("Role not found or not revoked.", "danger")
            return redirect(url_for("admin.manage_users"))

        # Re-activate the role
        cur.execute("""
            UPDATE user_roles
            SET revoked_at = NULL
            WHERE id = %s
        """, (role_id,))
        conn.commit()

        # Log action
        log_admin_action(admin_id, "add", "user", role_info["user_id"], {
            "user_email": role_info["email"],
            "role": role_info["role"],
            "restored": True
        })

        flash(f"Restored '{role_info['role'].replace('_', ' ').title()}' role for {role_info['email']}.", "success")
    except Exception as e:
        conn.rollback()
        print(f"RESTORE ROLE ERROR: {e}")
        flash("Something went wrong.", "danger")
    finally:
        cur.close()
        conn.close()

    # Clear undo session state
    session.pop("undo_revoke_role_id", None)
    session.pop("undo_revoke_role_name", None)
    session.pop("undo_revoke_user_email", None)

    return redirect(url_for("admin.manage_users"))


# ── Admin: Companies ────────────────────────────
@admin_bp.route("/admin/companies")
@role_required("admin")
def manage_companies():
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("""
            SELECT c.*, COUNT(pd.id) AS drive_count
            FROM companies c
            LEFT JOIN placement_drives pd ON pd.company_id = c.id AND pd.deleted_at IS NULL
            GROUP BY c.id
            ORDER BY c.name
        """)
        companies = [dict(row) for row in cur.fetchall()]
        return render_template("admin_companies.html", companies=companies)
    finally:
        cur.close()
        conn.close()


@admin_bp.route("/admin/companies/add", methods=["POST"])
def add_company():
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    admin_id = session["admin_id"]
    name     = request.form.get("name", "").strip()
    website  = request.form.get("website", "").strip() or None
    logo_url = None

    if not name:
        flash("Company name is required.", "danger")
        return redirect(url_for("admin.manage_companies"))

    # Upload logo if provided
    logo_file = request.files.get("logo")
    if logo_file and logo_file.filename:
        try:
            logo_url = upload_file_to_cloudinary(logo_file, folder="campusplus/companies")
        except Exception as e:
            print(f"LOGO UPLOAD ERROR: {e}")
            flash("Logo upload failed — company saved without logo.", "danger")

    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO companies (name, website, logo_url) VALUES (%s, %s, %s) RETURNING id
        """, (name, website, logo_url))
        new_id = cur.fetchone()[0]
        conn.commit()
        log_admin_action(admin_id, "add", "company", new_id, {"name": name})
        flash(f"Company '{name}' added.", "success")
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        flash("A company with this name already exists.", "danger")
    except Exception as e:
        conn.rollback()
        print(f"ADD COMPANY ERROR: {e}")
        log_admin_action(admin_id, "add", "company", None, {"error": str(e)}, status="fail")
        flash("Something went wrong.", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("admin.manage_companies"))


@admin_bp.route("/admin/companies/<int:company_id>/edit", methods=["POST"])
def edit_company(company_id):
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    admin_id     = session["admin_id"]
    name         = request.form.get("name", "").strip()
    website      = request.form.get("website", "").strip() or None
    existing_logo = request.form.get("existing_logo_url", "").strip() or None
    logo_url     = existing_logo  # default to existing

    # Upload new logo if provided
    logo_file = request.files.get("logo")
    if logo_file and logo_file.filename:
        try:
            logo_url = upload_file_to_cloudinary(logo_file, folder="campusplus/companies")
        except Exception as e:
            print(f"LOGO UPLOAD ERROR: {e}")
            flash("Logo upload failed — keeping existing logo.", "danger")

    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("""
            UPDATE companies SET name = %s, website = %s, logo_url = %s WHERE id = %s
        """, (name, website, logo_url, company_id))
        conn.commit()
        log_admin_action(admin_id, "edit", "company", company_id, {"name": name})
        flash(f"Company '{name}' updated.", "success")
    except Exception as e:
        conn.rollback()
        print(f"EDIT COMPANY ERROR: {e}")
        log_admin_action(admin_id, "edit", "company", company_id, {"error": str(e)}, status="fail")
        flash("Something went wrong.", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("admin.manage_companies"))


@admin_bp.route("/admin/companies/<int:company_id>/delete", methods=["POST"])
def delete_company(company_id):
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    admin_id = session["admin_id"]
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("SELECT name FROM companies WHERE id = %s", (company_id,))
        row  = cur.fetchone()
        name = row[0] if row else "Unknown"

        cur.execute("DELETE FROM companies WHERE id = %s", (company_id,))
        conn.commit()
        log_admin_action(admin_id, "delete", "company", company_id, {"name": name})
        flash(f"Company '{name}' deleted.", "success")
    except Exception as e:
        conn.rollback()
        print(f"DELETE COMPANY ERROR: {e}")
        log_admin_action(admin_id, "delete", "company", company_id, {"error": str(e)}, status="fail")
        flash("Something went wrong.", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("admin.manage_companies"))

PER_PAGE = 50

@admin_bp.route("/admin/logs")
@role_required("admin")
def view_logs():
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    # Filters from query string
    search      = request.args.get("search", "").strip()
    action      = request.args.get("action", "").strip()
    target_type = request.args.get("target_type", "").strip()
    status      = request.args.get("status", "").strip()
    date_from   = request.args.get("date_from", "").strip()
    date_to     = request.args.get("date_to", "").strip()
    page        = max(1, int(request.args.get("page", 1)))

    filters = {
        "search": search, "action": action, "target_type": target_type,
        "status": status, "date_from": date_from, "date_to": date_to,
    }

    # Build dynamic WHERE clause
    conditions = []
    params     = []

    if search:
        conditions.append("""
            (al.action ILIKE %s OR al.target_type ILIKE %s
             OR CAST(al.target_id AS TEXT) ILIKE %s
             OR CAST(al.details AS TEXT) ILIKE %s
             OR CAST(al.ip_address AS TEXT) ILIKE %s)
        """)
        search_pattern = f"%{search}%"
        params.extend([search_pattern] * 5)
    if action:
        conditions.append("al.action = %s")
        params.append(action)
    if target_type:
        conditions.append("al.target_type = %s")
        params.append(target_type)
    if status:
        conditions.append("al.status = %s")
        params.append(status)
    if date_from:
        conditions.append("al.created_at >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("al.created_at <= %s::date + interval '1 day'")
        params.append(date_to)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute(f"SELECT COUNT(*) FROM admin_logs al {where}", params)
        total_logs  = cur.fetchone()[0]
        total_pages = max(1, (total_logs + PER_PAGE - 1) // PER_PAGE)
        offset      = (page - 1) * PER_PAGE

        cur.execute(f"""
            SELECT al.id, al.action, al.target_type, al.target_id,
                   al.details, al.status, al.ip_address, al.created_at
            FROM admin_logs al
            {where}
            ORDER BY al.created_at DESC
            LIMIT %s OFFSET %s
        """, params + [PER_PAGE, offset])
        logs = cur.fetchall()

        # Parse JSONB details into dict for template
        parsed_logs = []
        for log in logs:
            log = dict(log)
            if log["details"] and isinstance(log["details"], str):
                try:
                    log["details"] = json_lib.loads(log["details"])
                except Exception:
                    log["details"] = {}
            parsed_logs.append(log)

        # Build query string for export + pagination links
        filter_params = {k: v for k, v in filters.items() if v}
        current_query = urlencode(filter_params)

        return render_template("admin_logs.html",
            logs          = parsed_logs,
            filters       = filters,
            total_logs    = total_logs,
            total_pages   = total_pages,
            page          = page,
            current_query = current_query,
        )
    finally:
        cur.close()
        conn.close()


# ── Admin: Export logs as CSV ───────────────────
@admin_bp.route("/admin/logs/export")
@role_required("admin")

def export_logs():
    if not session.get("is_admin"):
        return redirect(url_for("auth.index"))

    admin_id    = session["admin_id"]
    search      = request.args.get("search", "").strip()
    action      = request.args.get("action", "").strip()
    target_type = request.args.get("target_type", "").strip()
    status      = request.args.get("status", "").strip()
    date_from   = request.args.get("date_from", "").strip()
    date_to     = request.args.get("date_to", "").strip()

    conditions = []
    params     = []
    if search:
        conditions.append("""
            (action ILIKE %s OR target_type ILIKE %s
             OR CAST(target_id AS TEXT) ILIKE %s
             OR CAST(details AS TEXT) ILIKE %s
             OR CAST(ip_address AS TEXT) ILIKE %s)
        """)
        search_pattern = f"%{search}%"
        params.extend([search_pattern] * 5)
    if action:
        conditions.append("action = %s"); params.append(action)
    if target_type:
        conditions.append("target_type = %s"); params.append(target_type)
    if status:
        conditions.append("status = %s"); params.append(status)
    if date_from:
        conditions.append("created_at >= %s"); params.append(date_from)
    if date_to:
        conditions.append("created_at <= %s::date + interval '1 day'"); params.append(date_to)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute(f"""
            SELECT id, action, target_type, target_id, details, status, ip_address, created_at
            FROM admin_logs {where}
            ORDER BY created_at DESC
        """, params)
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    # Build CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Action", "Target Type", "Target ID", "Details", "Status", "IP Address", "Timestamp"])
    for row in rows:
        writer.writerow([
            row[0], row[1], row[2], row[3] or "",
            row[4] if row[4] else "",
            row[5], row[6] or "", row[7].strftime("%Y-%m-%d %H:%M:%S")
        ])

    log_admin_action(admin_id, "export", "user", None, {"filters": {
        "search": search, "action": action, "target_type": target_type,
        "status": status, "date_from": date_from, "date_to": date_to,
    }})

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=campusplus_admin_logs.csv"}
    )