-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- CampusPlus — Final Database Schema
-- MIT-WPU Campus Network
-- Run once: psql -U postgres -d campusplus -f schema.sql
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- USERS & AUTH
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(64)  NOT NULL,
    is_verified   BOOLEAN      NOT NULL DEFAULT FALSE,
    full_name     VARCHAR(255) NOT NULL,
    last_login    TIMESTAMP,
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- Pending registrations awaiting OTP verification
CREATE TABLE IF NOT EXISTS pending_users (
    id             SERIAL PRIMARY KEY,
    email          VARCHAR(255) UNIQUE NOT NULL,
    full_name      VARCHAR(255) NOT NULL,
    password_hash  VARCHAR(64)  NOT NULL,
    otp            VARCHAR(6)   NOT NULL,
    otp_expires_at TIMESTAMP    NOT NULL,
    attempts       SMALLINT     NOT NULL DEFAULT 0,
    created_at     TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- Keep existing databases in sync when this schema is re-run.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS full_name VARCHAR(255);

ALTER TABLE pending_users
    ADD COLUMN IF NOT EXISTS full_name VARCHAR(255);

ALTER TABLE users
    ALTER COLUMN full_name SET NOT NULL;

ALTER TABLE pending_users
    ALTER COLUMN full_name SET NOT NULL;


-- ROLES
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CREATE TYPE user_role AS ENUM (
    'student',
    'club_head',
    'placement_coordinator',
    'admin'
);

-- Active and historical role assignments per user
CREATE TABLE IF NOT EXISTS user_roles (
    id          SERIAL PRIMARY KEY,
    user_id     INT       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role        user_role NOT NULL,
    club_id     INT,                        -- FK added after clubs table
    assigned_by INT       REFERENCES users(id),
    assigned_at TIMESTAMP NOT NULL DEFAULT NOW(),
    revoked_at  TIMESTAMP                   -- NULL = currently active
);

-- Role upgrade requests submitted by students
CREATE TABLE IF NOT EXISTS role_requests (
    id             SERIAL PRIMARY KEY,
    user_id        INT       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    requested_role user_role NOT NULL,
    club_id        INT,                     -- FK added after clubs table
    reason         TEXT,
    status         VARCHAR(10) NOT NULL DEFAULT 'pending'
                               CHECK (status IN ('pending','approved','denied')),
    requested_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    reviewed_by    INT       REFERENCES users(id),
    reviewed_at    TIMESTAMP
);


-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- ACADEMICS
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CREATE TABLE IF NOT EXISTS courses (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(255) UNIQUE NOT NULL,
    slug       VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Subjects are standalone and shared across courses
CREATE TABLE IF NOT EXISTS subjects (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Junction: which subjects belong to which course
CREATE TABLE IF NOT EXISTS course_subjects (
    course_id  INT NOT NULL REFERENCES courses(id)  ON DELETE CASCADE,
    subject_id INT NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    PRIMARY KEY (course_id, subject_id)
);

-- Notes & PYQs link to a subject; Projects link to a course only
CREATE TABLE IF NOT EXISTS academic_content (
    id          SERIAL PRIMARY KEY,
    subject_id  INT         REFERENCES subjects(id) ON DELETE CASCADE,  -- NULL for projects
    course_id   INT         REFERENCES courses(id)  ON DELETE CASCADE,  -- filled for projects
    uploaded_by INT         NOT NULL REFERENCES users(id),
    type        VARCHAR(10) NOT NULL CHECK (type IN ('notes','pyq','project')),
    title       VARCHAR(255) NOT NULL,
    description TEXT,
    tags        VARCHAR(500),               -- comma-separated keywords for project search
    file_url    VARCHAR(500) NOT NULL,
    status      VARCHAR(10) NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending','approved','denied')),
    created_at  TIMESTAMP   NOT NULL DEFAULT NOW(),
    deleted_at  TIMESTAMP                   -- soft-delete on denial
);


-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- CLUBS
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CREATE TABLE IF NOT EXISTS clubs (
    id               SERIAL PRIMARY KEY,
    name             VARCHAR(255) UNIQUE NOT NULL,
    category         VARCHAR(20)  NOT NULL DEFAULT 'other'
                                  CHECK (category IN ('technical','cultural','social','sports','innovation','other')),
    description      TEXT,
    logo_url         VARCHAR(500),
    banner_url       VARCHAR(500),
    instagram_handle VARCHAR(100),
    requirements     TEXT,
    apply_link       VARCHAR(500),
    created_at       TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Photo gallery managed by club head
CREATE TABLE IF NOT EXISTS club_gallery (
    id        SERIAL PRIMARY KEY,
    club_id   INT          NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
    image_url VARCHAR(500) NOT NULL,
    caption   VARCHAR(255)
);

-- FK for user_roles.club_id and role_requests.club_id (deferred until clubs exists)
ALTER TABLE user_roles
    ADD CONSTRAINT fk_user_roles_club
    FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE SET NULL;

ALTER TABLE role_requests
    ADD CONSTRAINT fk_role_requests_club
    FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE SET NULL;


-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- EVENTS
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CREATE TABLE IF NOT EXISTS events (
    id                SERIAL PRIMARY KEY,
    club_id           INT          NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
    created_by        INT          NOT NULL REFERENCES users(id),
    title             VARCHAR(255) NOT NULL,
    description       TEXT,
    poster_url        VARCHAR(500),
    type              VARCHAR(10)  NOT NULL CHECK (type IN ('academic','social')),
    location_type     VARCHAR(12)  NOT NULL CHECK (location_type IN ('on_campus','off_campus')),
    venue             VARCHAR(255),
    event_date        TIMESTAMP,
    end_date          TIMESTAMP,             -- for multi-day events (fests, hackathons)
    registration_link VARCHAR(500),
    status            VARCHAR(10)  NOT NULL DEFAULT 'pending'
                                   CHECK (status IN ('pending','approved','denied')),
    created_at        TIMESTAMP    NOT NULL DEFAULT NOW(),
    deleted_at        TIMESTAMP
);


-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- ACCOMMODATIONS
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CREATE TABLE IF NOT EXISTS accommodations (
    id             SERIAL PRIMARY KEY,
    listed_by      INT          NOT NULL REFERENCES users(id),
    type           VARCHAR(10)  NOT NULL CHECK (type IN ('hostel','pg','flat')),
    title          VARCHAR(255) NOT NULL,
    address        TEXT         NOT NULL,
    location_url   VARCHAR(500),            -- Google Maps link
    rent           NUMERIC(10,2),
    broker_name    VARCHAR(255),
    broker_contact VARCHAR(20),
    status         VARCHAR(10)  NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending','approved','denied')),
    created_at     TIMESTAMP    NOT NULL DEFAULT NOW(),
    deleted_at     TIMESTAMP
);

CREATE TABLE IF NOT EXISTS accommodation_images (
    id               SERIAL PRIMARY KEY,
    accommodation_id INT NOT NULL REFERENCES accommodations(id) ON DELETE CASCADE,
    image_url        VARCHAR(500) NOT NULL
);

CREATE TABLE IF NOT EXISTS accommodation_reviews (
    id               SERIAL PRIMARY KEY,
    accommodation_id INT      NOT NULL REFERENCES accommodations(id) ON DELETE CASCADE,
    reviewed_by      INT      NOT NULL REFERENCES users(id),
    rating           SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment          TEXT,
    created_at       TIMESTAMP NOT NULL DEFAULT NOW()
);


-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- PLACEMENTS
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CREATE TABLE IF NOT EXISTS companies (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(255) UNIQUE NOT NULL,
    logo_url   VARCHAR(500),
    website    VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS placement_drives (
    id             SERIAL PRIMARY KEY,
    company_id     INT          NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    added_by       INT          NOT NULL REFERENCES users(id),
    role_title     VARCHAR(255) NOT NULL,
    jd_description TEXT,
    jd_file_url    VARCHAR(500),
    eligibility    TEXT,
    package_lpa    NUMERIC(5,2),
    drive_date     TIMESTAMP,
    apply_link     VARCHAR(500),
    status         VARCHAR(10)  NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending','approved','denied')),
    created_at     TIMESTAMP    NOT NULL DEFAULT NOW(),
    deleted_at     TIMESTAMP
);


-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- ADMIN LOGS
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CREATE TABLE IF NOT EXISTS admin_logs (
    id          SERIAL PRIMARY KEY,
    admin_id    INT         NOT NULL REFERENCES users(id),
    action      VARCHAR(20) NOT NULL
                CHECK (action IN (
                    'login','approve','deny','delete',
                    'add','edit','revoke','export'
                )),
    target_type VARCHAR(20) NOT NULL
                CHECK (target_type IN (
                    'note','pyq','project',
                    'club','event','accommodation',
                    'placement','user','role_request',
                    'course','subject','company'
                )),
    target_id   INT,                        -- id of the affected record
    details     JSONB,                      -- extra context (user_email, name, reason etc.)
    status      VARCHAR(10) NOT NULL DEFAULT 'success'
                CHECK (status IN ('success','fail')),
    ip_address  VARCHAR(45),                -- supports IPv4 and IPv6
    created_at  TIMESTAMP   NOT NULL DEFAULT NOW()
);


-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- INDEXES
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CREATE INDEX IF NOT EXISTS idx_users_email              ON users(email);
CREATE INDEX IF NOT EXISTS idx_pending_users_email      ON pending_users(email);
CREATE INDEX IF NOT EXISTS idx_user_roles_user          ON user_roles(user_id) WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_role_requests_status     ON role_requests(status);
CREATE INDEX IF NOT EXISTS idx_course_subjects_course   ON course_subjects(course_id);
CREATE INDEX IF NOT EXISTS idx_course_subjects_subject  ON course_subjects(subject_id);
CREATE INDEX IF NOT EXISTS idx_academic_content_subject ON academic_content(subject_id);
CREATE INDEX IF NOT EXISTS idx_academic_content_course  ON academic_content(course_id);
CREATE INDEX IF NOT EXISTS idx_academic_content_status  ON academic_content(status);
CREATE INDEX IF NOT EXISTS idx_academic_content_type    ON academic_content(type);
CREATE INDEX IF NOT EXISTS idx_club_gallery             ON club_gallery(club_id);
CREATE INDEX IF NOT EXISTS idx_events_club              ON events(club_id);
CREATE INDEX IF NOT EXISTS idx_events_status            ON events(status);
CREATE INDEX IF NOT EXISTS idx_accommodations_status    ON accommodations(status);
CREATE INDEX IF NOT EXISTS idx_placement_drives_status  ON placement_drives(status);
CREATE INDEX IF NOT EXISTS idx_admin_logs_admin         ON admin_logs(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_logs_created       ON admin_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_logs_target        ON admin_logs(target_type, target_id);


-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- TRIGGER: auto-assign student role on signup
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CREATE OR REPLACE FUNCTION assign_student_role()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_verified = TRUE THEN
        INSERT INTO user_roles (user_id, role)
        VALUES (NEW.id, 'student')
        ON CONFLICT DO NOTHING;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_assign_student_role
AFTER INSERT OR UPDATE OF is_verified ON users
FOR EACH ROW
EXECUTE FUNCTION assign_student_role();
