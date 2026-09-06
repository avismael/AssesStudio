from flask import abort, redirect, render_template, request, url_for
from psycopg import IntegrityError

from app import (
    app,
    category_teacher_clause,
    current_teacher_id,
    flash_ui,
    get_db,
    now_iso,
    setting,
    subject_teacher_clause,
    teacher_required,
    verify_csrf,
)


@app.get("/teacher/catalog")
@teacher_required
def teacher_catalog():
    teacher_id = current_teacher_id()
    with get_db() as conn:
        subject_filter, subject_params = subject_teacher_clause(conn, "s", teacher_id)
        category_filter, category_params = category_teacher_clause(conn, "c", teacher_id)
        subjects = conn.execute(
            f"""SELECT s.*, COUNT(DISTINCT c.id) AS category_count, COUNT(DISTINCT q.id) AS question_count
               FROM subjects s
               LEFT JOIN categories c ON c.subject_id=s.id AND c.is_archived=0{category_filter}
               LEFT JOIN question_bank q ON q.subject_id=s.id AND q.teacher_id=%s AND q.is_archived=0
               WHERE s.is_archived=0{subject_filter} GROUP BY s.id ORDER BY s.name""",
            tuple(category_params + [teacher_id] + subject_params),
        ).fetchall()
    return render_template("teacher/catalog/index.html", subjects=subjects, selected_subject=None, categories=[])


@app.get("/teacher/catalog/subject/<int:subject_id>")
@teacher_required
def teacher_catalog_subject(subject_id):
    teacher_id = current_teacher_id()
    with get_db() as conn:
        subject_filter, subject_params = subject_teacher_clause(conn, "s", teacher_id)
        category_filter, category_params = category_teacher_clause(conn, "c", teacher_id)
        subjects = conn.execute(
            f"""SELECT s.*, COUNT(DISTINCT c.id) AS category_count, COUNT(DISTINCT q.id) AS question_count
               FROM subjects s
               LEFT JOIN categories c ON c.subject_id=s.id AND c.is_archived=0{category_filter}
               LEFT JOIN question_bank q ON q.subject_id=s.id AND q.teacher_id=%s AND q.is_archived=0
               WHERE s.is_archived=0{subject_filter} GROUP BY s.id ORDER BY s.name""",
            tuple(category_params + [teacher_id] + subject_params),
        ).fetchall()
        selected_subject = next((row for row in subjects if row["id"] == subject_id), None)
        if selected_subject is None:
            abort(404)
        categories = conn.execute(
            f"""SELECT c.*, COUNT(q.id) AS question_count
               FROM categories c
               LEFT JOIN question_bank q ON q.category_id=c.id AND q.teacher_id=%s AND q.is_archived=0
               WHERE c.is_archived=0 AND c.subject_id=%s{category_filter}
               GROUP BY c.id ORDER BY c.sort_order,c.name""",
            tuple([teacher_id, selected_subject["id"]] + category_params),
        ).fetchall()
    return render_template("teacher/catalog/index.html", subjects=subjects, categories=categories, selected_subject=selected_subject)


@app.post("/teacher/subjects/new")
@teacher_required
def teacher_subject_new():
    verify_csrf()
    name = " ".join(request.form.get("name", "").strip().split())
    description = request.form.get("description", "").strip()
    if len(name) < 2:
        flash_ui("Write a subject name.", "error")
        return redirect(url_for("teacher_catalog"))
    timestamp = now_iso()
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO subjects(teacher_id,name,description,is_archived,created_at,updated_at) VALUES(%s,%s,%s,0,%s,%s)",
                (current_teacher_id(), name, description, timestamp, timestamp),
            )
            conn.commit()
        flash_ui("Subject created.", "success")
    except IntegrityError:
        flash_ui("A subject with that name already exists.", "error")
    return redirect(url_for("teacher_catalog"))


@app.post("/teacher/subjects/<int:subject_id>/edit")
@teacher_required
def teacher_subject_edit(subject_id):
    verify_csrf()
    name = " ".join(request.form.get("name", "").strip().split())
    description = request.form.get("description", "").strip()
    if len(name) < 2:
        flash_ui("Write a subject name.", "error")
        return redirect(url_for("teacher_catalog"))
    try:
        with get_db() as conn:
            conn.execute(
                "UPDATE subjects SET name=%s,description=%s,updated_at=%s WHERE id=%s AND teacher_id=%s AND is_archived=0",
                (name, description, now_iso(), subject_id, current_teacher_id()),
            )
            conn.commit()
        flash_ui("Subject updated.", "success")
    except IntegrityError:
        flash_ui("A subject with that name already exists.", "error")
    return redirect(url_for("teacher_catalog"))


