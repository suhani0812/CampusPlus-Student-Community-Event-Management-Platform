from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import psycopg2.extras
import os
from helpers import get_db, upload_file_to_cloudinary, role_required

student_bp = Blueprint("student", __name__)


# ── Dashboard ───────────────────────────────────
@student_bp.route("/dashboard")
@role_required("student", "club_head", "placement_coordinator", "admin")
def dashboard():

    user_id = session["user_id"]
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("""
            SELECT role FROM user_roles
            WHERE user_id = %s AND revoked_at IS NULL
            ORDER BY CASE role
                WHEN 'admin'                  THEN 1
                WHEN 'placement_coordinator'  THEN 2
                WHEN 'club_head'              THEN 3
                ELSE 4
            END LIMIT 1
        """, (user_id,))
        role_row     = cur.fetchone()
        primary_role = role_row["role"] if role_row else "student"

        cur.execute("""
            SELECT ac.title, ac.type, s.name AS subject_name
            FROM academic_content ac
            JOIN subjects s ON s.id = ac.subject_id
            WHERE ac.deleted_at IS NULL AND ac.status != 'denied'
            ORDER BY ac.created_at DESC LIMIT 3
        """)
        recent_uploads = cur.fetchall()

        cur.execute("""
            SELECT e.title, e.type, e.event_date, c.name AS club_name
            FROM events e
            JOIN clubs c ON c.id = e.club_id
            WHERE e.deleted_at IS NULL
              AND e.status != 'denied'
              AND (e.event_date IS NULL OR e.event_date >= NOW())
            ORDER BY e.event_date ASC NULLS LAST LIMIT 3
        """)
        upcoming_events = cur.fetchall()

        cur.execute("""
            SELECT pd.role_title, pd.package_lpa, co.name AS company_name
            FROM placement_drives pd
            JOIN companies co ON co.id = pd.company_id
            WHERE pd.deleted_at IS NULL AND pd.status != 'denied'
            ORDER BY pd.created_at DESC LIMIT 3
        """)
        latest_placements = cur.fetchall()

    finally:
        cur.close()
        conn.close()

    return render_template("dashboard.html",
        email             = session["user_email"],
        primary_role      = primary_role,
        recent_uploads    = recent_uploads,
        upcoming_events   = upcoming_events,
        latest_placements = latest_placements,
    )


# ── My Role page ────────────────────────────────
@student_bp.route("/role-request", methods=["GET", "POST"])
@role_required("student", "club_head", "placement_coordinator", "admin")
def role_request():

    user_id = session["user_id"]
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        if request.method == "POST":
            requested_role = request.form.get("requested_role")
            club_id        = request.form.get("club_id") or None
            reason         = request.form.get("reason", "").strip() or None

            if requested_role not in ("club_head", "placement_coordinator"):
                flash("Invalid role requested.", "danger")
                return redirect(url_for("student.role_request"))

            if requested_role == "club_head" and not club_id:
                flash("Please select a club.", "danger")
                return redirect(url_for("student.role_request"))

            cur.execute("""
                SELECT id FROM role_requests
                WHERE user_id = %s AND status = 'pending'
            """, (user_id,))
            if cur.fetchone():
                flash("You already have a pending request.", "danger")
                return redirect(url_for("student.role_request"))

            cur.execute("""
                INSERT INTO role_requests (user_id, requested_role, club_id, reason)
                VALUES (%s, %s, %s, %s)
            """, (user_id, requested_role, club_id, reason))
            conn.commit()
            flash("Request submitted! Admin will review it soon.", "success")
            return redirect(url_for("student.role_request"))

        # GET
        cur.execute("""
            SELECT ur.role, c.name AS club_name
            FROM user_roles ur
            LEFT JOIN clubs c ON c.id = ur.club_id
            WHERE ur.user_id = %s AND ur.revoked_at IS NULL
        """, (user_id,))
        active_roles = cur.fetchall()
        active_role_names = [r["role"] for r in active_roles]

        cur.execute("SELECT id FROM role_requests WHERE user_id = %s AND status = 'pending'", (user_id,))
        has_pending = cur.fetchone() is not None

        cur.execute("""
            SELECT rr.requested_role, rr.reason, rr.status,
                   rr.requested_at, rr.reviewed_at, c.name AS club_name
            FROM role_requests rr
            LEFT JOIN clubs c ON c.id = rr.club_id
            WHERE rr.user_id = %s
            ORDER BY rr.requested_at DESC
        """, (user_id,))
        requests = cur.fetchall()

        cur.execute("SELECT id, name FROM clubs ORDER BY name")
        clubs = cur.fetchall()

        return render_template("role_request.html",
            active_roles      = active_roles,
            active_role_names = active_role_names,
            has_pending       = has_pending,
            requests          = requests,
            clubs             = clubs,
        )
    except Exception as e:
        conn.rollback()
        print(f"ROLE REQUEST ERROR: {e}")
        flash("Something went wrong. Please try again.", "danger")
        return redirect(url_for("student.dashboard"))
    finally:
        cur.close()
        conn.close()


