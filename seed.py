#!/usr/bin/env python3
"""Development seed data for Assessment Studio Universal.

Creates:
- 4 demo teacher accounts (1 admin + 3 subject teachers).
- 3 demo subjects.
- 3 categories per subject (9 categories total).
- At least 2 questions per category (19 questions total; includes one audio/listening demo).
- 3 sections (A, B, C).
- 5 registered students per section (15 roster records + submitted attempts).
- Sample integrity events so each teacher dashboard and Excel export can be tested.

Teacher-owned questions, exams and attempts are distributed across the three subject teachers;
students and sections remain shared institutional roster data.

The script uses Python's standard library and creates Werkzeug-compatible PBKDF2 password hashes.
It writes to data/results.db by default, or to DATABASE_PATH when that environment
variable is set.

Usage:
    python seed.py
    python seed.py --keep-settings
    python seed.py --no-results
    python seed.py --clean

Re-running is safe for development: only rows whose IDs start with ``seed_`` are
replaced. Existing real attempts/questions are not deleted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import secrets
import sqlite3
import struct
import wave
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from policy_defaults import DEFAULT_RULES_VERSION, DEFAULT_STUDENT_RULES_EN, DEFAULT_STUDENT_RULES_ES

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
AUDIO_DIR = BASE_DIR / "static" / "audio"
DB_PATH = Path(os.getenv("DATABASE_PATH", str(DATA_DIR / "results.db")))

TYPE_KEYS = [
    "multiple_choice",
    "true_false",
    "short_answer",
    "numeric",
    "order",
    "matching",
    "listening",
]

DEMO_PASSWORD = "Demo1234"
DEMO_TEACHER_PASSWORD = "DemoTeacher123"
DEMO_ADMIN_PASSWORD = "DemoAdmin123"

DEMO_TEACHERS = [
    {"name": "Seed Administrator", "email": "seed.admin@assessment.local", "password": DEMO_ADMIN_PASSWORD, "role": "admin"},
    {"name": "Mathematics Teacher", "email": "seed.math@assessment.local", "password": DEMO_TEACHER_PASSWORD, "role": "teacher", "subject": "Mathematics"},
    {"name": "Science Teacher", "email": "seed.science@assessment.local", "password": DEMO_TEACHER_PASSWORD, "role": "teacher", "subject": "Science"},
    {"name": "English Teacher", "email": "seed.english@assessment.local", "password": DEMO_TEACHER_PASSWORD, "role": "teacher", "subject": "English"},
]

SECTIONS = {
    "A": [
        "Ana López",
        "Carlos Hernández",
        "Daniela Martínez",
        "José Ramírez",
        "Sofía Cruz",
    ],
    "B": [
        "Andrea Flores",
        "Diego Morales",
        "Elena Rodríguez",
        "Kevin García",
        "Valeria Pérez",
    ],
    "C": [
        "Camila Torres",
        "Fernando Mejía",
        "Gabriela Castillo",
        "Luis Romero",
        "Mariana Sánchez",
    ],
}

SUBJECTS = [
    {
        "name": "Mathematics",
        "description": "Demo subject for testing numeric and objective question types.",
        "categories": [
            ("Algebra", "Equations and basic algebraic reasoning."),
            ("Geometry", "Shapes, angles, area and perimeter."),
            ("Statistics", "Mean, mode and basic data interpretation."),
        ],
    },
    {
        "name": "Science",
        "description": "Demo subject for testing concepts, sequences and audio questions.",
        "categories": [
            ("Matter", "States and properties of matter."),
            ("Biology", "Cells and basic life science."),
            ("Energy", "Forms and transformations of energy."),
        ],
    },
    {
        "name": "English",
        "description": "Demo subject for grammar, vocabulary and reading.",
        "categories": [
            ("Grammar", "Basic grammar and sentence structure."),
            ("Vocabulary", "Common vocabulary and word relationships."),
            ("Reading", "Short reading-comprehension items."),
        ],
    },
]


def now_iso(dt: datetime | None = None) -> str:
    return (dt or datetime.now()).replace(microsecond=0).isoformat()


def generate_password_hash(password: str, iterations: int = 1_000_000) -> str:
    """Return a Werkzeug-compatible pbkdf2:sha256 password hash."""
    salt = secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations).hex()
    return f"pbkdf2:sha256:{iterations}${salt}${digest}"


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def ensure_column(conn: sqlite3.Connection, table: str, name: str, definition: str) -> None:
    if name not in table_columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create the universal schema when seed.py is run before the Flask app."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'teacher',
            is_active INTEGER NOT NULL DEFAULT 1,
            must_change_password INTEGER NOT NULL DEFAULT 0,
            last_login_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS attempts (
            id TEXT PRIMARY KEY,
            teacher_id INTEGER,
            student_id INTEGER,
            student_email TEXT,
            student_name TEXT NOT NULL,
            section TEXT NOT NULL,
            started_at TEXT NOT NULL,
            submitted_at TEXT,
            seed INTEGER NOT NULL,
            score REAL,
            total REAL,
            percentage REAL,
            grade10 REAL,
            category_scores TEXT,
            type_scores TEXT,
            answers_json TEXT,
            status TEXT NOT NULL DEFAULT 'in_progress',
            focus_departures INTEGER NOT NULL DEFAULT 0,
            focus_returns INTEGER NOT NULL DEFAULT 0,
            away_seconds REAL NOT NULL DEFAULT 0,
            longest_away_seconds REAL NOT NULL DEFAULT 0,
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
            exam_id INTEGER,
            exam_version_id INTEGER,
            assignment_id INTEGER,
            exam_version_name TEXT
        );

        CREATE TABLE IF NOT EXISTS integrity_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            detail_json TEXT,
            FOREIGN KEY (attempt_id) REFERENCES attempts(id)
        );

        CREATE TABLE IF NOT EXISTS attempt_penalties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id TEXT NOT NULL,
            teacher_id INTEGER NOT NULL,
            points REAL NOT NULL CHECK(points > 0),
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL,
            revoked_at TEXT,
            revoked_by INTEGER,
            is_active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (attempt_id) REFERENCES attempts(id),
            FOREIGN KEY (teacher_id) REFERENCES teachers(id),
            FOREIGN KEY (revoked_by) REFERENCES teachers(id)
        );

        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            description TEXT,
            is_archived INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL COLLATE NOCASE,
            section_id INTEGER NOT NULL,
            student_code TEXT UNIQUE,
            email TEXT,
            password_hash TEXT,
            must_change_password INTEGER NOT NULL DEFAULT 0,
            password_updated_at TEXT,
            last_login_at TEXT,
            notes TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            is_archived INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(section_id, full_name),
            FOREIGN KEY (section_id) REFERENCES sections(id)
        );

        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            description TEXT,
            is_archived INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            name TEXT NOT NULL COLLATE NOCASE,
            description TEXT,
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_archived INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(subject_id, name),
            FOREIGN KEY (subject_id) REFERENCES subjects(id)
        );

        CREATE TABLE IF NOT EXISTS question_bank (
            id TEXT PRIMARY KEY,
            teacher_id INTEGER,
            subject_id INTEGER,
            category_id INTEGER,
            type TEXT NOT NULL,
            prompt TEXT NOT NULL,
            data_json TEXT NOT NULL,
            answer_json TEXT NOT NULL,
            audio TEXT,
            script TEXT,
            is_active INTEGER NOT NULL DEFAULT 0,
            is_archived INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (subject_id) REFERENCES subjects(id),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER,
            subject_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            is_published INTEGER NOT NULL DEFAULT 0,
            is_archived INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (subject_id) REFERENCES subjects(id)
        );
        CREATE TABLE IF NOT EXISTS exam_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(exam_id,name),
            FOREIGN KEY (exam_id) REFERENCES exams(id)
        );
        CREATE TABLE IF NOT EXISTS exam_version_questions (
            version_id INTEGER NOT NULL,
            question_id TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(version_id,question_id),
            FOREIGN KEY (version_id) REFERENCES exam_versions(id) ON DELETE CASCADE,
            FOREIGN KEY (question_id) REFERENCES question_bank(id)
        );
        CREATE TABLE IF NOT EXISTS exam_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER NOT NULL,
            section_id INTEGER NOT NULL,
            version_mode TEXT NOT NULL DEFAULT 'random',
            fixed_version_id INTEGER,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(exam_id,section_id),
            FOREIGN KEY (exam_id) REFERENCES exams(id),
            FOREIGN KEY (section_id) REFERENCES sections(id),
            FOREIGN KEY (fixed_version_id) REFERENCES exam_versions(id)
        );
        CREATE TABLE IF NOT EXISTS student_exam_allocations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            version_id INTEGER NOT NULL,
            allocated_at TEXT NOT NULL,
            UNIQUE(assignment_id,student_id),
            FOREIGN KEY (assignment_id) REFERENCES exam_assignments(id),
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (version_id) REFERENCES exam_versions(id)
        );
        """
    )

    # Helpful when using a DB created by an older build.
    for name, definition in {
        "teacher_id": "INTEGER",
        "student_id": "INTEGER",
        "student_email": "TEXT",
        "category_scores": "TEXT",
        "type_scores": "TEXT",
        "answers_json": "TEXT",
        "focus_departures": "INTEGER NOT NULL DEFAULT 0",
        "focus_returns": "INTEGER NOT NULL DEFAULT 0",
        "away_seconds": "REAL NOT NULL DEFAULT 0",
        "longest_away_seconds": "REAL NOT NULL DEFAULT 0",
        "blur_events": "INTEGER NOT NULL DEFAULT 0",
        "pagehide_events": "INTEGER NOT NULL DEFAULT 0",
        "context_menu_attempts": "INTEGER NOT NULL DEFAULT 0",
        "copy_attempts": "INTEGER NOT NULL DEFAULT 0",
        "cut_attempts": "INTEGER NOT NULL DEFAULT 0",
        "paste_attempts": "INTEGER NOT NULL DEFAULT 0",
        "shortcut_attempts": "INTEGER NOT NULL DEFAULT 0",
        "fullscreen_exits": "INTEGER NOT NULL DEFAULT 0",
        "last_security_event_at": "TEXT",
        "questions_json": "TEXT",
        "assessment_title": "TEXT",
        "assessment_subject": "TEXT",
        "category_labels_json": "TEXT",
        "ui_language": "TEXT",
        "exam_id": "INTEGER",
        "exam_version_id": "INTEGER",
        "assignment_id": "INTEGER",
        "exam_version_name": "TEXT",
        "policy_version": "TEXT",
        "policy_accepted_at": "TEXT",
        "policy_text": "TEXT",
    }.items():
        ensure_column(conn, "attempts", name, definition)

    for name, definition in {
        "email": "TEXT",
        "password_hash": "TEXT",
        "must_change_password": "INTEGER NOT NULL DEFAULT 0",
        "password_updated_at": "TEXT",
        "last_login_at": "TEXT",
        "is_archived": "INTEGER NOT NULL DEFAULT 0",
    }.items():
        ensure_column(conn, "students", name, definition)

    ensure_column(conn, "question_bank", "teacher_id", "INTEGER")
    ensure_column(conn, "question_bank", "subject_id", "INTEGER")
    ensure_column(conn, "question_bank", "category_id", "INTEGER")
    ensure_column(conn, "exams", "teacher_id", "INTEGER")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_integrity_attempt ON integrity_events(attempt_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_attempt_penalties_active ON attempt_penalties(attempt_id,is_active)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_attempt_penalties_teacher ON attempt_penalties(teacher_id,created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_teachers_active ON teachers(is_active, role, full_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_question_bank_teacher ON question_bank(teacher_id, subject_id, is_archived)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_exams_teacher ON exams(teacher_id, subject_id, is_archived)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_attempts_teacher ON attempts(teacher_id, status, submitted_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_question_bank_active ON question_bank(subject_id, is_active, is_archived)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_question_bank_category ON question_bank(category_id, type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_categories_subject ON categories(subject_id, is_archived, sort_order, name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_students_section ON students(section_id, is_active, is_archived, full_name)")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_students_email_unique ON students(email COLLATE NOCASE) WHERE email IS NOT NULL AND TRIM(email) <> ''")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_exams_subject ON exams(subject_id,is_published,is_archived)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_versions_exam ON exam_versions(exam_id,is_active)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_assignments_section ON exam_assignments(section_id,is_active)")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_attempt_once_per_assignment ON attempts(student_id,assignment_id) WHERE assignment_id IS NOT NULL")


def upsert_demo_teachers(conn: sqlite3.Connection) -> tuple[dict[str, int], int]:
    """Create demo teacher accounts and return subject->teacher ownership plus admin id."""
    stamp = now_iso()
    subject_owner: dict[str, int] = {}
    admin_id = 0
    for item in DEMO_TEACHERS:
        row = conn.execute("SELECT id FROM teachers WHERE email=? COLLATE NOCASE", (item["email"],)).fetchone()
        password_hash = generate_password_hash(item["password"])
        if row:
            teacher_id = int(row["id"])
            conn.execute(
                """UPDATE teachers SET full_name=?,password_hash=?,role=?,is_active=1,must_change_password=0,updated_at=? WHERE id=?""",
                (item["name"], password_hash, item["role"], stamp, teacher_id),
            )
        else:
            cur = conn.execute(
                """INSERT INTO teachers(full_name,email,password_hash,role,is_active,must_change_password,created_at,updated_at)
                   VALUES(?,?,?,?,1,0,?,?)""",
                (item["name"], item["email"], password_hash, item["role"], stamp, stamp),
            )
            teacher_id = int(cur.lastrowid)
        if item.get("role") == "admin":
            admin_id = teacher_id
        if item.get("subject"):
            subject_owner[item["subject"]] = teacher_id
    return subject_owner, admin_id


def upsert_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO app_settings(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def get_or_create_subject(conn: sqlite3.Connection, name: str, description: str) -> int:
    stamp = now_iso()
    row = conn.execute("SELECT id FROM subjects WHERE name=? COLLATE NOCASE", (name,)).fetchone()
    if row:
        conn.execute(
            "UPDATE subjects SET description=?, is_archived=0, updated_at=? WHERE id=?",
            (description, stamp, row["id"]),
        )
        return int(row["id"])
    cur = conn.execute(
        "INSERT INTO subjects(name,description,is_archived,created_at,updated_at) VALUES(?,?,0,?,?)",
        (name, description, stamp, stamp),
    )
    return int(cur.lastrowid)


def get_or_create_category(
    conn: sqlite3.Connection,
    subject_id: int,
    name: str,
    description: str,
    sort_order: int,
) -> int:
    stamp = now_iso()
    row = conn.execute(
        "SELECT id FROM categories WHERE subject_id=? AND name=? COLLATE NOCASE",
        (subject_id, name),
    ).fetchone()
    if row:
        conn.execute(
            "UPDATE categories SET description=?, sort_order=?, is_archived=0, updated_at=? WHERE id=?",
            (description, sort_order, stamp, row["id"]),
        )
        return int(row["id"])
    cur = conn.execute(
        """INSERT INTO categories(subject_id,name,description,sort_order,is_archived,created_at,updated_at)
           VALUES(?,?,?,?,0,?,?)""",
        (subject_id, name, description, sort_order, stamp, stamp),
    )
    return int(cur.lastrowid)


def q_mc(qid: str, prompt: str, choices: list[str], correct_index: int) -> dict[str, Any]:
    ids = [f"c{i+1}" for i in range(len(choices))]
    return {
        "id": qid,
        "type": "multiple_choice",
        "prompt": prompt,
        "data": {"choices": [[cid, text] for cid, text in zip(ids, choices)]},
        "answer": ids[correct_index],
    }


def q_tf(qid: str, prompt: str, answer: bool) -> dict[str, Any]:
    return {
        "id": qid,
        "type": "true_false",
        "prompt": prompt,
        "data": {"choices": [["true", "True"], ["false", "False"]]},
        "answer": "true" if answer else "false",
    }


def q_numeric(qid: str, prompt: str, value: float, tolerance: float = 0.0) -> dict[str, Any]:
    return {
        "id": qid,
        "type": "numeric",
        "prompt": prompt,
        "data": {},
        "answer": {"value": value, "tolerance": tolerance},
    }


def q_short(qid: str, prompt: str, answers: list[str], case_sensitive: bool = False) -> dict[str, Any]:
    return {
        "id": qid,
        "type": "short_answer",
        "prompt": prompt,
        "data": {"case_sensitive": case_sensitive},
        "answer": answers,
    }


def q_order(qid: str, prompt: str, items: list[str]) -> dict[str, Any]:
    keys = [str(i + 1) for i in range(len(items))]
    return {
        "id": qid,
        "type": "order",
        "prompt": prompt,
        "data": {"items": [[key, text] for key, text in zip(keys, items)]},
        "answer": keys,
    }


def q_matching(qid: str, prompt: str, pairs: list[tuple[str, str]]) -> dict[str, Any]:
    left = [[f"l{i+1}", pair[0]] for i, pair in enumerate(pairs)]
    right = [[f"r{i+1}", pair[1]] for i, pair in enumerate(pairs)]
    answer = {f"l{i+1}": f"r{i+1}" for i in range(len(pairs))}
    return {
        "id": qid,
        "type": "matching",
        "prompt": prompt,
        "data": {"left": left, "right": right},
        "answer": answer,
    }


def q_listening(
    qid: str,
    prompt: str,
    choices: list[str],
    correct_index: int,
    audio: str,
    script: str,
) -> dict[str, Any]:
    item = q_mc(qid, prompt, choices, correct_index)
    item["type"] = "listening"
    item["audio"] = audio
    item["script"] = script
    return item


def create_beep_audio(filename: str, beep_count: int = 3) -> None:
    """Create a tiny WAV file so the listening player can be tested without TTS."""
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    path = AUDIO_DIR / filename
    sample_rate = 22050
    frequency = 660.0
    beep_seconds = 0.22
    gap_seconds = 0.18
    amplitude = 12000

    frames: list[bytes] = []
    for beep_index in range(beep_count):
        samples = int(sample_rate * beep_seconds)
        for i in range(samples):
            fade = min(1.0, i / 200, (samples - i) / 200)
            value = int(amplitude * fade * math.sin(2 * math.pi * frequency * i / sample_rate))
            frames.append(struct.pack("<h", value))
        if beep_index < beep_count - 1:
            frames.extend([struct.pack("<h", 0)] * int(sample_rate * gap_seconds))

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"".join(frames))


def demo_question_specs() -> dict[tuple[str, str], list[dict[str, Any]]]:
    return {
        ("Mathematics", "Algebra"): [
            q_mc("seed_math_alg_01", "Solve: x + 5 = 12. What is x?", ["5", "6", "7", "17"], 2),
            q_numeric("seed_math_alg_02", "Calculate 3 × 8.", 24),
        ],
        ("Mathematics", "Geometry"): [
            q_tf("seed_math_geo_01", "The sum of the interior angles of a triangle is 180°.", True),
            q_numeric("seed_math_geo_02", "A rectangle is 7 cm long and 4 cm wide. What is its area in cm²?", 28),
        ],
        ("Mathematics", "Statistics"): [
            q_mc("seed_math_sta_01", "What is the mode of 2, 4, 4, 5, 7?", ["2", "4", "5", "7"], 1),
            q_numeric("seed_math_sta_02", "What is the mean of 4, 6 and 8?", 6),
        ],
        ("Science", "Matter"): [
            q_mc("seed_sci_mat_01", "Which state of matter has a definite volume but takes the shape of its container?", ["Solid", "Liquid", "Gas", "Plasma"], 1),
            q_tf("seed_sci_mat_02", "Evaporation is the change from liquid to gas.", True),
        ],
        ("Science", "Biology"): [
            q_matching(
                "seed_sci_bio_01",
                "Match each cell structure with its main function.",
                [("Nucleus", "Controls cell activities"), ("Cell membrane", "Controls what enters and leaves"), ("Chloroplast", "Carries out photosynthesis")],
            ),
            q_mc("seed_sci_bio_02", "Which organelle is commonly associated with photosynthesis in plant cells?", ["Nucleus", "Chloroplast", "Ribosome", "Vacuole"], 1),
        ],
        ("Science", "Energy"): [
            q_order(
                "seed_sci_eng_01",
                "Put this simple energy transformation in order for a flashlight.",
                ["Chemical energy in the battery", "Electrical energy in the circuit", "Light energy from the bulb"],
            ),
            q_mc("seed_sci_eng_02", "Which of these is a renewable energy source?", ["Coal", "Petroleum", "Solar energy", "Natural gas"], 2),
            q_listening(
                "seed_sci_eng_03",
                "Audio test: how many short tones do you hear?",
                ["Two", "Three", "Four", "Five"],
                1,
                "seed_three_beeps.wav",
                "Three short tones are played. This synthetic audio exists only to test the Audio / Listening question type.",
            ),
        ],
        ("English", "Grammar"): [
            q_mc("seed_eng_gra_01", "Choose the correct past form: Yesterday, I ___ to school early.", ["go", "went", "going", "goes"], 1),
            q_order("seed_eng_gra_02", "Put the words in the correct sentence order.", ["She", "is", "reading", "a book"]),
        ],
        ("English", "Vocabulary"): [
            q_matching(
                "seed_eng_voc_01",
                "Match each place with the action you normally do there.",
                [("Hospital", "See a doctor"), ("Bank", "Get money"), ("Supermarket", "Buy groceries")],
            ),
            q_short("seed_eng_voc_02", "Write the opposite of 'expensive'.", ["cheap", "inexpensive"]),
        ],
        ("English", "Reading"): [
            q_mc(
                "seed_eng_rea_01",
                "Read: 'Mia lives near the park. Every Saturday she walks there with her dog.' Where does Mia go on Saturdays?",
                ["To the bank", "To the park", "To school", "To the hospital"],
                1,
            ),
            q_tf(
                "seed_eng_rea_02",
                "Read: 'Tom usually takes the bus, but today he is walking.' Tom is walking today.",
                True,
            ),
        ],
    }


def upsert_question(
    conn: sqlite3.Connection,
    teacher_id: int,
    subject_id: int,
    category_id: int,
    spec: dict[str, Any],
) -> None:
    stamp = now_iso()
    conn.execute(
        """INSERT INTO question_bank
           (id,teacher_id,subject_id,category_id,type,prompt,data_json,answer_json,audio,script,is_active,is_archived,created_at,updated_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,1,0,?,?)
           ON CONFLICT(id) DO UPDATE SET
             teacher_id=excluded.teacher_id,
             subject_id=excluded.subject_id,
             category_id=excluded.category_id,
             type=excluded.type,
             prompt=excluded.prompt,
             data_json=excluded.data_json,
             answer_json=excluded.answer_json,
             audio=excluded.audio,
             script=excluded.script,
             is_active=1,
             is_archived=0,
             updated_at=excluded.updated_at""",
        (
            spec["id"],
            teacher_id,
            subject_id,
            category_id,
            spec["type"],
            spec["prompt"],
            json.dumps(spec.get("data", {}), ensure_ascii=False),
            json.dumps(spec.get("answer"), ensure_ascii=False),
            spec.get("audio"),
            spec.get("script"),
            stamp,
            stamp,
        ),
    )


def row_to_snapshot(row: sqlite3.Row) -> dict[str, Any]:
    data = json.loads(row["data_json"] or "{}")
    question = {
        "id": row["id"],
        "subject_id": row["subject_id"],
        "subject_name": row["subject_name"],
        "category_id": row["category_id"],
        "category_name": row["category_name"],
        "type": row["type"],
        "prompt": row["prompt"],
        "answer": json.loads(row["answer_json"]),
    }
    question.update(data)
    if row["audio"]:
        question["audio"] = row["audio"]
    if row["script"]:
        question["script"] = row["script"]
    return question


def fetch_subject_questions(conn: sqlite3.Connection, subject_id: int, teacher_id: int | None = None) -> list[dict[str, Any]]:
    teacher_clause = " AND q.teacher_id=?" if teacher_id is not None else ""
    params: tuple[Any, ...] = (subject_id, teacher_id) if teacher_id is not None else (subject_id,)
    rows = conn.execute(
        """SELECT q.*, s.name AS subject_name, c.name AS category_name
           FROM question_bank q
           JOIN subjects s ON s.id=q.subject_id
           JOIN categories c ON c.id=q.category_id
           WHERE q.subject_id=? AND q.is_active=1 AND q.is_archived=0""" + teacher_clause + """
           ORDER BY c.sort_order, c.name, q.id""",
        params,
    ).fetchall()
    return [row_to_snapshot(row) for row in rows]


def blank_type_scores() -> dict[str, dict[str, float]]:
    return {key: {"earned": 0.0, "total": 0.0} for key in TYPE_KEYS}


def upsert_demo_roster(conn: sqlite3.Connection) -> dict[tuple[str, str], int]:
    """Create the 3 demo sections and 15 registered student accounts."""
    roster: dict[tuple[str, str], int] = {}
    stamp = now_iso()
    password_hash = generate_password_hash(DEMO_PASSWORD)
    for section_name, names in SECTIONS.items():
        row = conn.execute("SELECT id FROM sections WHERE name=? COLLATE NOCASE", (section_name,)).fetchone()
        if row:
            section_id = int(row["id"])
            conn.execute("UPDATE sections SET is_archived=0,updated_at=? WHERE id=?", (stamp, section_id))
        else:
            cur = conn.execute(
                "INSERT INTO sections(name,description,is_archived,created_at,updated_at) VALUES(?,?,0,?,?)",
                (section_name, f"Demo section {section_name}", stamp, stamp),
            )
            section_id = int(cur.lastrowid)
        for idx, full_name in enumerate(names, start=1):
            code = f"SEED-{section_name}-{idx:02d}"
            email = f"seed.{section_name.lower()}{idx:02d}@example.com"
            student = conn.execute(
                "SELECT id FROM students WHERE student_code=? OR email=? COLLATE NOCASE OR (section_id=? AND full_name=? COLLATE NOCASE)",
                (code, email, section_id, full_name),
            ).fetchone()
            if student:
                student_id = int(student["id"])
                conn.execute(
                    """UPDATE students SET full_name=?,section_id=?,student_code=?,email=?,password_hash=?,must_change_password=0,
                       password_updated_at=?,notes=?,is_active=1,updated_at=? WHERE id=?""",
                    (full_name, section_id, code, email, password_hash, stamp, "Demo student generated by seed.py", stamp, student_id),
                )
            else:
                cur = conn.execute(
                    """INSERT INTO students(full_name,section_id,student_code,email,password_hash,must_change_password,password_updated_at,notes,is_active,created_at,updated_at)
                       VALUES(?,?,?,?,?,0,?,?,1,?,?)""",
                    (full_name, section_id, code, email, password_hash, stamp, "Demo student generated by seed.py", stamp, stamp),
                )
                student_id = int(cur.lastrowid)
            roster[(section_name, full_name)] = student_id
    return roster


def seed_demo_exams(conn: sqlite3.Connection, subject_ids: dict[str, int], teacher_ids: dict[str, int]) -> int:
    """Create three published demo exams, each with two versions and section assignments."""
    stamp = now_iso()
    section_rows = conn.execute("SELECT id,name FROM sections WHERE name IN ('A','B','C') AND is_archived=0 ORDER BY name").fetchall()
    definitions = [
        ("English", "SEED • English Review", "Two-version English demo exam assigned randomly."),
        ("Mathematics", "SEED • Mathematics Skills", "Reusable Mathematics exam with multiple versions."),
        ("Science", "SEED • Science Concepts", "Science demo exam for testing section assignments."),
    ]
    created = 0
    for subject_name, title, description in definitions:
        subject_id = subject_ids[subject_name]
        teacher_id = teacher_ids[subject_name]
        row = conn.execute("SELECT id FROM exams WHERE title=? AND teacher_id=?", (title, teacher_id)).fetchone()
        if row:
            exam_id = int(row["id"])
            conn.execute("UPDATE exams SET teacher_id=?,subject_id=?,description=?,is_published=1,is_archived=0,updated_at=? WHERE id=?",
                         (teacher_id, subject_id, description, stamp, exam_id))
        else:
            cur = conn.execute("INSERT INTO exams(teacher_id,subject_id,title,description,is_published,is_archived,created_at,updated_at) VALUES(?,?,?,?,1,0,?,?)",
                               (teacher_id, subject_id, title, description, stamp, stamp))
            exam_id = int(cur.lastrowid)
        qids = [r["id"] for r in conn.execute("SELECT id FROM question_bank WHERE teacher_id=? AND subject_id=? AND id LIKE 'seed_%' AND is_archived=0 ORDER BY id", (teacher_id, subject_id)).fetchall()]
        if len(qids) < 2:
            continue
        version_ids = []
        for idx, name in enumerate(("A", "B")):
            vr = conn.execute("SELECT id FROM exam_versions WHERE exam_id=? AND name=?", (exam_id, name)).fetchone()
            if vr:
                version_id = int(vr["id"])
                conn.execute("UPDATE exam_versions SET is_active=1,updated_at=? WHERE id=?", (stamp, version_id))
            else:
                cur = conn.execute("INSERT INTO exam_versions(exam_id,name,is_active,created_at,updated_at) VALUES(?,?,1,?,?)", (exam_id, name, stamp, stamp))
                version_id = int(cur.lastrowid)
            version_ids.append(version_id)
            # Each version gets a different overlapping subset so grading/version behavior is easy to inspect.
            chosen = [qid for pos, qid in enumerate(qids) if (pos + idx) % 2 == 0]
            if len(chosen) < 2:
                chosen = qids[: min(4, len(qids))]
            conn.execute("DELETE FROM exam_version_questions WHERE version_id=?", (version_id,))
            for position, qid in enumerate(chosen):
                conn.execute("INSERT INTO exam_version_questions(version_id,question_id,position) VALUES(?,?,?)", (version_id, qid, position))
        for sec in section_rows:
            # English/Science use random versions; Mathematics demonstrates a fixed version in A and random in B/C.
            mode = "fixed" if subject_name == "Mathematics" and sec["name"] == "A" else "random"
            fixed = version_ids[0] if mode == "fixed" else None
            conn.execute("""INSERT INTO exam_assignments(exam_id,section_id,version_mode,fixed_version_id,is_active,created_at,updated_at)
                VALUES(?,?,?,?,1,?,?) ON CONFLICT(exam_id,section_id) DO UPDATE SET version_mode=excluded.version_mode,
                fixed_version_id=excluded.fixed_version_id,is_active=1,updated_at=excluded.updated_at""",
                (exam_id, sec["id"], mode, fixed, stamp, stamp))
        created += 1
    return created


def insert_demo_attempts(
    conn: sqlite3.Connection,
    subject_ids: dict[str, int],
    category_ids: dict[tuple[str, str], int],
    roster: dict[tuple[str, str], int],
    teacher_ids: dict[str, int],
) -> int:
    # Rebuild only generated attempts/events on each run.
    seed_attempt_ids = [row["id"] for row in conn.execute("SELECT id FROM attempts WHERE id LIKE 'seed_attempt_%'").fetchall()]
    if seed_attempt_ids:
        placeholders = ",".join("?" for _ in seed_attempt_ids)
        conn.execute(f"DELETE FROM integrity_events WHERE attempt_id IN ({placeholders})", seed_attempt_ids)
        conn.execute(f"DELETE FROM attempts WHERE id IN ({placeholders})", seed_attempt_ids)

    rng = random.Random(20260814)
    subject_names = ["English", "Mathematics", "Science"]
    all_students = [(section, name) for section, names in SECTIONS.items() for name in names]
    base_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0) - timedelta(days=2)

    for index, (section, student_name) in enumerate(all_students, start=1):
        subject_name = subject_names[(index - 1) % len(subject_names)]
        subject_id = subject_ids[subject_name]
        teacher_id = teacher_ids[subject_name]
        questions = fetch_subject_questions(conn, subject_id, teacher_id)
        total = len(questions)

        # Deterministic but varied demo performance.
        target_probability = 0.55 + ((index - 1) % 5) * 0.09
        correctness: dict[str, bool] = {}
        for q in questions:
            correctness[q["id"]] = rng.random() < min(target_probability, 0.95)

        # Ensure the data looks varied and avoids accidental all-zero results.
        if questions and not any(correctness.values()):
            correctness[questions[0]["id"]] = True

        category_scores: dict[str, dict[str, float]] = {}
        type_scores = blank_type_scores()
        answers_json: dict[str, Any] = {}
        score = 0.0

        for q in questions:
            cat_key = str(q["category_id"])
            category_scores.setdefault(cat_key, {"earned": 0.0, "total": 0.0})
            category_scores[cat_key]["total"] += 1.0
            type_scores[q["type"]]["total"] += 1.0
            earned = 1.0 if correctness[q["id"]] else 0.0
            category_scores[cat_key]["earned"] += earned
            type_scores[q["type"]]["earned"] += earned
            score += earned
            answers_json[q["id"]] = "seed-correct" if earned else "seed-incorrect"

        percentage = round((score / total) * 100, 1) if total else 0.0
        grade10 = round((score / total) * 10, 1) if total else 0.0

        started = base_time + timedelta(minutes=index * 11)
        submitted = started + timedelta(minutes=18 + (index % 8))

        # Mix clean and review-worthy integrity records.
        focus_departures = 0
        focus_returns = 0
        away_seconds = 0.0
        longest_away = 0.0
        blur_events = 0
        pagehide_events = 0
        context_menu_attempts = 0
        copy_attempts = 0
        paste_attempts = 0
        shortcut_attempts = 0
        fullscreen_exits = 0
        event_specs: list[tuple[str, datetime, dict[str, Any]]] = []

        if index % 4 == 0:
            focus_departures = 1 + (index % 2)
            focus_returns = focus_departures
            away_seconds = round(8.5 + index * 1.7, 1)
            longest_away = round(away_seconds / focus_departures, 1)
            pagehide_events = 1
            event_specs.append(("visibility_hidden", started + timedelta(minutes=6), {"question": 3, "source": "seed"}))
            event_specs.append(("visibility_visible", started + timedelta(minutes=6, seconds=int(longest_away)), {"away_seconds": longest_away, "source": "seed"}))

        if index % 5 == 0:
            blur_events = 1
            context_menu_attempts = 1
            copy_attempts = 1 if index % 10 == 0 else 0
            paste_attempts = 1 if index % 15 == 0 else 0
            shortcut_attempts = 1
            event_specs.append(("window_blur", started + timedelta(minutes=9), {"question": 4, "source": "seed"}))
            event_specs.append(("context_menu", started + timedelta(minutes=10), {"question": 4, "source": "seed"}))

        if index % 7 == 0:
            fullscreen_exits = 1
            event_specs.append(("fullscreen_exit", started + timedelta(minutes=12), {"question": 5, "source": "seed"}))

        category_labels = {
            str(cat_id): category_name
            for (subj_name, category_name), cat_id in category_ids.items()
            if subj_name == subject_name
        }

        attempt_id = f"seed_attempt_{index:02d}"
        last_security_event_at = max((event_time for _, event_time, _ in event_specs), default=None)
        student_id = roster.get((section, student_name))
        student_email = conn.execute("SELECT email FROM students WHERE id=?", (student_id,)).fetchone()["email"] if student_id else None

        conn.execute(
            """INSERT INTO attempts (
                id, teacher_id, student_id, student_email, student_name, section, started_at, submitted_at, seed,
                score, total, percentage, grade10, category_scores, type_scores,
                answers_json, status, focus_departures, focus_returns, away_seconds,
                longest_away_seconds, blur_events, pagehide_events,
                context_menu_attempts, copy_attempts, cut_attempts, paste_attempts,
                shortcut_attempts, fullscreen_exits, last_security_event_at,
                questions_json, assessment_title, assessment_subject, category_labels_json, ui_language
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'submitted',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                attempt_id,
                teacher_id,
                student_id,
                student_email,
                student_name,
                section,
                now_iso(started),
                now_iso(submitted),
                9000 + index,
                score,
                float(total),
                percentage,
                grade10,
                json.dumps(category_scores, ensure_ascii=False),
                json.dumps(type_scores, ensure_ascii=False),
                json.dumps(answers_json, ensure_ascii=False),
                focus_departures,
                focus_returns,
                away_seconds,
                longest_away,
                blur_events,
                pagehide_events,
                context_menu_attempts,
                copy_attempts,
                0,
                paste_attempts,
                shortcut_attempts,
                fullscreen_exits,
                now_iso(last_security_event_at) if last_security_event_at else None,
                json.dumps(questions, ensure_ascii=False),
                f"Demo Assessment · {subject_name}",
                subject_name,
                json.dumps(category_labels, ensure_ascii=False),
                "es",
            ),
        )

        for event_type, occurred_at, detail in event_specs:
            conn.execute(
                "INSERT INTO integrity_events(attempt_id,event_type,occurred_at,detail_json) VALUES(?,?,?,?)",
                (attempt_id, event_type, now_iso(occurred_at), json.dumps(detail, ensure_ascii=False)),
            )

    return len(all_students)


def clean_demo(conn: sqlite3.Connection) -> None:
    attempt_ids = [row["id"] for row in conn.execute("SELECT id FROM attempts WHERE id LIKE 'seed_attempt_%'").fetchall()]
    if attempt_ids:
        placeholders = ",".join("?" for _ in attempt_ids)
        conn.execute(f"DELETE FROM integrity_events WHERE attempt_id IN ({placeholders})", attempt_ids)
        conn.execute(f"DELETE FROM attempts WHERE id IN ({placeholders})", attempt_ids)
    demo_exam_ids = [r["id"] for r in conn.execute("SELECT id FROM exams WHERE title LIKE 'SEED • %'").fetchall()]
    if demo_exam_ids:
        ph = ",".join("?" for _ in demo_exam_ids)
        version_ids = [r["id"] for r in conn.execute(f"SELECT id FROM exam_versions WHERE exam_id IN ({ph})", demo_exam_ids).fetchall()]
        if version_ids:
            vph = ",".join("?" for _ in version_ids)
            conn.execute(f"DELETE FROM exam_version_questions WHERE version_id IN ({vph})", version_ids)
            conn.execute(f"DELETE FROM student_exam_allocations WHERE version_id IN ({vph})", version_ids)
        conn.execute(f"DELETE FROM exam_assignments WHERE exam_id IN ({ph})", demo_exam_ids)
        conn.execute(f"DELETE FROM exam_versions WHERE exam_id IN ({ph})", demo_exam_ids)
        conn.execute(f"DELETE FROM exams WHERE id IN ({ph})", demo_exam_ids)
    conn.execute("DELETE FROM question_bank WHERE id LIKE 'seed_%'")
    student_count = conn.execute("SELECT COUNT(*) AS n FROM students WHERE student_code LIKE 'SEED-%'").fetchone()["n"]
    conn.execute("DELETE FROM students WHERE student_code LIKE 'SEED-%'")
    conn.commit()
    print(f"Removed {len(attempt_ids)} demo attempts, {student_count} demo students, and all seed_* questions.")
    print("Demo sections/subjects/categories were intentionally kept so manually added data remains safe.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Assessment Studio Universal with development data.")
    parser.add_argument("--clean", action="store_true", help="Remove generated seed_* questions/attempts and exit.")
    parser.add_argument("--no-results", action="store_true", help="Create subjects/categories/questions only; do not create student results.")
    parser.add_argument("--keep-settings", action="store_true", help="Do not switch the current test to the demo English subject.")
    args = parser.parse_args()

    with connect() as conn:
        ensure_schema(conn)

        if args.clean:
            clean_demo(conn)
            return

        create_beep_audio("seed_three_beeps.wav", 3)
        teacher_ids, admin_teacher_id = upsert_demo_teachers(conn)

        subject_ids: dict[str, int] = {}
        category_ids: dict[tuple[str, str], int] = {}

        for subject_spec in SUBJECTS:
            subject_id = get_or_create_subject(conn, subject_spec["name"], subject_spec["description"])
            subject_ids[subject_spec["name"]] = subject_id
            for order, (category_name, description) in enumerate(subject_spec["categories"], start=1):
                category_id = get_or_create_category(conn, subject_id, category_name, description, order)
                category_ids[(subject_spec["name"], category_name)] = category_id

        specs = demo_question_specs()
        question_count = 0
        for (subject_name, category_name), questions in specs.items():
            subject_id = subject_ids[subject_name]
            category_id = category_ids[(subject_name, category_name)]
            for spec in questions:
                upsert_question(conn, teacher_ids[subject_name], subject_id, category_id, spec)
                question_count += 1

        if not args.keep_settings:
            upsert_setting(conn, "institution_name", "Demo Institution")
            upsert_setting(conn, "assessment_title", "Universal Demo Assessment")
            upsert_setting(conn, "assessment_subtitle", "Development seed data for testing Assessment Studio Universal.")
            upsert_setting(conn, "listening_max_plays", "2")
            upsert_setting(conn, "current_subject_id", str(subject_ids["English"]))
            upsert_setting(conn, "student_access_mode", "accounts")
            upsert_setting(conn, "ui_language", "es")
            upsert_setting(conn, "student_rules_es", DEFAULT_STUDENT_RULES_ES)
            upsert_setting(conn, "student_rules_en", DEFAULT_STUDENT_RULES_EN)
            upsert_setting(conn, "rules_version", DEFAULT_RULES_VERSION)
            upsert_setting(conn, "require_rules_acknowledgment", "1")
            upsert_setting(conn, "rules_updated_at", now_iso())

        roster = upsert_demo_roster(conn)
        exam_count = seed_demo_exams(conn, subject_ids, teacher_ids)

        attempt_count = 0
        if not args.no_results:
            attempt_count = insert_demo_attempts(conn, subject_ids, category_ids, roster, teacher_ids)

        conn.commit()

        category_count = len(category_ids)
        print("\nAssessment Studio seed complete")
        print("-" * 38)
        print(f"Database:       {DB_PATH}")
        print(f"Subjects:       {len(subject_ids)}")
        print(f"Categories:     {category_count}")
        print(f"Questions:      {question_count}")
        print(f"Demo exams:     {exam_count} (2 versions each)")
        print(f"Sections:       {len(SECTIONS)} ({', '.join(SECTIONS)})")
        print(f"Students:       {len(roster)} registered accounts")
        print(f"Teacher users:  {len(DEMO_TEACHERS)} (1 admin + 3 teachers)")
        print(f"Demo results:   {attempt_count if not args.no_results else 0}")
        print("Demo login:     seed.a01@example.com / " + DEMO_PASSWORD)
        print("                 (all seed accounts use Demo1234)")
        print("Listening WAV:  static/audio/seed_three_beeps.wav")
        if not args.keep_settings:
            print("Current subject: English")
        print("\nTeacher logins:")
        print(f"  Admin:         seed.admin@assessment.local / {DEMO_ADMIN_PASSWORD}")
        print(f"  Mathematics:   seed.math@assessment.local / {DEMO_TEACHER_PASSWORD}")
        print(f"  Science:       seed.science@assessment.local / {DEMO_TEACHER_PASSWORD}")
        print(f"  English:       seed.english@assessment.local / {DEMO_TEACHER_PASSWORD}")
        print("Run the app with: python app.py")


if __name__ == "__main__":
    main()
