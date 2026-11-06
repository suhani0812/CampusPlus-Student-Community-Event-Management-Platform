# 🎓 CampusPlus

**An all-in-one campus portal for MIT-WPU students**: Academics, Clubs, Events, Accommodations and Placements in one place, with sign-up restricted to `@mitwpu.edu.in` emails and verified by OTP.

Built with **Flask (Python)**, **PostgreSQL**, **HTML/CSS** and **Cloudinary** for file storage.

---

## ✨ Features

### Authentication
- Sign-up restricted to `@mitwpu.edu.in` email addresses (enforced server-side)
- 6-digit **email OTP verification** (10-minute expiry, 5 attempt limit, 60-second resend cooldown)
- Single login page for everyone. Admin accounts are detected automatically and redirected to the admin panel
- Show/hide password toggle

### Role-based access control
| Role | Capabilities |
|---|---|
| **Student** | View everything, upload notes/PYQs/projects, list accommodations, leave reviews |
| **Club Head** | Everything a student can do, plus manage their own club's details, gallery and events |
| **Placement Coordinator** | Manage placement drives and JDs |
| **Admin** | Full control: approvals, edits, deletions, role management |

- Every new user is auto-assigned `student` (via a PostgreSQL trigger)
- Users can hold **multiple roles**, and roles are **revocable** (e.g. a club head replaced next year)
- Students request upgrades from the **My Role** page, and the admin approves or denies

### Student portal
- **Dashboard** with live cards: recent uploads, upcoming events, latest placements
- **Clubs**: searchable and filterable by category, with a full club profile (banner, requirements, Instagram, gallery, events, apply link)
- **Events**: upcoming and past tabs, filter by academic/social and on/off campus, event detail with registration link
- **My Role**: view active roles, request upgrades, see request history

### Club head portal
- Edit club description, requirements, Instagram, application link, logo and banner
- Upload and delete gallery photos
- Add and delete events (new events go to admin review)

### Admin panel (sidebar layout)
- **Overview** with pending counts and quick actions
- **Role requests**: approve or deny, with history
- **Content moderation**: approve or deny notes/PYQs/projects, events, accommodations and placement drives
- **Clubs**: add, edit, delete
- **Courses & subjects**: manage courses and a shared subject pool, link and unlink subjects
- **Companies**: manage placement companies with logo upload
- **Admin logs**: full audit trail with filters (action, target, status, date range) and **CSV export**

### Content moderation flow
New uploads are **visible immediately** with status `pending`. The admin later marks them `approved`, or `denied`, which soft-deletes them.

---

## 🧱 Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask (Blueprints) |
| Database | PostgreSQL (`psycopg2`) |
| Frontend | HTML, CSS, vanilla JavaScript, Jinja2 |
| Email | Flask-Mail (Gmail SMTP) |
| File storage | Cloudinary |

---

## 📁 Project Structure

```
campusplus/
├── app.py                  # App init, config, blueprint registration
├── helpers.py              # DB connection, hashing, OTP, email, Cloudinary, audit logger, role_required
├── routes/
│   ├── __init__.py
│   ├── auth.py             # Login, signup, OTP, logout
│   ├── student.py          # Dashboard, academics, clubs, events, role requests
│   ├── club_head.py        # Club head management pages
│   └── admin.py            # Admin panel routes
├── templates/              # Jinja2 templates
├── static/
│   └── css/user_style.css
├── schema.sql              # Database schema (17 tables)
├── seed.sql                # MIT-WPU courses, subjects, clubs and admin user
├── requirements.txt
├── env.example             # Copy to .env and fill in
└── README.md
```

---

## 🗄️ Database Overview

17 tables:

`users` · `pending_users` · `user_roles` · `role_requests` · `courses` · `subjects` · `course_subjects` · `academic_content` · `clubs` · `club_gallery` · `events` · `accommodations` · `accommodation_images` · `accommodation_reviews` · `companies` · `placement_drives` · `admin_logs`

Design notes:
- **Shared subject pool**: subjects are standalone and linked to courses through `course_subjects`, so a subject like *Data Structures & Algorithms* exists once and is shared by CSE, AI&DS, CSF, MCA and others. Uploaded notes are therefore not duplicated.
- **Soft deletes**: `deleted_at` on moderated content preserves history.
- **Audit trail**: `admin_logs` records action, target type, target id, JSON details, success/fail status, IP address and timestamp.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- PostgreSQL 14+
- A Gmail account with an [App Password](https://myaccount.google.com/apppasswords) (2-Step Verification must be on)
- A free [Cloudinary](https://cloudinary.com) account

### 1. Clone and install

```bash
git clone https://github.com/<your-username>/campusplus.git
cd campusplus
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp env.example .env
```

On Windows PowerShell: `Copy-Item env.example .env`

Fill in `.env`:

```env
SECRET_KEY=a-long-random-string

DB_HOST=localhost
DB_PORT=5432
DB_NAME=campusplus
DB_USER=postgres
DB_PASSWORD=your_postgres_password

MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your_gmail@gmail.com
MAIL_PASSWORD=your_16_char_app_password

CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

> ⚠️ No spaces in `MAIL_PASSWORD` and no inline comments on the same line as a value.

### 3. Set up the database

```bash
psql -U postgres -c "CREATE DATABASE campusplus;"
psql -U postgres -d campusplus -f schema.sql
psql -U postgres -d campusplus -f seed.sql
```

> On Windows, if `psql` isn't recognised, add PostgreSQL to PATH for the session:
> `$env:Path += ";C:\Program Files\PostgreSQL\16\bin"`

### 4. Run

```bash
python app.py
```

Open `http://127.0.0.1:5000`.

---

## 🔐 Admin Access

The admin account is **pre-seeded** by `seed.sql` and bypasses OTP signup. Log in through the normal login page and you will be redirected to the admin panel.

> ⚠️ **Change the seeded admin email and password before deploying.** Generate a new SHA-256 hash for the password and update it in `seed.sql`, or update the row directly in the database.

---

## 🗺️ Roadmap

- [x] OTP-verified, domain-restricted authentication
- [x] Role system with upgrade requests
- [x] Admin panel (role requests, moderation, clubs, courses, companies, logs + CSV export)
- [x] Clubs portal and club head management
- [x] Events portal
- [ ] Academics portal (course → notes/PYQs/projects → subject → files, with upload)
- [ ] Accommodations (listings, image gallery, reviews and ratings)
- [ ] Placements (companies, drives, JDs) and placement coordinator pages
- [ ] Admin Users page (view users, revoke roles)
- [ ] Add `@role_required` consistently across all routes

### Known limitations / planned hardening
- Passwords are hashed with SHA-256. **Migrate to bcrypt or argon2** before production.
- Add CSRF protection (e.g. Flask-WTF).
- Add rate limiting on login and OTP endpoints.
- Replace `datetime.utcnow()` with timezone-aware datetimes.

---

Built by a cybersecurity student at MIT-WPU, Pune.
