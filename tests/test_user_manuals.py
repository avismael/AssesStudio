import csv
import io
import json
import math
import re
from pathlib import Path

import app
from werkzeug.datastructures import FileStorage


ROOT = Path(app.__file__).parent
MANUAL_ROOT = ROOT / "userdirections"
EXAMPLES = MANUAL_ROOT / "examples"
QUESTION_HEADER = [
    "Asignatura", "Categoria", "Tipo", "Pregunta", "Opciones", "Respuesta", "Pares",
    "Orden", "Tolerancia", "SensibleMayusculas", "Script", "Audio", "FuenteAudio", "IdiomaVoz",
]
QUESTION_FILES = [
    "preguntas_todos_los_tipos.csv",
    "preguntas_multiple_choice.csv",
    "preguntas_true_false.csv",
    "preguntas_short_answer.csv",
    "preguntas_numeric.csv",
    "preguntas_order.csv",
    "preguntas_matching.csv",
    "preguntas_listening.csv",
]


def upload_for(path, payload=None):
    return FileStorage(
        stream=io.BytesIO(path.read_bytes() if payload is None else payload),
        filename=path.name,
        content_type="text/csv",
    )


def teacher_client(csrf_token="manual-test-token"):
    client = app.app.test_client()
    with app.get_db() as conn:
        teacher = conn.execute("SELECT id FROM teachers WHERE role='teacher' AND is_active=1 ORDER BY id LIMIT 1").fetchone()
    with client.session_transaction() as session:
        session.update(teacher_authenticated=True, teacher_id=teacher["id"], csrf_token=csrf_token)
    return client, teacher["id"]


def admin_client(csrf_token="manual-test-token"):
    client = app.app.test_client()
    with app.get_db() as conn:
        admin = conn.execute("SELECT id FROM teachers WHERE role='admin' AND is_active=1 ORDER BY id LIMIT 1").fetchone()
    with client.session_transaction() as session:
        session.update(teacher_authenticated=True, teacher_id=admin["id"], csrf_token=csrf_token)
    return client, admin["id"]


