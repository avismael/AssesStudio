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
It requires DATABASE_URL and an Alembic-migrated PostgreSQL database. Audio is
written under AUDIO_DIR (static/audio by default).

Usage:
    python seed.py --confirm-development-database
    python seed.py --confirm-development-database --keep-settings
    python seed.py --confirm-development-database --no-results
    python seed.py --confirm-development-database --clean

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
import struct
import wave
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from database import close_pool, connection as database_connection
from policy_defaults import DEFAULT_RULES_VERSION, DEFAULT_STUDENT_RULES_EN, DEFAULT_STUDENT_RULES_ES

BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = Path(os.getenv("AUDIO_DIR", str(BASE_DIR / "static" / "audio")))

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


def connect():
    return database_connection()


def verify_schema(conn) -> None:
    """Refuse to seed databases that have not been migrated to the expected revision."""
    try:
        row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
    except Exception as exc:
        raise RuntimeError("Database schema is missing; run 'alembic upgrade head' before seed.py") from exc
    if not row or row["version_num"] != "20260902_0001":
        raise RuntimeError("Database schema is not current; run 'alembic upgrade head' before seed.py")

def upsert_demo_teachers(conn: Any) -> tuple[dict[str, int], int]:
    """Create demo teacher accounts and return subject->teacher ownership plus admin id."""
    stamp = now_iso()
    subject_owner: dict[str, int] = {}
    admin_id = 0
    for item in DEMO_TEACHERS:
        row = conn.execute("SELECT id FROM teachers WHERE email=%s ", (item["email"],)).fetchone()
        password_hash = generate_password_hash(item["password"])
        if row:
            teacher_id = int(row["id"])
            conn.execute(
                """UPDATE teachers SET full_name=%s,password_hash=%s,role=%s,is_active=1,must_change_password=0,updated_at=%s WHERE id=%s""",
                (item["name"], password_hash, item["role"], stamp, teacher_id),
            )
        else:
            teacher_id = conn.execute(
                """INSERT INTO teachers(full_name,email,password_hash,role,is_active,must_change_password,created_at,updated_at)
                   VALUES(%s,%s,%s,%s,1,0,%s,%s) RETURNING id""",
                (item["name"], item["email"], password_hash, item["role"], stamp, stamp),
            ).fetchone()["id"]
        if item.get("role") == "admin":
            admin_id = teacher_id
        if item.get("subject"):
            subject_owner[item["subject"]] = teacher_id
    return subject_owner, admin_id