# ── Upload academic content ────────────────────
@student_bp.route("/upload-content", methods=["POST"])
@role_required("student", "club_head", "placement_coordinator", "admin")
def upload_content():

    file       = request.files.get("content_file")
    title      = request.form.get("title")
    subject_id = request.form.get("subject_id")
    course_id  = request.form.get("course_id")
    type_      = request.form.get("type")   # notes | pyq | project
    tags       = request.form.get("tags", "").strip() or None

    if not file or file.filename == "":
        flash("Please select a file.", "danger")
        return redirect(url_for("student.dashboard"))

    allowed = {".pdf", ".ppt", ".pptx", ".doc", ".docx"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        flash("Only PDF, PPT, PPTX, DOC, DOCX files allowed.", "danger")
        return redirect(url_for("student.dashboard"))

    try:
        file_url = upload_file_to_cloudinary(file, folder="campusplus/academics")

        conn = get_db()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO academic_content
                (subject_id, course_id, uploaded_by, type, title, tags, file_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (subject_id or None, course_id or None, session["user_id"], type_, title, tags, file_url))
        conn.commit()
        cur.close()
        conn.close()

        flash("Uploaded successfully! Pending admin review.", "success")
        return redirect(url_for("student.dashboard"))

    except Exception as e:
        print(f"UPLOAD ERROR: {e}")
        flash("Upload failed. Please try again.", "danger")
        return redirect(url_for("student.dashboard"))

# ── Clubs list ──────────────────────────────────
@student_bp.route("/clubs")
@role_required("student", "club_head", "placement_coordinator", "admin")
def clubs():
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT * FROM clubs ORDER BY name")
        clubs = cur.fetchall()

        banner_colors = [
            "linear-gradient(135deg,#667eea,#764ba2)",
            "linear-gradient(135deg,#f093fb,#f5576c)",
            "linear-gradient(135deg,#4facfe,#00f2fe)",
            "linear-gradient(135deg,#43e97b,#38f9d7)",
            "linear-gradient(135deg,#fa709a,#fee140)",
            "linear-gradient(135deg,#a18cd1,#fbc2eb)",
        ]

        return render_template("clubs.html", 
            clubs=clubs, 
            banner_colors=banner_colors,
            user_email=session.get("user_email", "")
        )
    finally:
        cur.close()
        conn.close()


# ── Club detail ─────────────────────────────────
@student_bp.route("/clubs/<int:club_id>")
@role_required("student", "club_head", "placement_coordinator", "admin")
def club_detail(club_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    user_id = session["user_id"]
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT * FROM clubs WHERE id = %s", (club_id,))
        club = cur.fetchone()
        if not club:
            flash("Club not found.", "danger")
            return redirect(url_for("student.clubs"))

        cur.execute("""
            SELECT * FROM club_gallery WHERE club_id = %s
        """, (club_id,))
        gallery = cur.fetchall()

        cur.execute("""
            SELECT * FROM events
            WHERE club_id = %s AND deleted_at IS NULL AND status = 'approved'
            ORDER BY event_date DESC
        """, (club_id,))
        events = cur.fetchall()

        # Check if logged-in user is club head of this club
        cur.execute("""
            SELECT id FROM user_roles
            WHERE user_id = %s AND role = 'club_head'
              AND club_id = %s AND revoked_at IS NULL
        """, (user_id, club_id))
        is_club_head = cur.fetchone() is not None

        banner_colors = [
            "linear-gradient(135deg,#667eea,#764ba2)",
            "linear-gradient(135deg,#f093fb,#f5576c)",
            "linear-gradient(135deg,#4facfe,#00f2fe)",
            "linear-gradient(135deg,#43e97b,#38f9d7)",
            "linear-gradient(135deg,#fa709a,#fee140)",
            "linear-gradient(135deg,#a18cd1,#fbc2eb)",
        ]

        return render_template("club_detail.html",
            club         = club,
            gallery      = gallery,
            events       = events,
            is_club_head = is_club_head,
            banner_color = banner_colors[club_id % len(banner_colors)],
            user_email   = session.get("user_email", "")
        )
    finally:
        cur.close()
        conn.close()


# ── Events list ─────────────────────────────────
@student_bp.route("/events")
@role_required("student", "club_head", "placement_coordinator", "admin")
def events():
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    user_id = session["user_id"]
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        # Check if user is head of any club
        cur.execute("""
            SELECT club_id FROM user_roles
            WHERE user_id = %s AND role = 'club_head' AND revoked_at IS NULL
            LIMIT 1
        """, (user_id,))
        club_head_row = cur.fetchone()
        user_club_id = club_head_row["club_id"] if club_head_row else None

        # Fetch all approved events
        cur.execute("""
            SELECT e.*, c.name AS club_name, c.logo_url AS club_logo_url, c.category AS club_category
            FROM events e
            JOIN clubs c ON c.id = e.club_id
            WHERE e.deleted_at IS NULL AND e.status = 'approved'
            ORDER BY e.event_date ASC NULLS LAST
        """)
        all_events = [dict(r) for r in cur.fetchall()]

        # Compute stats
        academic_count = sum(1 for e in all_events if e["type"] == "academic")
        social_count = sum(1 for e in all_events if e["type"] == "social")
        on_campus_count = sum(1 for e in all_events if e["location_type"] == "on_campus")
        off_campus_count = sum(1 for e in all_events if e["location_type"] == "off_campus")

        return render_template(
            "events.html",
            events=all_events,
            total_events=len(all_events),
            academic_count=academic_count,
            social_count=social_count,
            on_campus_count=on_campus_count,
            off_campus_count=off_campus_count,
            user_club_id=user_club_id,
            user_email=session.get("user_email", ""),
        )
    finally:
        cur.close()
        conn.close()


# ── Event detail ────────────────────────────────
@student_bp.route("/events/<int:event_id>")
@role_required("student", "club_head", "placement_coordinator", "admin")
def event_detail(event_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("""
            SELECT e.*, c.name AS club_name, c.logo_url AS club_logo_url, c.category AS club_category,
                   c.instagram_handle, c.description AS club_description
            FROM events e
            JOIN clubs c ON c.id = e.club_id
            WHERE e.id = %s AND e.deleted_at IS NULL AND e.status = 'approved'
        """, (event_id,))
        event = cur.fetchone()
        if not event:
            flash("Event not found or pending approval.", "danger")
            return redirect(url_for("student.events"))

        # Fetch other upcoming events by the same club
        cur.execute("""
            SELECT id, title, event_date, type, venue
            FROM events
            WHERE club_id = %s AND id != %s AND deleted_at IS NULL AND status = 'approved'
            ORDER BY event_date ASC LIMIT 3
        """, (event["club_id"], event_id))
        more_events = cur.fetchall()

        return render_template(
            "event_detail.html",
            event=event,
            more_events=more_events,
            user_email=session.get("user_email", ""),
        )
    finally:
        cur.close()
        conn.close()


# ── Accommodations list ─────────────────────────
@student_bp.route("/accommodations")
@role_required("student", "club_head", "placement_coordinator", "admin")
def accommodations():
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    user_id = session["user_id"]
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("""
            SELECT 
                a.*,
                u.full_name AS lister_name,
                u.email AS lister_email,
                COALESCE(ROUND(AVG(r.rating)::numeric, 1), 0) AS avg_rating,
                COUNT(r.id) AS review_count,
                (SELECT image_url FROM accommodation_images WHERE accommodation_id = a.id ORDER BY id ASC LIMIT 1) AS cover_image
            FROM accommodations a
            JOIN users u ON u.id = a.listed_by
            LEFT JOIN accommodation_reviews r ON r.accommodation_id = a.id
            WHERE (a.status = 'approved' OR (a.listed_by = %s AND a.status = 'pending'))
              AND a.deleted_at IS NULL
            GROUP BY a.id, u.full_name, u.email
            ORDER BY a.created_at DESC
        """, (user_id,))
        all_accomm = [dict(r) for r in cur.fetchall()]

        total_listings = len(all_accomm)
        pg_count = sum(1 for a in all_accomm if a["type"] == "pg")
        hostel_count = sum(1 for a in all_accomm if a["type"] == "hostel")
        flat_count = sum(1 for a in all_accomm if a["type"] == "flat")
        rents = [float(a["rent"]) for a in all_accomm if a["rent"]]
        min_rent = int(min(rents)) if rents else 0
        avg_rent = int(sum(rents) / len(rents)) if rents else 0

        return render_template(
            "accommodations.html",
            accommodations=all_accomm,
            total_listings=total_listings,
            pg_count=pg_count,
            hostel_count=hostel_count,
            flat_count=flat_count,
            min_rent=min_rent,
            avg_rent=avg_rent,
            user_id=user_id,
            user_email=session.get("user_email", ""),
        )
    finally:
        cur.close()
        conn.close()


# ── Add accommodation listing ───────────────────
@student_bp.route("/accommodations/add", methods=["POST"])
@role_required("student", "club_head", "placement_coordinator", "admin")
def add_accommodation():
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    user_id        = session["user_id"]
    title          = request.form.get("title", "").strip()
    type_          = request.form.get("type")
    rent_raw       = request.form.get("rent", "").strip()
    address        = request.form.get("address", "").strip()
    location_url   = request.form.get("location_url", "").strip() or None
    broker_name    = request.form.get("broker_name", "").strip() or None
    broker_contact = request.form.get("broker_contact", "").strip() or None

    if not title or not address or not rent_raw:
        flash("Title, address, and rent are required fields.", "danger")
        return redirect(url_for("student.accommodations"))

    if type_ not in ("hostel", "pg", "flat"):
        flash("Invalid accommodation type.", "danger")
        return redirect(url_for("student.accommodations"))

    try:
        rent = float(rent_raw)
    except ValueError:
        flash("Rent must be a valid number.", "danger")
        return redirect(url_for("student.accommodations"))

    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO accommodations 
                (listed_by, type, title, address, location_url, rent, broker_name, broker_contact, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending')
            RETURNING id
        """, (user_id, type_, title, address, location_url, rent, broker_name, broker_contact))
        acc_id = cur.fetchone()[0]

        # Handle multiple images
        images = request.files.getlist("images")
        for img in images:
            if img and img.filename:
                try:
                    img_url = upload_file_to_cloudinary(img, folder="campusplus/accommodations")
                    cur.execute("""
                        INSERT INTO accommodation_images (accommodation_id, image_url)
                        VALUES (%s, %s)
                    """, (acc_id, img_url))
                except Exception as e:
                    print(f"IMAGE UPLOAD ERROR: {e}")

        conn.commit()
        flash("Property listed successfully! It is pending admin verification.", "success")
    except Exception as e:
        conn.rollback()
        print(f"ADD ACCOMMODATION ERROR: {e}")
        flash("Failed to list property. Please try again.", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("student.accommodations"))


# ── Accommodation detail ────────────────────────
@student_bp.route("/accommodations/<int:acc_id>")
@role_required("student", "club_head", "placement_coordinator", "admin")
def accommodation_detail(acc_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    user_id = session["user_id"]
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("""
            SELECT 
                a.*,
                u.full_name AS lister_name,
                u.email AS lister_email,
                COALESCE(ROUND(AVG(r.rating)::numeric, 1), 0) AS avg_rating,
                COUNT(r.id) AS review_count
            FROM accommodations a
            JOIN users u ON u.id = a.listed_by
            LEFT JOIN accommodation_reviews r ON r.accommodation_id = a.id
            WHERE a.id = %s 
              AND (a.status = 'approved' OR (a.listed_by = %s AND a.status = 'pending'))
              AND a.deleted_at IS NULL
            GROUP BY a.id, u.full_name, u.email
        """, (acc_id, user_id))
        acc = cur.fetchone()
        if not acc:
            flash("Accommodation not found or pending verification.", "danger")
            return redirect(url_for("student.accommodations"))

        # Fetch images
        cur.execute("""
            SELECT id, image_url FROM accommodation_images
            WHERE accommodation_id = %s
            ORDER BY id ASC
        """, (acc_id,))
        images = cur.fetchall()

        # Fetch reviews
        cur.execute("""
            SELECT r.*, u.full_name, u.email
            FROM accommodation_reviews r
            JOIN users u ON u.id = r.reviewed_by
            WHERE r.accommodation_id = %s
            ORDER BY r.created_at DESC
        """, (acc_id,))
        reviews = cur.fetchall()

        # Check if current user has already reviewed
        cur.execute("""
            SELECT id FROM accommodation_reviews
            WHERE accommodation_id = %s AND reviewed_by = %s
        """, (acc_id, user_id))
        user_has_reviewed = cur.fetchone() is not None

        return render_template(
            "accommodation_detail.html",
            acc=acc,
            images=images,
            reviews=reviews,
            user_has_reviewed=user_has_reviewed,
            user_email=session.get("user_email", ""),
        )
    finally:
        cur.close()
        conn.close()


# ── Add review to accommodation ─────────────────
@student_bp.route("/accommodations/<int:acc_id>/reviews", methods=["POST"])
@role_required("student", "club_head", "placement_coordinator", "admin")
def add_accommodation_review(acc_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    user_id = session["user_id"]
    rating_raw = request.form.get("rating", "5")
    comment = request.form.get("comment", "").strip() or None

    try:
        rating = int(rating_raw)
        if rating < 1 or rating > 5:
            rating = 5
    except ValueError:
        rating = 5

    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO accommodation_reviews (accommodation_id, reviewed_by, rating, comment)
            VALUES (%s, %s, %s, %s)
        """, (acc_id, user_id, rating, comment))
        conn.commit()
        flash("Thank you! Your review has been published.", "success")
    except Exception as e:
        conn.rollback()
        print(f"REVIEW ERROR: {e}")
        flash("Could not submit review.", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("student.accommodation_detail", acc_id=acc_id))


# ── Placements list ─────────────────────────────
@student_bp.route("/placements")
@role_required("student", "club_head", "placement_coordinator", "admin")
def placements():
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    user_id = session["user_id"]
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        # Check if user has placement_coordinator role
        cur.execute("""
            SELECT id FROM user_roles
            WHERE user_id = %s AND role IN ('placement_coordinator', 'admin') AND revoked_at IS NULL
        """, (user_id,))
        is_coordinator = cur.fetchone() is not None or session.get("is_admin", False)

        # Fetch all approved drives + user's pending drives
        cur.execute("""
            SELECT pd.*, co.name AS company_name, co.logo_url AS company_logo_url, co.website AS company_website,
                   u.full_name AS added_by_name, u.email AS added_by_email
            FROM placement_drives pd
            JOIN companies co ON co.id = pd.company_id
            JOIN users u ON u.id = pd.added_by
            WHERE (pd.status = 'approved' OR (pd.added_by = %s AND pd.status = 'pending'))
              AND pd.deleted_at IS NULL
            ORDER BY pd.drive_date ASC NULLS LAST
        """, (user_id,))
        all_drives = [dict(r) for r in cur.fetchall()]

        # Fetch companies for add drive modal dropdown
        cur.execute("SELECT id, name FROM companies ORDER BY name ASC")
        companies = [dict(r) for r in cur.fetchall()]

        # Compute stats
        total_drives = len(all_drives)
        packages = [float(d["package_lpa"]) for d in all_drives if d["package_lpa"]]
        max_package = max(packages) if packages else 0.0
        avg_package = round(sum(packages) / len(packages), 1) if packages else 0.0
        dream_count = sum(1 for d in all_drives if d["package_lpa"] and float(d["package_lpa"]) >= 15.0)
        company_count = len(companies)

        return render_template(
            "placements.html",
            drives=all_drives,
            companies=companies,
            total_drives=total_drives,
            max_package=max_package,
            avg_package=avg_package,
            dream_count=dream_count,
            company_count=company_count,
            is_coordinator=is_coordinator,
            user_id=user_id,
            user_email=session.get("user_email", ""),
        )
    finally:
        cur.close()
        conn.close()


# ── Add placement drive ─────────────────────────
@student_bp.route("/placements/add", methods=["POST"])
@role_required("student", "club_head", "placement_coordinator", "admin")
def add_placement_drive():
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    user_id           = session["user_id"]
    company_id_raw    = request.form.get("company_id", "").strip()
    new_company_name  = request.form.get("new_company_name", "").strip()
    role_title        = request.form.get("role_title", "").strip()
    package_lpa_raw   = request.form.get("package_lpa", "").strip()
    drive_date        = request.form.get("drive_date") or None
    eligibility       = request.form.get("eligibility", "").strip() or None
    jd_description    = request.form.get("jd_description", "").strip() or None
    apply_link        = request.form.get("apply_link", "").strip() or None
    jd_file_url       = None

    if not role_title:
        flash("Job role title is required.", "danger")
        return redirect(url_for("student.placements"))

    try:
        package_lpa = float(package_lpa_raw) if package_lpa_raw else None
    except ValueError:
        package_lpa = None

    # Handle JD file attachment
    jd_file = request.files.get("jd_file")
    if jd_file and jd_file.filename:
        try:
            jd_file_url = upload_file_to_cloudinary(jd_file, folder="campusplus/placements")
        except Exception as e:
            print(f"JD UPLOAD ERROR: {e}")

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        # Determine company_id
        company_id = None
        if company_id_raw and company_id_raw.isdigit():
            company_id = int(company_id_raw)
        elif new_company_name:
            cur.execute("SELECT id FROM companies WHERE LOWER(name) = LOWER(%s)", (new_company_name,))
            existing = cur.fetchone()
            if existing:
                company_id = existing["id"]
            else:
                cur.execute("INSERT INTO companies (name) VALUES (%s) RETURNING id", (new_company_name,))
                company_id = cur.fetchone()["id"]

        if not company_id:
            flash("Please select or enter a recruiting company.", "danger")
            return redirect(url_for("student.placements"))

        # Check if user is coordinator or admin (auto-approve if coordinator/admin)
        cur.execute("""
            SELECT id FROM user_roles
            WHERE user_id = %s AND role IN ('placement_coordinator', 'admin') AND revoked_at IS NULL
        """, (user_id,))
        is_trusted = cur.fetchone() is not None or session.get("is_admin", False)
        status = "approved" if is_trusted else "pending"

        cur.execute("""
            INSERT INTO placement_drives
                (company_id, added_by, role_title, jd_description, jd_file_url, eligibility, package_lpa, drive_date, apply_link, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (company_id, user_id, role_title, jd_description, jd_file_url, eligibility, package_lpa, drive_date, apply_link, status))
        conn.commit()

        if status == "approved":
            flash("Placement drive published successfully!", "success")
        else:
            flash("Placement drive submitted for review. Pending coordinator approval.", "success")
    except Exception as e:
        conn.rollback()
        print(f"ADD PLACEMENT ERROR: {e}")
        flash("Failed to post placement drive.", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("student.placements"))


# ── Placement drive detail ──────────────────────
@student_bp.route("/placements/<int:drive_id>")
@role_required("student", "club_head", "placement_coordinator", "admin")
def placement_detail(drive_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    user_id = session["user_id"]
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("""
            SELECT pd.*, co.name AS company_name, co.logo_url AS company_logo_url, co.website AS company_website,
                   u.full_name AS added_by_name, u.email AS added_by_email
            FROM placement_drives pd
            JOIN companies co ON co.id = pd.company_id
            JOIN users u ON u.id = pd.added_by
            WHERE pd.id = %s 
              AND (pd.status = 'approved' OR (pd.added_by = %s AND pd.status = 'pending'))
              AND pd.deleted_at IS NULL
        """, (drive_id, user_id))
        drive = cur.fetchone()
        if not drive:
            flash("Placement drive not found or pending verification.", "danger")
            return redirect(url_for("student.placements"))

        # Fetch other upcoming drives
        cur.execute("""
            SELECT pd.id, pd.role_title, pd.package_lpa, pd.drive_date, co.name AS company_name, co.logo_url AS company_logo_url
            FROM placement_drives pd
            JOIN companies co ON co.id = pd.company_id
            WHERE pd.id != %s AND pd.deleted_at IS NULL AND pd.status = 'approved'
            ORDER BY pd.drive_date ASC LIMIT 3
        """, (drive_id,))
        other_drives = cur.fetchall()

        return render_template(
            "placement_detail.html",
            drive=drive,
            other_drives=other_drives,
            user_email=session.get("user_email", ""),
        )
    finally:
        cur.close()
        conn.close()