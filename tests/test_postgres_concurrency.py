from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import conftest
import app
import pytest
from psycopg.conninfo import conninfo_to_dict


def test_effective_database_name_rejects_conninfo_override():
    malicious_url = "postgresql://user:pass@localhost/safe_test?dbname=production"
    effective_name = conninfo_to_dict(malicious_url)["dbname"]
    assert effective_name == "production"
    with pytest.raises(pytest.UsageError, match="Effective PostgreSQL"):
        conftest.require_test_database_name(effective_name, "Effective PostgreSQL")
    source = Path(conftest.__file__).read_text(encoding="utf-8")
    assert source.index('require_test_database_name(connection.info.dbname') < source.index(
        'connection.execute("DROP SCHEMA public CASCADE")'
    )


def test_postgresql_migration_and_health_contracts():
    client = app.app.test_client()
    assert client.get("/health/live").get_json() == {"status": "ok"}
    assert client.get("/health/ready").get_json() == {"status": "ok"}
    with app.get_db() as conn:
        assert conn.execute("SELECT version_num FROM alembic_version").fetchone()["version_num"] == "20260902_0001"
        assert conn.execute("SELECT extname FROM pg_extension WHERE extname='citext'").fetchone()
        assert conn.execute(
            "SELECT indexname FROM pg_indexes WHERE indexname='idx_attempt_once_per_assignment'"
        ).fetchone()


def test_health_ready_returns_503_when_pool_is_unavailable(monkeypatch):
    def unavailable_db():
        raise app.PoolTimeout("test pool exhaustion")

    monkeypatch.setattr(app, "get_db", unavailable_db)
    response = app.app.test_client().get("/health/ready")
    assert response.status_code == 503
    assert response.get_json() == {"status": "unavailable"}


def _student_client(student_id, attempt_id=None):
    client = app.app.test_client()
    with app.get_db() as conn:
        rules = app.current_rules(conn)
    with client.session_transaction() as session:
        session.update(
            student_authenticated=True,
            student_id=student_id,
            csrf_token="concurrency-token",
            rules_acknowledged_version=rules["version"],
            rules_acknowledged_at=app.now_iso(),
        )
        if attempt_id:
            session["attempt_id"] = attempt_id
    return client


def _create_concurrency_exam():
    stamp = app.now_iso()
    with app.get_db() as conn:
        teacher_id = conn.execute("SELECT id FROM teachers WHERE role='teacher' AND is_active=1 ORDER BY id LIMIT 1").fetchone()["id"]
        conn.execute("INSERT INTO sections(id,name,is_archived,created_at,updated_at) VALUES(901,'Concurrency',0,%s,%s)", (stamp, stamp))
        for student_id in range(901, 905):
            conn.execute(
                """INSERT INTO students
                   (id,full_name,section_id,student_code,email,password_hash,must_change_password,is_active,is_archived,created_at,updated_at)
                   VALUES(%s,%s,901,%s,%s,%s,0,1,0,%s,%s)""",
                (student_id, f"Concurrent Student {student_id}", f"CON-{student_id}",
                 f"concurrent-{student_id}@example.invalid", app.generate_password_hash("Student123"), stamp, stamp),
            )
        conn.execute("INSERT INTO subjects(id,teacher_id,name,is_archived,created_at,updated_at) VALUES(901,%s,'Concurrency Subject',0,%s,%s)", (teacher_id, stamp, stamp))
        conn.execute("INSERT INTO categories(id,teacher_id,subject_id,name,sort_order,is_archived,created_at,updated_at) VALUES(901,%s,901,'Concurrency Category',0,0,%s,%s)", (teacher_id, stamp, stamp))
        conn.execute(
            """INSERT INTO question_bank
               (id,teacher_id,subject_id,category_id,type,prompt,data_json,answer_json,is_active,is_archived,created_at,updated_at)
               VALUES('q_concurrency',%s,901,901,'multiple_choice','Choose A','{"choices":[["a","A"],["b","B"]]}','"a"',1,0,%s,%s)""",
            (teacher_id, stamp, stamp),
        )
        exam_id = conn.execute(
            """INSERT INTO exams(teacher_id,subject_id,title,is_published,is_archived,created_at,updated_at)
               VALUES(%s,901,'Concurrency Exam',1,0,%s,%s) RETURNING id""",
            (teacher_id, stamp, stamp),
        ).fetchone()["id"]
        version_ids = []
        for name in ("A", "B"):
            version_id = conn.execute(
                "INSERT INTO exam_versions(exam_id,name,is_active,created_at,updated_at) VALUES(%s,%s,1,%s,%s) RETURNING id",
                (exam_id, name, stamp, stamp),
            ).fetchone()["id"]
            version_ids.append(version_id)
            conn.execute(
                "INSERT INTO exam_version_questions(version_id,question_id,position) VALUES(%s,'q_concurrency',0)",
                (version_id,),
            )
        assignment_id = conn.execute(
            """INSERT INTO exam_assignments(exam_id,section_id,version_mode,is_active,created_at,updated_at)
               VALUES(%s,901,'random',1,%s,%s) RETURNING id""",
            (exam_id, stamp, stamp),
        ).fetchone()["id"]
    return assignment_id, version_ids


