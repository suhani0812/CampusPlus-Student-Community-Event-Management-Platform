import os
import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import psycopg2.extras
from helpers import get_db, upload_file_to_cloudinary, role_required

academics_bp = Blueprint("academics", __name__)

ALLOWED_EXTENSIONS = {
    ".pdf", ".ppt", ".pptx", ".doc", ".docx",
    ".zip", ".rar", ".tar.gz", ".ipynb", ".txt"
}


def _get_department(course_name: str) -> dict:
    """Categorizes course for badge styling & filtering."""
    name_l = course_name.lower()
    if any(k in name_l for k in ["b.tech", "m.tech", "engineering", "petroleum"]):
        return {"code": "engineering", "name": "Engineering & Tech", "icon": "⚙️", "badge": "badge-tech"}
    if any(k in name_l for k in ["computer science", "data science", "mca", "cloud", "cybersecurity"]):
        return {"code": "computing", "name": "Computing & IT", "icon": "💻", "badge": "badge-comp"}
    if any(k in name_l for k in ["bba", "mba", "b.com", "commerce", "management"]):
        return {"code": "management", "name": "Business & Mgmt", "icon": "📈", "badge": "badge-mgmt"}
    if any(k in name_l for k in ["design", "b.des", "liberal arts", "arts"]):
        return {"code": "design", "name": "Design & Arts", "icon": "🎨", "badge": "badge-design"}
    if any(k in name_l for k in ["physics", "bio", "chemical"]):
        return {"code": "science", "name": "Sciences", "icon": "🔬", "badge": "badge-sci"}
    if "llb" in name_l:
        return {"code": "law", "name": "Law & Justice", "icon": "⚖️", "badge": "badge-law"}
    return {"code": "other", "name": "Academics", "icon": "🎓", "badge": "badge-other"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAGE 1: /academics (Course Grid with Search)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@academics_bp.route("/academics")
@role_required("student", "club_head", "placement_coordinator", "admin")
def courses_grid():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("""
            SELECT 
                c.id, 
                c.name, 
                c.slug, 
                c.created_at,
                COUNT(DISTINCT cs.subject_id) AS subject_count,
                COUNT(DISTINCT CASE WHEN ac_sub.type = 'notes' AND ac_sub.status = 'approved' AND ac_sub.deleted_at IS NULL THEN ac_sub.id END) AS notes_count,
                COUNT(DISTINCT CASE WHEN ac_sub.type = 'pyq' AND ac_sub.status = 'approved' AND ac_sub.deleted_at IS NULL THEN ac_sub.id END) AS pyqs_count,
                COUNT(DISTINCT CASE WHEN ac_course.type = 'project' AND ac_course.status = 'approved' AND ac_course.deleted_at IS NULL THEN ac_course.id END) AS projects_count
            FROM courses c
            LEFT JOIN course_subjects cs ON cs.course_id = c.id
            LEFT JOIN academic_content ac_sub ON ac_sub.subject_id = cs.subject_id
            LEFT JOIN academic_content ac_course ON ac_course.course_id = c.id
            GROUP BY c.id, c.name, c.slug, c.created_at
            ORDER BY c.name
        """)
        courses = cur.fetchall()

        courses_data = []
        total_notes = 0
        total_pyqs = 0
        total_projects = 0
        for row in courses:
            c_dict = dict(row)
            dept = _get_department(c_dict["name"])
            c_dict["dept_code"] = dept["code"]
            c_dict["dept_name"] = dept["name"]
            c_dict["dept_icon"] = dept["icon"]
            c_dict["dept_badge"] = dept["badge"]
            total_notes += c_dict["notes_count"]
            total_pyqs += c_dict["pyqs_count"]
            total_projects += c_dict["projects_count"]
            courses_data.append(c_dict)

        return render_template(
            "academics/courses.html",
            courses=courses_data,
            total_courses=len(courses_data),
            total_notes=total_notes,
            total_pyqs=total_pyqs,
            total_projects=total_projects,
            user_email=session.get("user_email", ""),
        )
    finally:
        cur.close()
        conn.close()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAGE 2: /academics/<course_slug> (3 Cards: Notes / PYQs / Projects)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@academics_bp.route("/academics/<course_slug>")
@role_required("student", "club_head", "placement_coordinator", "admin")
def course_hub(course_slug):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT * FROM courses WHERE slug = %s", (course_slug,))
        course = cur.fetchone()
        if not course:
            flash("Course not found.", "danger")
            return redirect(url_for("academics.courses_grid"))

        course_id = course["id"]

        # Number of subjects
        cur.execute("SELECT COUNT(*) AS count FROM course_subjects WHERE course_id = %s", (course_id,))
        subject_count = cur.fetchone()["count"]

        # Number of approved notes
        cur.execute("""
            SELECT COUNT(DISTINCT ac.id) AS count
            FROM academic_content ac
            JOIN course_subjects cs ON cs.subject_id = ac.subject_id
            WHERE cs.course_id = %s AND ac.type = 'notes' AND ac.status = 'approved' AND ac.deleted_at IS NULL
        """, (course_id,))
        notes_count = cur.fetchone()["count"]

        # Number of approved pyqs
        cur.execute("""
            SELECT COUNT(DISTINCT ac.id) AS count
            FROM academic_content ac
            JOIN course_subjects cs ON cs.subject_id = ac.subject_id
            WHERE cs.course_id = %s AND ac.type = 'pyq' AND ac.status = 'approved' AND ac.deleted_at IS NULL
        """, (course_id,))
        pyqs_count = cur.fetchone()["count"]

        # Number of approved projects
        cur.execute("""
            SELECT COUNT(*) AS count
            FROM academic_content
            WHERE course_id = %s AND type = 'project' AND status = 'approved' AND deleted_at IS NULL
        """, (course_id,))
        projects_count = cur.fetchone()["count"]

        dept = _get_department(course["name"])

        # Fetch up to 4 recent approved uploads in this course
        cur.execute("""
            SELECT ac.id, ac.type, ac.title, ac.created_at, s.name AS subject_name
            FROM academic_content ac
            LEFT JOIN subjects s ON s.id = ac.subject_id
            LEFT JOIN course_subjects cs ON cs.subject_id = s.id
            WHERE (cs.course_id = %s OR ac.course_id = %s)
              AND ac.status = 'approved'
              AND ac.deleted_at IS NULL
            ORDER BY ac.created_at DESC
            LIMIT 4
        """, (course_id, course_id))
        recent_activity = cur.fetchall()

        return render_template(
            "academics/course_hub.html",
            course=course,
            dept=dept,
            subject_count=subject_count,
            notes_count=notes_count,
            pyqs_count=pyqs_count,
            projects_count=projects_count,
            recent_activity=recent_activity,
            user_email=session.get("user_email", ""),
        )
    finally:
        cur.close()
        conn.close()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAGE 3a: /academics/<course_slug>/notes and /pyqs (Subject List with Search)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@academics_bp.route("/academics/<course_slug>/<any(notes, pyqs, pyq):content_type>")
@role_required("student", "club_head", "placement_coordinator", "admin")
def subject_list(course_slug, content_type):
    # Normalize url content_type ('pyqs' or 'pyq' -> DB 'pyq', 'notes' -> DB 'notes')
    normalized_type = "pyqs" if content_type in ("pyq", "pyqs") else "notes"
    db_type = "pyq" if normalized_type == "pyqs" else "notes"
    user_id = session.get("user_id")

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT * FROM courses WHERE slug = %s", (course_slug,))
        course = cur.fetchone()
        if not course:
            flash("Course not found.", "danger")
            return redirect(url_for("academics.courses_grid"))

        dept = _get_department(course["name"])

        # Fetch all subjects for this course with approved file count
        # and pending files uploaded by current user
        cur.execute("""
            SELECT 
                s.id, 
                s.name,
                COUNT(DISTINCT CASE 
                    WHEN ac.status = 'approved' AND ac.deleted_at IS NULL 
                    THEN ac.id 
                END) AS file_count,
                COUNT(DISTINCT CASE 
                    WHEN ac.uploaded_by = %s AND ac.status = 'pending' AND ac.deleted_at IS NULL 
                    THEN ac.id 
                END) AS my_pending_count
            FROM subjects s
            JOIN course_subjects cs ON cs.subject_id = s.id
            LEFT JOIN academic_content ac ON ac.subject_id = s.id AND ac.type = %s
            WHERE cs.course_id = %s
            GROUP BY s.id, s.name
            ORDER BY s.name
        """, (user_id, db_type, course["id"]))
        subjects = cur.fetchall()

        total_files = sum(s["file_count"] for s in subjects)

        return render_template(
            "academics/subject_list.html",
            course=course,
            dept=dept,
            subjects=subjects,
            content_type=normalized_type,
            db_type=db_type,
            total_files=total_files,
            user_email=session.get("user_email", ""),
        )
    finally:
        cur.close()
        conn.close()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAGE 3b: /academics/<course_slug>/projects (Projects List + Upload)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@academics_bp.route("/academics/<course_slug>/projects")
@role_required("student", "club_head", "placement_coordinator", "admin")
def course_projects(course_slug):
    user_id = session.get("user_id")
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT * FROM courses WHERE slug = %s", (course_slug,))
        course = cur.fetchone()
        if not course:
            flash("Course not found.", "danger")
            return redirect(url_for("academics.courses_grid"))

        dept = _get_department(course["name"])

        # Approved projects + user's own pending projects
        cur.execute("""
            SELECT 
                ac.id,
                ac.title,
                ac.description,
                ac.tags,
                ac.file_url,
                ac.status,
                ac.created_at,
                ac.uploaded_by,
                u.full_name AS uploader_name,
                u.email AS uploader_email
            FROM academic_content ac
            JOIN users u ON u.id = ac.uploaded_by
            WHERE ac.course_id = %s
              AND ac.type = 'project'
              AND (ac.status = 'approved' OR (ac.uploaded_by = %s AND ac.status = 'pending'))
              AND ac.deleted_at IS NULL
            ORDER BY ac.created_at DESC
        """, (course["id"], user_id))
        projects = cur.fetchall()

        # Extract unique tags for tag filter
        all_tags = set()
        for p in projects:
            if p["tags"]:
                for t in p["tags"].split(","):
                    t_clean = t.strip()
                    if t_clean:
                        all_tags.add(t_clean)
        sorted_tags = sorted(list(all_tags), key=lambda x: x.lower())

        return render_template(
            "academics/projects.html",
            course=course,
            dept=dept,
            projects=projects,
            tags=sorted_tags,
            user_id=user_id,
            user_email=session.get("user_email", ""),
        )
    finally:
        cur.close()
        conn.close()


@academics_bp.route("/academics/<course_slug>/projects/upload", methods=["POST"])
@role_required("student", "club_head", "placement_coordinator", "admin")
def upload_project(course_slug):
    file = request.files.get("content_file")
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip() or None
    tags = request.form.get("tags", "").strip() or None

    if not title:
        flash("Please enter a project title.", "danger")
        return redirect(url_for("academics.course_projects", course_slug=course_slug))

    if not file or file.filename == "":
        flash("Please choose a file or archive to upload.", "danger")
        return redirect(url_for("academics.course_projects", course_slug=course_slug))

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        flash(f"Unsupported file format '{ext}'. Allowed: PDF, PPT, PPTX, DOC, DOCX, ZIP, RAR, IPYNB.", "danger")
        return redirect(url_for("academics.course_projects", course_slug=course_slug))

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT id FROM courses WHERE slug = %s", (course_slug,))
        course = cur.fetchone()
        if not course:
            flash("Course not found.", "danger")
            return redirect(url_for("academics.courses_grid"))

        file_url = upload_file_to_cloudinary(file, folder="campusplus/academics/projects")

        cur.execute("""
            INSERT INTO academic_content 
                (subject_id, course_id, uploaded_by, type, title, description, tags, file_url, status)
            VALUES (NULL, %s, %s, 'project', %s, %s, %s, %s, 'pending')
        """, (course["id"], session["user_id"], title, description, tags, file_url))
        conn.commit()

        flash("Project submitted successfully! It is currently pending admin moderation.", "success")
        return redirect(url_for("academics.course_projects", course_slug=course_slug))
    except Exception as e:
        conn.rollback()
        print(f"PROJECT UPLOAD ERROR: {e}")
        flash(f"Upload failed: {str(e)}", "danger")
        return redirect(url_for("academics.course_projects", course_slug=course_slug))
    finally:
        cur.close()
        conn.close()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAGE 4: /academics/<course_slug>/notes/<subject_id> & /pyqs/<subject_id>
# (Files List + Upload Form)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@academics_bp.route("/academics/<course_slug>/<any(notes, pyqs, pyq):content_type>/<int:subject_id>")
@role_required("student", "club_head", "placement_coordinator", "admin")
def subject_files(course_slug, content_type, subject_id):
    normalized_type = "pyqs" if content_type in ("pyq", "pyqs") else "notes"
    db_type = "pyq" if normalized_type == "pyqs" else "notes"
    user_id = session.get("user_id")

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT * FROM courses WHERE slug = %s", (course_slug,))
        course = cur.fetchone()
        if not course:
            flash("Course not found.", "danger")
            return redirect(url_for("academics.courses_grid"))

        cur.execute("""
            SELECT s.* FROM subjects s
            JOIN course_subjects cs ON cs.subject_id = s.id
            WHERE s.id = %s AND cs.course_id = %s
        """, (subject_id, course["id"]))
        subject = cur.fetchone()

        if not subject:
            # Fallback check if subject exists in global pool
            cur.execute("SELECT * FROM subjects WHERE id = %s", (subject_id,))
            subject = cur.fetchone()
            if not subject:
                flash("Subject not found.", "danger")
                return redirect(url_for("academics.subject_list", course_slug=course_slug, content_type=normalized_type))

        dept = _get_department(course["name"])

        # Fetch approved files + user's pending files for this subject & type
        cur.execute("""
            SELECT 
                ac.id,
                ac.title,
                ac.description,
                ac.file_url,
                ac.status,
                ac.created_at,
                ac.uploaded_by,
                u.full_name AS uploader_name,
                u.email AS uploader_email
            FROM academic_content ac
            JOIN users u ON u.id = ac.uploaded_by
            WHERE ac.subject_id = %s
              AND ac.type = %s
              AND (ac.status = 'approved' OR (ac.uploaded_by = %s AND ac.status = 'pending'))
              AND ac.deleted_at IS NULL
            ORDER BY ac.created_at DESC
        """, (subject_id, db_type, user_id))
        files = cur.fetchall()

        # Count of other content type for easy toggle badge
        alt_db_type = "notes" if db_type == "pyq" else "pyq"
        cur.execute("""
            SELECT COUNT(*) AS count
            FROM academic_content
            WHERE subject_id = %s AND type = %s AND status = 'approved' AND deleted_at IS NULL
        """, (subject_id, alt_db_type))
        alt_count = cur.fetchone()["count"]

        return render_template(
            "academics/subject_files.html",
            course=course,
            dept=dept,
            subject=subject,
            files=files,
            content_type=normalized_type,
            db_type=db_type,
            alt_count=alt_count,
            user_id=user_id,
            user_email=session.get("user_email", ""),
        )
    finally:
        cur.close()
        conn.close()


@academics_bp.route("/academics/<course_slug>/<any(notes, pyqs, pyq):content_type>/<int:subject_id>/upload", methods=["POST"])
@role_required("student", "club_head", "placement_coordinator", "admin")
def upload_subject_file(course_slug, content_type, subject_id):
    normalized_type = "pyqs" if content_type in ("pyq", "pyqs") else "notes"
    db_type = "pyq" if normalized_type == "pyqs" else "notes"

    file = request.files.get("content_file")
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip() or None

    if not title:
        flash("Please enter a title for the file.", "danger")
        return redirect(url_for("academics.subject_files", course_slug=course_slug, content_type=normalized_type, subject_id=subject_id))

    if not file or file.filename == "":
        flash("Please select a file to upload.", "danger")
        return redirect(url_for("academics.subject_files", course_slug=course_slug, content_type=normalized_type, subject_id=subject_id))

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        flash(f"Unsupported file format '{ext}'. Allowed: PDF, PPT, PPTX, DOC, DOCX, ZIP, RAR.", "danger")
        return redirect(url_for("academics.subject_files", course_slug=course_slug, content_type=normalized_type, subject_id=subject_id))

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT id FROM courses WHERE slug = %s", (course_slug,))
        course = cur.fetchone()
        if not course:
            flash("Course not found.", "danger")
            return redirect(url_for("academics.courses_grid"))

        cur.execute("SELECT id, name FROM subjects WHERE id = %s", (subject_id,))
        subject = cur.fetchone()
        if not subject:
            flash("Subject not found.", "danger")
            return redirect(url_for("academics.subject_list", course_slug=course_slug, content_type=normalized_type))

        file_url = upload_file_to_cloudinary(file, folder=f"campusplus/academics/{db_type}")

        cur.execute("""
            INSERT INTO academic_content 
                (subject_id, course_id, uploaded_by, type, title, description, tags, file_url, status)
            VALUES (%s, NULL, %s, %s, %s, %s, NULL, %s, 'pending')
        """, (subject["id"], session["user_id"], db_type, title, description, file_url))
        conn.commit()

        display_type_label = "PYQ paper" if db_type == "pyq" else "Notes"
        flash(f"{display_type_label} uploaded successfully! It is pending admin review.", "success")
        return redirect(url_for("academics.subject_files", course_slug=course_slug, content_type=normalized_type, subject_id=subject_id))
    except Exception as e:
        conn.rollback()
        print(f"FILE UPLOAD ERROR: {e}")
        flash(f"Upload failed: {str(e)}", "danger")
        return redirect(url_for("academics.subject_files", course_slug=course_slug, content_type=normalized_type, subject_id=subject_id))
    finally:
        cur.close()
        conn.close()