def upsert_setting(conn: Any, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO app_settings(key,value) VALUES(%s,%s) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def get_or_create_subject(conn: Any, teacher_id: int | str, name: str | None = None, description: str | None = None) -> int:
    if description is None:
        description = str(name or "")
        name = str(teacher_id)
        row = conn.execute("SELECT id FROM teachers WHERE role='teacher' AND is_active=1 ORDER BY id LIMIT 1").fetchone()
        if not row:
            row = conn.execute("SELECT id FROM teachers WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()
        if not row:
            raise RuntimeError("A seed teacher is required before creating subjects")
        teacher_id = int(row["id"])
    stamp = now_iso()
    row = conn.execute("SELECT id FROM subjects WHERE teacher_id=%s AND name=%s ", (teacher_id, name)).fetchone()
    if row:
        conn.execute(
            "UPDATE subjects SET description=%s, is_archived=0, updated_at=%s WHERE id=%s AND teacher_id=%s",
            (description, stamp, row["id"], teacher_id),
        )
        return int(row["id"])
    row = conn.execute(
        "INSERT INTO subjects(teacher_id,name,description,is_archived,created_at,updated_at) VALUES(%s,%s,%s,0,%s,%s) RETURNING id",
        (teacher_id, name, description, stamp, stamp),
    ).fetchone()
    return int(row["id"])


def get_or_create_category(
    conn: Any,
    teacher_id: int,
    subject_id: int,
    name: str | None = None,
    description: str | None = None,
    sort_order: int | None = None,
) -> int:
    if sort_order is None:
        sort_order = int(description or 0)
        description = str(name or "")
        name = str(subject_id)
        subject_id = int(teacher_id)
        row = conn.execute("SELECT teacher_id FROM subjects WHERE id=%s", (subject_id,)).fetchone()
        if not row:
            raise RuntimeError("A valid subject is required before creating categories")
        teacher_id = int(row["teacher_id"])
    stamp = now_iso()
    row = conn.execute(
        "SELECT id FROM categories WHERE teacher_id=%s AND subject_id=%s AND name=%s ",
        (teacher_id, subject_id, name),
    ).fetchone()
    if row:
        conn.execute(
            "UPDATE categories SET description=%s, sort_order=%s, is_archived=0, updated_at=%s WHERE id=%s AND teacher_id=%s",
            (description, sort_order, stamp, row["id"], teacher_id),
        )
        return int(row["id"])
    row = conn.execute(
        """INSERT INTO categories(teacher_id,subject_id,name,description,sort_order,is_archived,created_at,updated_at)
           VALUES(%s,%s,%s,%s,%s,0,%s,%s) RETURNING id""",
        (teacher_id, subject_id, name, description, sort_order, stamp, stamp),
    ).fetchone()
    return int(row["id"])


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
    conn: Any,
    teacher_id: int,
    subject_id: int,
    category_id: int,
    spec: dict[str, Any],
) -> None:
    stamp = now_iso()
    conn.execute(
        """INSERT INTO question_bank
           (id,teacher_id,subject_id,category_id,type,prompt,data_json,answer_json,audio,script,is_active,is_archived,created_at,updated_at)
           VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,0,%s,%s)
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


def row_to_snapshot(row: dict[str, Any]) -> dict[str, Any]:
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


def fetch_version_questions(conn: Any, version_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """SELECT q.*, s.name AS subject_name, c.name AS category_name
           FROM exam_version_questions evq
           JOIN question_bank q ON q.id=evq.question_id
           JOIN subjects s ON s.id=q.subject_id
           JOIN categories c ON c.id=q.category_id
           WHERE evq.version_id=%s AND q.is_active=1 AND q.is_archived=0
           ORDER BY evq.position, q.id""",
        (version_id,),
    ).fetchall()
    return [row_to_snapshot(row) for row in rows]


def blank_type_scores() -> dict[str, dict[str, float]]:
    return {key: {"earned": 0.0, "total": 0.0} for key in TYPE_KEYS}


def upsert_demo_roster(conn: Any) -> dict[tuple[str, str], int]:
    """Create the 3 demo sections and 15 registered student accounts."""
    roster: dict[tuple[str, str], int] = {}
    stamp = now_iso()
    password_hash = generate_password_hash(DEMO_PASSWORD)
    for section_name, names in SECTIONS.items():
        row = conn.execute("SELECT id FROM sections WHERE name=%s ", (section_name,)).fetchone()
        if row:
            section_id = int(row["id"])
            conn.execute("UPDATE sections SET is_archived=0,updated_at=%s WHERE id=%s", (stamp, section_id))
        else:
            section_id = conn.execute(
                "INSERT INTO sections(name,description,is_archived,created_at,updated_at) VALUES(%s,%s,0,%s,%s) RETURNING id",
                (section_name, f"Demo section {section_name}", stamp, stamp),
            ).fetchone()["id"]
        for idx, full_name in enumerate(names, start=1):
            code = f"SEED-{section_name}-{idx:02d}"
            email = f"seed.{section_name.lower()}{idx:02d}@example.com"
            student = conn.execute(
                "SELECT id FROM students WHERE student_code=%s OR email=%s  OR (section_id=%s AND full_name=%s )",
                (code, email, section_id, full_name),
            ).fetchone()
            if student:
                student_id = int(student["id"])
                conn.execute(
                    """UPDATE students SET full_name=%s,section_id=%s,student_code=%s,email=%s,password_hash=%s,must_change_password=0,
                       password_updated_at=%s,notes=%s,is_active=1,updated_at=%s WHERE id=%s""",
                    (full_name, section_id, code, email, password_hash, stamp, "Demo student generated by seed.py", stamp, student_id),
                )
            else:
                student_id = conn.execute(
                    """INSERT INTO students(full_name,section_id,student_code,email,password_hash,must_change_password,password_updated_at,notes,is_active,created_at,updated_at)
                       VALUES(%s,%s,%s,%s,%s,0,%s,%s,1,%s,%s) RETURNING id""",
                    (full_name, section_id, code, email, password_hash, stamp, "Demo student generated by seed.py", stamp, stamp),
                ).fetchone()["id"]
            roster[(section_name, full_name)] = student_id
    return roster


def seed_demo_exams(
    conn: Any,
    subject_ids: dict[str, int],
    teacher_ids: dict[str, int],
) -> tuple[int, dict[tuple[str, str], dict[str, Any]]]:
    """Create three published demo exams, each with two versions and section assignments."""
    stamp = now_iso()
    section_rows = conn.execute("SELECT id,name FROM sections WHERE name IN ('A','B','C') AND is_archived=0 ORDER BY name").fetchall()
    definitions = [
        ("English", "SEED • English Review", "Two-version English demo exam assigned randomly."),
        ("Mathematics", "SEED • Mathematics Skills", "Reusable Mathematics exam with multiple versions."),
        ("Science", "SEED • Science Concepts", "Science demo exam for testing section assignments."),
    ]
    created = 0
    assignment_map: dict[tuple[str, str], dict[str, Any]] = {}
    for subject_name, title, description in definitions:
        subject_id = subject_ids[subject_name]
        teacher_id = teacher_ids[subject_name]
        row = conn.execute("SELECT id FROM exams WHERE title=%s AND teacher_id=%s", (title, teacher_id)).fetchone()
        if row:
            exam_id = int(row["id"])
            conn.execute("UPDATE exams SET teacher_id=%s,subject_id=%s,description=%s,is_published=1,is_archived=0,updated_at=%s WHERE id=%s",
                         (teacher_id, subject_id, description, stamp, exam_id))
        else:
            exam_id = conn.execute("INSERT INTO exams(teacher_id,subject_id,title,description,is_published,is_archived,created_at,updated_at) VALUES(%s,%s,%s,%s,1,0,%s,%s) RETURNING id",
                               (teacher_id, subject_id, title, description, stamp, stamp)).fetchone()["id"]
        qids = [r["id"] for r in conn.execute("SELECT id FROM question_bank WHERE teacher_id=%s AND subject_id=%s AND id LIKE %s AND is_archived=0 ORDER BY id", (teacher_id, subject_id, "seed_%")).fetchall()]
        if len(qids) < 2:
            continue
        version_ids = []
        for idx, name in enumerate(("A", "B")):
            vr = conn.execute("SELECT id FROM exam_versions WHERE exam_id=%s AND name=%s", (exam_id, name)).fetchone()
            if vr:
                version_id = int(vr["id"])
                conn.execute("UPDATE exam_versions SET is_active=1,updated_at=%s WHERE id=%s", (stamp, version_id))
            else:
                version_id = conn.execute("INSERT INTO exam_versions(exam_id,name,is_active,created_at,updated_at) VALUES(%s,%s,1,%s,%s) RETURNING id", (exam_id, name, stamp, stamp)).fetchone()["id"]
            version_ids.append(version_id)
            # Each version gets a different overlapping subset so grading/version behavior is easy to inspect.
            chosen = [qid for pos, qid in enumerate(qids) if (pos + idx) % 2 == 0]
            if len(chosen) < 2:
                chosen = qids[: min(4, len(qids))]
            conn.execute("DELETE FROM exam_version_questions WHERE version_id=%s", (version_id,))
            for position, qid in enumerate(chosen):
                conn.execute("INSERT INTO exam_version_questions(version_id,question_id,position) VALUES(%s,%s,%s)", (version_id, qid, position))
        for sec in section_rows:
            # English/Science use random versions; Mathematics demonstrates a fixed version in A and random in B/C.
            mode = "fixed" if subject_name == "Mathematics" and sec["name"] == "A" else "random"
            fixed = version_ids[0] if mode == "fixed" else None
            assignment_id = conn.execute("""INSERT INTO exam_assignments(exam_id,section_id,version_mode,fixed_version_id,is_active,created_at,updated_at)
                VALUES(%s,%s,%s,%s,1,%s,%s) ON CONFLICT(exam_id,section_id) DO UPDATE SET version_mode=excluded.version_mode,
                fixed_version_id=excluded.fixed_version_id,is_active=1,updated_at=excluded.updated_at RETURNING id""",
                (exam_id, sec["id"], mode, fixed, stamp, stamp)).fetchone()["id"]
            assignment_map[(subject_name, sec["name"])] = {
                "assignment_id": assignment_id,
                "exam_id": exam_id,
                "version_ids": version_ids,
                "fixed_version_id": fixed,
            }
        created += 1
    return created, assignment_map


def delete_seed_attempts(conn: Any) -> list[str]:
    attempt_ids = [row["id"] for row in conn.execute(
        "SELECT id FROM attempts WHERE id LIKE %s", ("seed_attempt_%",)
    ).fetchall()]
    if not attempt_ids:
        return []
    placeholders = ",".join("%s" for _ in attempt_ids)
    conn.execute(f"DELETE FROM attempt_penalties WHERE attempt_id IN ({placeholders})", attempt_ids)
    conn.execute(f"DELETE FROM integrity_events WHERE attempt_id IN ({placeholders})", attempt_ids)
    conn.execute(f"DELETE FROM attempts WHERE id IN ({placeholders})", attempt_ids)
    return attempt_ids


def insert_demo_attempts(
    conn: Any,
    subject_ids: dict[str, int],
    category_ids: dict[tuple[str, str], int],
    roster: dict[tuple[str, str], int],
    teacher_ids: dict[str, int],
    assignment_map: dict[tuple[str, str], dict[str, Any]],
) -> int:
    # Rebuild only generated attempts and their dependents on each run.
    delete_seed_attempts(conn)

    rng = random.Random(20260814)
    subject_names = ["English", "Mathematics", "Science"]
    all_students = [(section, name) for section, names in SECTIONS.items() for name in names]
    base_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0) - timedelta(days=2)

    for index, (section, student_name) in enumerate(all_students, start=1):
        subject_name = subject_names[(index - 1) % len(subject_names)]
        subject_id = subject_ids[subject_name]
        teacher_id = teacher_ids[subject_name]
        assignment = assignment_map[(subject_name, section)]
        version_id = assignment["fixed_version_id"] or assignment["version_ids"][(index - 1) % len(assignment["version_ids"])]
        questions = fetch_version_questions(conn, version_id)
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
        student_email = conn.execute("SELECT email FROM students WHERE id=%s", (student_id,)).fetchone()["email"] if student_id else None
        conn.execute(
            """INSERT INTO student_exam_allocations(assignment_id,student_id,version_id,allocated_at)
               VALUES(%s,%s,%s,%s) ON CONFLICT(assignment_id,student_id) DO UPDATE
               SET version_id=excluded.version_id""",
            (assignment["assignment_id"], student_id, version_id, now_iso(started)),
        )

        conn.execute(
            """INSERT INTO attempts (
                id, teacher_id, student_id, student_email, student_name, section, started_at, submitted_at, seed,
                score, total, percentage, grade10, category_scores, type_scores,
                answers_json, status, focus_departures, focus_returns, away_seconds,
                longest_away_seconds, blur_events, pagehide_events,
                context_menu_attempts, copy_attempts, cut_attempts, paste_attempts,
                shortcut_attempts, fullscreen_exits, last_security_event_at,
                questions_json, assessment_title, assessment_subject, category_labels_json, ui_language,
                exam_id, exam_version_id, assignment_id, exam_version_name
            ) VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,%s,
                'submitted',
                %s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s
            )""",
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
                assignment["exam_id"],
                version_id,
                assignment["assignment_id"],
                "A" if version_id == assignment["version_ids"][0] else "B",
            ),
        )

        for event_type, occurred_at, detail in event_specs:
            conn.execute(
                "INSERT INTO integrity_events(attempt_id,event_type,occurred_at,detail_json) VALUES(%s,%s,%s,%s)",
                (attempt_id, event_type, now_iso(occurred_at), json.dumps(detail, ensure_ascii=False)),
            )

    return len(all_students)


def clean_demo(conn: Any) -> None:
    attempt_ids = delete_seed_attempts(conn)
    demo_exam_ids = [r["id"] for r in conn.execute("SELECT id FROM exams WHERE title LIKE %s", ("SEED • %",)).fetchall()]
    if demo_exam_ids:
        ph = ",".join("%s" for _ in demo_exam_ids)
        version_ids = [r["id"] for r in conn.execute(f"SELECT id FROM exam_versions WHERE exam_id IN ({ph})", demo_exam_ids).fetchall()]
        if version_ids:
            vph = ",".join("%s" for _ in version_ids)
            conn.execute(f"DELETE FROM exam_version_questions WHERE version_id IN ({vph})", version_ids)
            conn.execute(f"DELETE FROM student_exam_allocations WHERE version_id IN ({vph})", version_ids)
        conn.execute(f"DELETE FROM exam_assignments WHERE exam_id IN ({ph})", demo_exam_ids)
        conn.execute(f"DELETE FROM exam_versions WHERE exam_id IN ({ph})", demo_exam_ids)
        conn.execute(f"DELETE FROM exams WHERE id IN ({ph})", demo_exam_ids)
    conn.execute("DELETE FROM question_bank WHERE id LIKE %s", ("seed_%",))
    student_count = conn.execute("SELECT COUNT(*) AS n FROM students WHERE student_code LIKE %s", ("SEED-%",)).fetchone()["n"]
    conn.execute("DELETE FROM students WHERE student_code LIKE %s", ("SEED-%",))
    conn.commit()
    print(f"Removed {len(attempt_ids)} demo attempts, {student_count} demo students, and all seed_* questions.")
    print("Demo sections/subjects/categories were intentionally kept so manually added data remains safe.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Assessment Studio Universal with development data.")
    parser.add_argument(
        "--confirm-development-database",
        action="store_true",
        help="Required confirmation that DATABASE_URL targets a disposable development/test database.",
    )
    parser.add_argument("--clean", action="store_true", help="Remove generated seed_* questions/attempts and exit.")
    parser.add_argument("--no-results", action="store_true", help="Create subjects/categories/questions only; do not create student results.")
    parser.add_argument("--keep-settings", action="store_true", help="Do not switch the current test to the demo English subject.")
    args = parser.parse_args()
    if not args.confirm_development_database:
        parser.error("--confirm-development-database is required because seed.py mutates PostgreSQL and writes demo audio")

    with connect() as conn:
        verify_schema(conn)

        if args.clean:
            clean_demo(conn)
            return

        create_beep_audio("seed_three_beeps.wav", 3)
        teacher_ids, admin_teacher_id = upsert_demo_teachers(conn)

        subject_ids: dict[str, int] = {}
        category_ids: dict[tuple[str, str], int] = {}

        for subject_spec in SUBJECTS:
            owner_teacher_id = teacher_ids[subject_spec["name"]]
            subject_id = get_or_create_subject(conn, owner_teacher_id, subject_spec["name"], subject_spec["description"])
            subject_ids[subject_spec["name"]] = subject_id
            for order, (category_name, description) in enumerate(subject_spec["categories"], start=1):
                category_id = get_or_create_category(conn, owner_teacher_id, subject_id, category_name, description, order)
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
        exam_count, assignment_map = seed_demo_exams(conn, subject_ids, teacher_ids)

        attempt_count = 0
        if not args.no_results:
            attempt_count = insert_demo_attempts(conn, subject_ids, category_ids, roster, teacher_ids, assignment_map)

        conn.commit()

        category_count = len(category_ids)
        print("\nAssessment Studio seed complete")
        print("-" * 38)
        print(f"Database:       {conn.info.dbname}")
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
        print(f"Listening WAV:  {AUDIO_DIR / 'seed_three_beeps.wav'}")
        if not args.keep_settings:
            print("Current subject: English")
        print("\nTeacher logins:")
        print(f"  Admin:         seed.admin@assessment.local / {DEMO_ADMIN_PASSWORD}")
        print(f"  Mathematics:   seed.math@assessment.local / {DEMO_TEACHER_PASSWORD}")
        print(f"  Science:       seed.science@assessment.local / {DEMO_TEACHER_PASSWORD}")
        print(f"  English:       seed.english@assessment.local / {DEMO_TEACHER_PASSWORD}")
        print("Run the app with: python app.py")


if __name__ == "__main__":
    try:
        main()
    finally:
        close_pool()