def general_catalog(conn, teacher_id=None):
    if teacher_id is None:
        teacher_id = conn.execute("SELECT id FROM teachers WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()["id"]
    return conn.execute(
        """SELECT subjects.id AS subject_id,categories.id AS category_id
           FROM subjects JOIN categories ON categories.subject_id=subjects.id AND categories.teacher_id=subjects.teacher_id
           WHERE subjects.name='General' AND categories.name='General'
             AND subjects.teacher_id=%s AND subjects.is_archived=0 AND categories.is_archived=0""",
        (teacher_id,)
    ).fetchone()


def test_every_example_passes_the_real_upload_reader():
    paths = sorted(EXAMPLES.glob("*.csv"))
    assert len(paths) == 9
    for path in paths:
        fields, rows = app.read_csv_upload(upload_for(path))
        assert rows, path.name
        if path.name.startswith("preguntas_"):
            assert fields == [app.normalize_csv_key(header) for header in QUESTION_HEADER]
        else:
            assert fields == ["nie", "nombre", "apellido", "correo"]


def test_upload_reader_supports_semicolon_utf8_bom_and_latin1():
    cases = [
        ("semicolon.csv", "\ufeffNIE;Nombre;Apellido;Correo\nU-1;José;Pérez;jose@example.edu\n".encode("utf-8")),
        ("latin1.csv", "NIE,Nombre,Apellido,Correo\nL-1,María,Peña,maria@example.edu\n".encode("latin-1")),
    ]
    for filename, payload in cases:
        fields, rows = app.read_csv_upload(upload_for(EXAMPLES / filename, payload))
        assert fields == ["nie", "nombre", "apellido", "correo"]
        assert len(rows) == 1
        assert rows[0]["correo"].endswith("@example.edu")


def test_student_example_has_valid_headers_and_rows():
    path = EXAMPLES / "estudiantes_importacion.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert reader.fieldnames == ["NIE", "Nombre", "Apellido", "Correo"]
    assert rows
    assert all(row["NIE"].strip() and row["Nombre"].strip() and row["Apellido"].strip() for row in rows)
    assert all(app.valid_email(row["Correo"]) for row in rows)
    assert len({row["NIE"] for row in rows}) == len(rows)
    assert len({app.normalize_email(row["Correo"]) for row in rows}) == len(rows)


def test_student_example_import_route_inserts_rows_and_archived_values_remain_unique():
    with app.get_db() as conn:
        stamp = app.now_iso()
        section_id = conn.execute(
            """INSERT INTO sections(name,description,is_archived,created_at,updated_at)
               VALUES('Manual CSV Students','Documentation integration test',0,%s,%s) RETURNING id""",
            (stamp, stamp),
        ).fetchone()["id"]
        conn.commit()

    client, _ = admin_client()
    response = client.post(
        "/teacher/students/import",
        data={
            "csrf_token": "manual-test-token",
            "section_id": str(section_id),
            "batch_password_mode": "manual",
            "batch_password": "ManualPass123",
            "must_change_password": "on",
            "csv_file": upload_for(EXAMPLES / "estudiantes_importacion.csv"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    with app.get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM students WHERE section_id=%s ORDER BY student_code", (section_id,)
        ).fetchall()
        assert [row["student_code"] for row in rows] == ["20260001", "20260002", "20260003"]
        assert all(row["must_change_password"] == 1 for row in rows)
        assert all(app.check_password_hash(row["password_hash"], "ManualPass123") for row in rows)
        conn.execute("UPDATE students SET is_archived=1 WHERE student_code='20260001'")
        conn.commit()

    archived_conflicts = (
        "NIE,Nombre,Apellido,Correo\n"
        "20260001,Nuevo,NIE,nuevo.nie@example.edu\n"
        "20269999,Nuevo,Correo,ana.martinez@example.edu\n"
    ).encode("utf-8")
    response = client.post(
        "/teacher/students/import",
        data={
            "csrf_token": "manual-test-token",
            "section_id": str(section_id),
            "batch_password_mode": "manual",
            "batch_password": "ManualPass123",
            "csv_file": upload_for(EXAMPLES / "archived-conflicts.csv", archived_conflicts),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    with app.get_db() as conn:
        assert conn.execute("SELECT COUNT(*) AS n FROM students WHERE student_code='20260001'").fetchone()["n"] == 1
        assert not conn.execute("SELECT 1 FROM students WHERE student_code='20269999'").fetchone()


def test_every_question_example_passes_the_real_csv_parser():
    seen_types = set()
    with app.get_db() as conn:
        catalog = general_catalog(conn)
        assert catalog is not None
        for filename in QUESTION_FILES:
            path = EXAMPLES / filename
            fields, rows = app.read_csv_upload(upload_for(path))
            assert fields == [app.normalize_csv_key(header) for header in QUESTION_HEADER]
            assert rows, filename
            for row in rows:
                values, missing_audio = app.question_values_from_csv(conn, row)
                assert values["subject_id"] == catalog["subject_id"]
                assert values["category_id"] == catalog["category_id"]
                assert missing_audio is False
                if values["type"] == "numeric":
                    answer = json.loads(values["answer_json"])
                    assert math.isfinite(answer["value"]) and math.isfinite(answer["tolerance"])
                seen_types.add(values["type"])
    assert seen_types == set(app.TYPE_LABELS)


def test_consolidated_question_example_imports_all_types_inactive_for_current_owner():
    client, teacher_id = teacher_client()
    path = EXAMPLES / "preguntas_todos_los_tipos.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        prompts = [row["Pregunta"] for row in csv.DictReader(handle)]
    response = client.post(
        "/teacher/questions/import",
        data={"csrf_token": "manual-test-token", "csv_file": upload_for(path)},
        content_type="multipart/form-data",
    )
    assert response.status_code == 302
    placeholders = ",".join("%s" for _ in prompts)
    with app.get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM question_bank WHERE teacher_id=%s AND prompt IN ({placeholders})",
            [teacher_id, *prompts],
        ).fetchall()
    assert len(rows) == 7
    assert {row["type"] for row in rows} == set(app.TYPE_LABELS)
    assert all(row["teacher_id"] == teacher_id and row["is_active"] == 0 for row in rows)
    assert all(app.listening_row_usable(row) for row in rows)


def test_inactive_non_archived_question_is_currently_selectable_into_version():
    client, teacher_id = teacher_client()
    with app.get_db() as conn:
        catalog = general_catalog(conn)
        stamp = app.now_iso()
        question_id = "manual_inactive_selection"
        conn.execute(
            """INSERT INTO question_bank
               (id,teacher_id,subject_id,category_id,type,prompt,data_json,answer_json,is_active,is_archived,created_at,updated_at)
               VALUES(%s,%s,%s,%s,'multiple_choice','Inactive selection contract',%s,%s,0,0,%s,%s)""",
            (question_id, teacher_id, catalog["subject_id"], catalog["category_id"],
             json.dumps({"choices": [["c1", "A"], ["c2", "B"]]}), json.dumps("c1"), stamp, stamp),
        )
        exam_id = conn.execute(
            """INSERT INTO exams(teacher_id,subject_id,title,description,is_published,is_archived,created_at,updated_at)
               VALUES(%s,%s,'Inactive selection test','',0,0,%s,%s) RETURNING id""",
            (teacher_id, catalog["subject_id"], stamp, stamp),
        ).fetchone()["id"]
        version_id = conn.execute(
            "INSERT INTO exam_versions(exam_id,name,is_active,created_at,updated_at) VALUES(%s,'A',1,%s,%s) RETURNING id",
            (exam_id, stamp, stamp),
        ).fetchone()["id"]
        conn.commit()

    selector = client.get(f"/teacher/exams/{exam_id}/versions/{version_id}/questions")
    assert selector.status_code == 200
    assert question_id in selector.get_data(as_text=True)
    response = client.post(
        f"/teacher/exams/{exam_id}/versions/{version_id}/questions",
        data={"csrf_token": "manual-test-token", "question_ids": question_id},
    )
    assert response.status_code == 302
    with app.get_db() as conn:
        selected = conn.execute(
            "SELECT 1 FROM exam_version_questions WHERE version_id=%s AND question_id=%s",
            (version_id, question_id),
        ).fetchone()
    assert selected is not None


def test_teacher_catalog_subject_cards_open_a_category_view():
    client, teacher_id = admin_client()
    with app.get_db() as conn:
        stamp = app.now_iso()
        subject_a = conn.execute(
            """INSERT INTO subjects(teacher_id,name,description,is_archived,created_at,updated_at)
               VALUES(%s,'Catalog Route Alpha','',0,%s,%s) RETURNING id""",
            (teacher_id, stamp, stamp),
        ).fetchone()["id"]
        subject_b = conn.execute(
            """INSERT INTO subjects(teacher_id,name,description,is_archived,created_at,updated_at)
               VALUES(%s,'Catalog Route Beta','',0,%s,%s) RETURNING id""",
            (teacher_id, stamp, stamp),
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO categories(teacher_id,subject_id,name,description,sort_order,is_archived,created_at,updated_at) VALUES(%s,%s,'Alpha Category','',0,0,%s,%s)",
            (teacher_id, subject_a, stamp, stamp),
        )
        conn.execute(
            "INSERT INTO categories(teacher_id,subject_id,name,description,sort_order,is_archived,created_at,updated_at) VALUES(%s,%s,'Beta Category','',0,0,%s,%s)",
            (teacher_id, subject_b, stamp, stamp),
        )
        conn.commit()

    index = client.get('/teacher/catalog')
    index_body = index.get_data(as_text=True)
    assert index.status_code == 200
    assert 'Catalog Route Alpha' in index_body
    assert 'data-open-subject-modal' in index_body
    assert f'data-url="/teacher/subjects/{subject_a}/edit"' in index_body
    assert 'Alpha Category' not in index_body

    response = client.get(f"/teacher/catalog/subject/{subject_b}")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Catalog Route Beta' in body
    assert f'data-url="/teacher/subjects/{subject_b}/edit"' in body
    assert 'Beta Category' in body
    assert 'Alpha Category' not in body


def test_manual_markdown_relative_links_resolve():
    markdown_files = [
        ROOT / "README.md",
        ROOT / "CHANGELOG_USER_MANUALS.md",
        ROOT / "docs" / "README.md",
        ROOT / "docs" / "14-glossary-governance-roadmap.md",
        *MANUAL_ROOT.rglob("*.md"),
    ]
    link_pattern = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")
    missing = []
    for document in markdown_files:
        for target in link_pattern.findall(document.read_text(encoding="utf-8")):
            clean_target = target.split("#", 1)[0]
            if not clean_target or "://" in clean_target or clean_target.startswith("mailto:"):
                continue
            if not (document.parent / clean_target).resolve().exists():
                missing.append(f"{document.relative_to(ROOT)} -> {target}")
    assert not missing, "Broken relative documentation links: " + ", ".join(missing)
