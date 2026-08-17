"""Initial PostgreSQL schema.

Revision ID: 20260816_0001
Revises:
"""
from alembic import op


revision = "20260816_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute(
        """
        CREATE TABLE teachers (
            id BIGSERIAL PRIMARY KEY,
            full_name TEXT NOT NULL,
            email CITEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'teacher' CHECK (role IN ('admin','teacher')),
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
            must_change_password INTEGER NOT NULL DEFAULT 0 CHECK (must_change_password IN (0,1)),
            last_login_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE sections (
            id BIGSERIAL PRIMARY KEY,
            name CITEXT NOT NULL UNIQUE,
            description TEXT,
            is_archived INTEGER NOT NULL DEFAULT 0 CHECK (is_archived IN (0,1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE students (
            id BIGSERIAL PRIMARY KEY,
            full_name CITEXT NOT NULL,
            section_id BIGINT NOT NULL REFERENCES sections(id),
            student_code TEXT UNIQUE,
            email CITEXT,
            password_hash TEXT,
            must_change_password INTEGER NOT NULL DEFAULT 1 CHECK (must_change_password IN (0,1)),
            password_updated_at TEXT,
            last_login_at TEXT,
            notes TEXT,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
            is_archived INTEGER NOT NULL DEFAULT 0 CHECK (is_archived IN (0,1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(section_id, full_name)
        );
        CREATE TABLE subjects (
            id BIGSERIAL PRIMARY KEY,
            name CITEXT NOT NULL UNIQUE,
            description TEXT,
            is_archived INTEGER NOT NULL DEFAULT 0 CHECK (is_archived IN (0,1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE categories (
            id BIGSERIAL PRIMARY KEY,
            subject_id BIGINT NOT NULL REFERENCES subjects(id),
            name CITEXT NOT NULL,
            description TEXT,
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_archived INTEGER NOT NULL DEFAULT 0 CHECK (is_archived IN (0,1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(subject_id, name)
        );
        CREATE TABLE question_bank (
            id TEXT PRIMARY KEY,
            teacher_id BIGINT NOT NULL REFERENCES teachers(id),
            subject_id BIGINT NOT NULL REFERENCES subjects(id),
            category_id BIGINT NOT NULL REFERENCES categories(id),
            type TEXT NOT NULL,
            prompt TEXT NOT NULL,
            data_json TEXT NOT NULL,
            answer_json TEXT NOT NULL,
            audio TEXT,
            script TEXT,
            is_active INTEGER NOT NULL DEFAULT 0 CHECK (is_active IN (0,1)),
            is_archived INTEGER NOT NULL DEFAULT 0 CHECK (is_archived IN (0,1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE exams (
            id BIGSERIAL PRIMARY KEY,
            teacher_id BIGINT NOT NULL REFERENCES teachers(id),
            subject_id BIGINT NOT NULL REFERENCES subjects(id),
            title TEXT NOT NULL,
            description TEXT,
            is_published INTEGER NOT NULL DEFAULT 0 CHECK (is_published IN (0,1)),
            is_archived INTEGER NOT NULL DEFAULT 0 CHECK (is_archived IN (0,1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE exam_versions (
            id BIGSERIAL PRIMARY KEY,
            exam_id BIGINT NOT NULL REFERENCES exams(id),
            name CITEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(exam_id, name)
        );
        CREATE TABLE exam_version_questions (
            version_id BIGINT NOT NULL REFERENCES exam_versions(id) ON DELETE CASCADE,
            question_id TEXT NOT NULL REFERENCES question_bank(id),
            position INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(version_id, question_id)
        );
        CREATE TABLE exam_assignments (
            id BIGSERIAL PRIMARY KEY,
            exam_id BIGINT NOT NULL REFERENCES exams(id),
            section_id BIGINT NOT NULL REFERENCES sections(id),
            version_mode TEXT NOT NULL DEFAULT 'random' CHECK (version_mode IN ('random','fixed')),
            fixed_version_id BIGINT REFERENCES exam_versions(id),
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(exam_id, section_id)
        );
        CREATE TABLE student_exam_allocations (
            id BIGSERIAL PRIMARY KEY,
            assignment_id BIGINT NOT NULL REFERENCES exam_assignments(id),
            student_id BIGINT NOT NULL REFERENCES students(id),
            version_id BIGINT NOT NULL REFERENCES exam_versions(id),
            allocated_at TEXT NOT NULL,
            UNIQUE(assignment_id, student_id)
        );
        CREATE TABLE attempts (
            id TEXT PRIMARY KEY,
            teacher_id BIGINT NOT NULL REFERENCES teachers(id),
            student_id BIGINT NOT NULL REFERENCES students(id),
            student_email TEXT,
            student_name TEXT NOT NULL,
            section TEXT NOT NULL,
            started_at TEXT NOT NULL,
            submitted_at TEXT,
            seed BIGINT NOT NULL,
            score DOUBLE PRECISION,
            total DOUBLE PRECISION,
            percentage DOUBLE PRECISION,
            grade10 DOUBLE PRECISION,
            category_scores TEXT,
            type_scores TEXT,
            answers_json TEXT,
            status TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress','submitted')),
            focus_departures INTEGER NOT NULL DEFAULT 0,
            focus_returns INTEGER NOT NULL DEFAULT 0,
            away_seconds DOUBLE PRECISION NOT NULL DEFAULT 0,
            longest_away_seconds DOUBLE PRECISION NOT NULL DEFAULT 0,
            blur_events INTEGER NOT NULL DEFAULT 0,
            pagehide_events INTEGER NOT NULL DEFAULT 0,
            context_menu_attempts INTEGER NOT NULL DEFAULT 0,
            copy_attempts INTEGER NOT NULL DEFAULT 0,
            cut_attempts INTEGER NOT NULL DEFAULT 0,
            paste_attempts INTEGER NOT NULL DEFAULT 0,
            shortcut_attempts INTEGER NOT NULL DEFAULT 0,
            fullscreen_exits INTEGER NOT NULL DEFAULT 0,
            last_security_event_at TEXT,
            questions_json TEXT,
            assessment_title TEXT,
            assessment_subject TEXT,
            category_labels_json TEXT,
            ui_language TEXT,
            exam_id BIGINT NOT NULL REFERENCES exams(id),
            exam_version_id BIGINT NOT NULL REFERENCES exam_versions(id),
            assignment_id BIGINT NOT NULL REFERENCES exam_assignments(id),
            exam_version_name TEXT,
            policy_version TEXT,
            policy_accepted_at TEXT,
            policy_text TEXT
        );
        CREATE TABLE integrity_events (
            id BIGSERIAL PRIMARY KEY,
            attempt_id TEXT NOT NULL REFERENCES attempts(id),
            event_type TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            detail_json TEXT
        );
        CREATE TABLE attempt_penalties (
            id BIGSERIAL PRIMARY KEY,
            attempt_id TEXT NOT NULL REFERENCES attempts(id),
            teacher_id BIGINT NOT NULL REFERENCES teachers(id),
            points DOUBLE PRECISION NOT NULL CHECK(points > 0),
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL,
            revoked_at TEXT,
            revoked_by BIGINT REFERENCES teachers(id),
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1))
        );
        CREATE TABLE app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);

        CREATE UNIQUE INDEX idx_students_email_unique ON students(email) WHERE email IS NOT NULL AND BTRIM(email::text) <> '';
        CREATE INDEX idx_teachers_active ON teachers(is_active, role, full_name);
        CREATE INDEX idx_question_bank_teacher ON question_bank(teacher_id, subject_id, is_archived);
        CREATE INDEX idx_question_bank_active ON question_bank(subject_id, is_active, is_archived);
        CREATE INDEX idx_question_bank_category ON question_bank(category_id, type);
        CREATE INDEX idx_exams_teacher ON exams(teacher_id, is_published, is_archived);
        CREATE INDEX idx_exams_subject ON exams(subject_id, is_published, is_archived);
        CREATE INDEX idx_attempts_teacher ON attempts(teacher_id, status, submitted_at);
        CREATE UNIQUE INDEX idx_attempt_once_per_assignment ON attempts(student_id, assignment_id) WHERE assignment_id IS NOT NULL;
        CREATE INDEX idx_integrity_attempt ON integrity_events(attempt_id);
        CREATE INDEX idx_attempt_penalties_active ON attempt_penalties(attempt_id, is_active);
        CREATE INDEX idx_attempt_penalties_teacher ON attempt_penalties(teacher_id, created_at);
        CREATE INDEX idx_categories_subject ON categories(subject_id, is_archived, sort_order, name);
        CREATE INDEX idx_students_section ON students(section_id, is_active, is_archived, full_name);
        CREATE INDEX idx_versions_exam ON exam_versions(exam_id, is_active);
        CREATE INDEX idx_assignments_section ON exam_assignments(section_id, is_active);
        """
    )


def downgrade():
    op.execute(
        """
        DROP TABLE IF EXISTS attempt_penalties;
        DROP TABLE IF EXISTS integrity_events;
        DROP TABLE IF EXISTS attempts;
        DROP TABLE IF EXISTS student_exam_allocations;
        DROP TABLE IF EXISTS exam_assignments;
        DROP TABLE IF EXISTS exam_version_questions;
        DROP TABLE IF EXISTS exam_versions;
        DROP TABLE IF EXISTS exams;
        DROP TABLE IF EXISTS question_bank;
        DROP TABLE IF EXISTS categories;
        DROP TABLE IF EXISTS subjects;
        DROP TABLE IF EXISTS students;
        DROP TABLE IF EXISTS sections;
        DROP TABLE IF EXISTS app_settings;
        DROP TABLE IF EXISTS teachers;
        """
    )