def test_concurrent_start_is_stable_unique_and_balanced():
    assignment_id, version_ids = _create_concurrency_exam()
    student_ids = [901, 901, 902, 903, 904]
    clients = [_student_client(student_id) for student_id in student_ids]

    with ThreadPoolExecutor(max_workers=len(clients)) as executor:
        responses = list(executor.map(
            lambda client: client.post(
                f"/student/exams/{assignment_id}/start",
                data={"csrf_token": "concurrency-token"},
            ),
            clients,
        ))

    assert all(response.status_code == 302 for response in responses)
    with app.get_db() as conn:
        attempts = conn.execute(
            "SELECT student_id,exam_version_id FROM attempts WHERE assignment_id=%s ORDER BY student_id",
            (assignment_id,),
        ).fetchall()
        allocations = conn.execute(
            "SELECT student_id,version_id FROM student_exam_allocations WHERE assignment_id=%s ORDER BY student_id",
            (assignment_id,),
        ).fetchall()
    assert len(attempts) == len(allocations) == 4
    assert [(row["student_id"], row["exam_version_id"]) for row in attempts] == [
        (row["student_id"], row["version_id"]) for row in allocations
    ]
    counts = [sum(row["version_id"] == version_id for row in allocations) for version_id in version_ids]
    assert max(counts) - min(counts) <= 1


def test_concurrent_submit_is_idempotent():
    with app.get_db() as conn:
        attempt = conn.execute(
            "SELECT id,student_id FROM attempts WHERE student_id=901 AND status='in_progress' ORDER BY started_at LIMIT 1"
        ).fetchone()
    if not attempt:
        assignment_id, _ = _create_concurrency_exam()
        client = _student_client(901)
        client.post(
            f"/student/exams/{assignment_id}/start",
            data={"csrf_token": "concurrency-token"},
        )
        with app.get_db() as conn:
            attempt = conn.execute(
                "SELECT id,student_id FROM attempts WHERE student_id=901 AND status='in_progress' ORDER BY started_at LIMIT 1"
            ).fetchone()
    clients = [_student_client(attempt["student_id"], attempt["id"]) for _ in range(2)]

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(
            lambda client: client.post(
                "/submit",
                data={"csrf_token": "concurrency-token", "q_q_concurrency": "a"},
            ),
            clients,
        ))

    assert all(response.status_code == 302 for response in responses)
    with app.get_db() as conn:
        submitted = conn.execute("SELECT status,score,total FROM attempts WHERE id=%s", (attempt["id"],)).fetchone()
    assert submitted == {"status": "submitted", "score": 1.0, "total": 1.0}


def test_concurrent_penalties_cannot_exceed_raw_grade():
    stamp = app.now_iso()
    with app.get_db() as conn:
        teacher_id = conn.execute("SELECT id FROM teachers WHERE role='teacher' AND is_active=1 ORDER BY id LIMIT 1").fetchone()["id"]
        subject_id = conn.execute("SELECT id FROM subjects ORDER BY id LIMIT 1").fetchone()["id"]
        conn.execute("INSERT INTO sections(id,name,is_archived,created_at,updated_at) VALUES(920,'Penalty Concurrency',0,%s,%s)", (stamp, stamp))
        conn.execute(
            """INSERT INTO students
               (id,full_name,section_id,student_code,email,password_hash,must_change_password,is_active,is_archived,created_at,updated_at)
               VALUES(920,'Penalty Student',920,'PEN-920','penalty-920@example.invalid',%s,0,1,0,%s,%s)""",
            (app.generate_password_hash("Student123"), stamp, stamp),
        )
        exam_id = conn.execute(
            """INSERT INTO exams(teacher_id,subject_id,title,is_published,is_archived,created_at,updated_at)
               VALUES(%s,%s,'Penalty Concurrency Exam',1,0,%s,%s) RETURNING id""",
            (teacher_id, subject_id, stamp, stamp),
        ).fetchone()["id"]
        version_id = conn.execute(
            "INSERT INTO exam_versions(exam_id,name,is_active,created_at,updated_at) VALUES(%s,'A',1,%s,%s) RETURNING id",
            (exam_id, stamp, stamp),
        ).fetchone()["id"]
        assignment_id = conn.execute(
            """INSERT INTO exam_assignments(exam_id,section_id,version_mode,fixed_version_id,is_active,created_at,updated_at)
               VALUES(%s,920,'fixed',%s,1,%s,%s) RETURNING id""",
            (exam_id, version_id, stamp, stamp),
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO student_exam_allocations(assignment_id,student_id,version_id,allocated_at) VALUES(%s,920,%s,%s)",
            (assignment_id, version_id, stamp),
        )
        conn.execute(
            """INSERT INTO attempts
               (id,teacher_id,student_id,student_name,section,started_at,submitted_at,seed,status,grade10,
                questions_json,exam_id,exam_version_id,assignment_id,exam_version_name)
               VALUES('penalty-concurrency',%s,920,'Penalty Student','Penalty Concurrency',%s,%s,920,'submitted',5,
                      '[]',%s,%s,%s,'A')""",
            (teacher_id, stamp, stamp, exam_id, version_id, assignment_id),
        )
        conn.commit()

    clients = [app.app.test_client(), app.app.test_client()]
    for client in clients:
        with client.session_transaction() as session:
            session.update(teacher_authenticated=True, teacher_id=teacher_id, csrf_token="penalty-race-token")
    barrier = Barrier(2)

    def apply_penalty(index):
        barrier.wait()
        return clients[index].post(
            "/teacher/results/penalty-concurrency/penalties",
            data={"csrf_token": "penalty-race-token", "points": "4", "reason": f"Concurrent reason {index}"},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(apply_penalty, range(2)))

    assert all(response.status_code == 302 for response in responses)
    flash_categories = []
    for client in clients:
        with client.session_transaction() as session:
            flash_categories.extend(category for category, _ in session.get("_flashes", []))
    assert sorted(flash_categories) == ["error", "success"]
    with app.get_db() as conn:
        penalties = conn.execute(
            "SELECT points FROM attempt_penalties WHERE attempt_id='penalty-concurrency' AND is_active=1"
        ).fetchall()
        total = app.active_penalty_total(conn, "penalty-concurrency")
    assert len(penalties) == 1
    assert total == 4.0 and total <= 5.0