@app.post("/teacher/subjects/<int:subject_id>/archive")
@teacher_required
def teacher_subject_archive(subject_id):
    verify_csrf()
    with get_db() as conn:
        subject = conn.execute(
            "SELECT id,name FROM subjects WHERE id=%s AND teacher_id=%s AND is_archived=0",
            (subject_id, current_teacher_id()),
        ).fetchone()
        if not subject:
            abort(404)
        remaining = conn.execute(
            "SELECT id FROM subjects WHERE teacher_id=%s AND is_archived=0 AND id<>%s ORDER BY name",
            (current_teacher_id(), subject_id),
        ).fetchall()
        if not remaining:
            flash_ui("At least one active subject must remain.", "error")
            return redirect(url_for("teacher_catalog"))
        conn.execute("UPDATE subjects SET is_archived=1,updated_at=%s WHERE id=%s AND teacher_id=%s", (now_iso(), subject_id, current_teacher_id()))
        conn.execute("UPDATE categories SET is_archived=1,updated_at=%s WHERE subject_id=%s AND teacher_id=%s", (now_iso(), subject_id, current_teacher_id()))
        conn.execute("UPDATE question_bank SET is_active=0,is_archived=1,updated_at=%s WHERE subject_id=%s AND teacher_id=%s", (now_iso(), subject_id, current_teacher_id()))
        current = setting(conn, "current_subject_id")
        if str(current) == str(subject_id):
            conn.execute("UPDATE app_settings SET value=%s WHERE key='current_subject_id'", (str(remaining[0]["id"]),))
        conn.commit()
    flash_ui("Subject archived.", "success")
    return redirect(url_for("teacher_catalog"))


@app.post("/teacher/categories/new")
@teacher_required
def teacher_category_new():
    verify_csrf()
    try:
        subject_id = int(request.form.get("subject_id", "0"))
        sort_order = int(request.form.get("sort_order", "0") or 0)
    except ValueError:
        flash_ui("Choose a valid subject.", "error")
        return redirect(url_for("teacher_catalog"))
    name = " ".join(request.form.get("name", "").strip().split())
    description = request.form.get("description", "").strip()
    if len(name) < 2:
        flash_ui("Write a category name.", "error")
        return redirect(url_for("teacher_catalog"))
    timestamp = now_iso()
    try:
        with get_db() as conn:
            exists = conn.execute("SELECT 1 FROM subjects WHERE id=%s AND teacher_id=%s AND is_archived=0", (subject_id, current_teacher_id())).fetchone()
            if not exists:
                flash_ui("Selected subject does not exist.", "error")
                return redirect(url_for("teacher_catalog"))
            conn.execute(
                "INSERT INTO categories(teacher_id,subject_id,name,description,sort_order,is_archived,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,0,%s,%s)",
                (current_teacher_id(), subject_id, name, description, sort_order, timestamp, timestamp),
            )
            conn.commit()
        flash_ui("Category created.", "success")
    except IntegrityError:
        flash_ui("That category already exists in this subject.", "error")
    return redirect(url_for("teacher_catalog"))


@app.post("/teacher/categories/<int:category_id>/edit")
@teacher_required
def teacher_category_edit(category_id):
    verify_csrf()
    try:
        subject_id = int(request.form.get("subject_id", "0"))
        sort_order = int(request.form.get("sort_order", "0") or 0)
    except ValueError:
        flash_ui("Choose a valid subject.", "error")
        return redirect(url_for("teacher_catalog"))
    name = " ".join(request.form.get("name", "").strip().split())
    description = request.form.get("description", "").strip()
    if len(name) < 2:
        flash_ui("Write a category name.", "error")
        return redirect(url_for("teacher_catalog"))
    try:
        with get_db() as conn:
            exists = conn.execute("SELECT 1 FROM subjects WHERE id=%s AND teacher_id=%s AND is_archived=0", (subject_id, current_teacher_id())).fetchone()
            if not exists:
                flash_ui("Choose a valid subject.", "error")
                return redirect(url_for("teacher_catalog"))
            conn.execute(
                "UPDATE categories SET teacher_id=%s,subject_id=%s,name=%s,description=%s,sort_order=%s,updated_at=%s WHERE id=%s AND teacher_id=%s AND is_archived=0",
                (current_teacher_id(), subject_id, name, description, sort_order, now_iso(), category_id, current_teacher_id()),
            )
            conn.execute("UPDATE question_bank SET subject_id=%s,updated_at=%s WHERE category_id=%s AND teacher_id=%s", (subject_id, now_iso(), category_id, current_teacher_id()))
            conn.commit()
        flash_ui("Category updated.", "success")
    except IntegrityError:
        flash_ui("That category already exists in this subject.", "error")
    return redirect(url_for("teacher_catalog"))


@app.post("/teacher/categories/<int:category_id>/archive")
@teacher_required
def teacher_category_archive(category_id):
    verify_csrf()
    with get_db() as conn:
        category = conn.execute("SELECT id FROM categories WHERE id=%s AND teacher_id=%s AND is_archived=0", (category_id, current_teacher_id())).fetchone()
        if not category:
            abort(404)
        conn.execute("UPDATE categories SET is_archived=1,updated_at=%s WHERE id=%s AND teacher_id=%s", (now_iso(), category_id, current_teacher_id()))
        conn.execute("UPDATE question_bank SET is_active=0,is_archived=1,updated_at=%s WHERE category_id=%s AND teacher_id=%s", (now_iso(), category_id, current_teacher_id()))
        conn.commit()
    flash_ui("Category archived.", "success")
    return redirect(url_for("teacher_catalog"))
