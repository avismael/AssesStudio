from collections import defaultdict
import re

from flask import abort, redirect, render_template, request, url_for
from psycopg import IntegrityError
from werkzeug.security import generate_password_hash

from app import (
    admin_required,
    app,
    clean_name,
    csv_cell,
    csv_download,
    flash_ui,
    generate_temp_password,
    get_db,
    get_ui_language,
    has_csv_column,
    now_iso,
    normalize_email,
    read_csv_upload,
    valid_email,
    valid_student_password,
    verify_csrf,
)


def teacher_students_return_filters(source=None):
    source = source or request.values
    return {
        "q": clean_name(source.get("return_q", ""), 100),
        "section": str(source.get("return_section", "")).strip(),
    }


def render_teacher_students(credentials=None, bulk_credentials=None, import_summary=None, filters_override=None, selected_section_id=None):
    if filters_override is None and request.method == "GET":
        query = clean_name(request.args.get("q", ""), 100)
        section_filter = request.args.get("section", "").strip()
    else:
        filters = filters_override or {}
        query = clean_name(filters.get("q", ""), 100)
        section_filter = str(filters.get("section", "")).strip()
    if selected_section_id is not None:
        try:
            selected_section_id = int(selected_section_id)
        except ValueError:
            selected_section_id = None
    where = ["sec.is_archived=0", "COALESCE(st.is_archived,0)=0"]
    params = []
    if query:
        where.append("(st.full_name ILIKE %s OR COALESCE(st.student_code,'') ILIKE %s OR sec.name ILIKE %s)")
        like = f"%{query}%"
        params.extend([like, like, like])
    if selected_section_id:
        where.append("st.section_id=%s")
        params.append(selected_section_id)
    if section_filter:
        try:
            where.append("st.section_id=%s")
            params.append(int(section_filter))
        except ValueError:
            pass
    with get_db() as conn:
        sections = conn.execute(
            """SELECT sec.*, COUNT(st.id) AS student_count,
                      SUM(CASE WHEN st.is_active=1 THEN 1 ELSE 0 END) AS active_count
               FROM sections sec LEFT JOIN students st ON st.section_id=sec.id AND COALESCE(st.is_archived,0)=0
               WHERE sec.is_archived=0 GROUP BY sec.id ORDER BY sec.name"""
        ).fetchall()
        archived_sections = conn.execute(
            """SELECT sec.*, COUNT(st.id) AS student_count,
                      SUM(CASE WHEN st.is_active=1 THEN 1 ELSE 0 END) AS active_count
               FROM sections sec LEFT JOIN students st ON st.section_id=sec.id
               WHERE sec.is_archived=1 GROUP BY sec.id ORDER BY sec.name"""
        ).fetchall()
        students = conn.execute(
            f"""SELECT st.*, sec.name AS section_name
                FROM students st JOIN sections sec ON sec.id=st.section_id
                WHERE {' AND '.join(where)} ORDER BY sec.name, st.full_name""",
            params,
        ).fetchall()
        archived_students = []
        if selected_section_id:
            archived_students = conn.execute(
                """SELECT st.*, sec.name AS section_name
                   FROM students st JOIN sections sec ON sec.id=st.section_id
                   WHERE st.section_id=%s AND COALESCE(st.is_archived,0)=1
                   ORDER BY st.full_name""",
                (selected_section_id,),
            ).fetchall()
        active_students = conn.execute("SELECT COUNT(*) AS n FROM students WHERE is_active=1 AND COALESCE(is_archived,0)=0").fetchone()["n"]
        inactive_students = conn.execute("SELECT COUNT(*) AS n FROM students WHERE is_active=0 AND COALESCE(is_archived,0)=0").fetchone()["n"]
    students_by_section = defaultdict(list)
    for student in students:
        students_by_section[int(student["section_id"])].append(student)
    selected_section = None
    selected_section_is_archived = False
    if selected_section_id:
        selected_section = next((sec for sec in sections if int(sec["id"]) == selected_section_id), None)
        if not selected_section:
            selected_section = next((sec for sec in archived_sections if int(sec["id"]) == selected_section_id), None)
            selected_section_is_archived = bool(selected_section)
        elif int(selected_section["is_archived"] or 0):
            selected_section_is_archived = True
    return render_template(
        "teacher/students/index.html", students=students, sections=sections,
        active_students=active_students, inactive_students=inactive_students,
        students_by_section=students_by_section,
        archived_sections=archived_sections,
        archived_students=archived_students,
        filters={"q": query, "section": str(selected_section_id or section_filter or "")},
        selected_section=selected_section,
        selected_section_is_archived=selected_section_is_archived,
        selected_section_id=selected_section_id,
        credentials=credentials, bulk_credentials=bulk_credentials, import_summary=import_summary,
    )


@app.get("/teacher/students")
@admin_required
def teacher_students():
    return render_teacher_students()


@app.get("/teacher/students/section/<int:section_id>")
@admin_required
def teacher_students_section(section_id):
    return render_teacher_students(selected_section_id=section_id)


@app.get("/teacher/students/import/template")
@admin_required
def teacher_students_import_template():
    english = get_ui_language() == "en"
    return csv_download(
        "student_import_template.csv" if english else "plantilla_estudiantes.csv",
        ["Student ID", "First name", "Last name", "Email"] if english else ["NIE", "Nombre", "Apellido", "Correo"],
        [
            ["20260001", "Ana", "Martínez", "ana.martinez@clases.edu"],
            ["20260002", "Carlos", "López", ""],
        ],
    )


@app.post("/teacher/students/import")
@admin_required
def teacher_students_import():
    verify_csrf()
    try:
        section_id = int(request.form.get("section_id", "0"))
    except ValueError:
        section_id = 0
    generate_email = bool(request.form.get("generate_email_from_nie"))
    domain = request.form.get("email_domain", "clases.edu").strip().lower().lstrip("@")[:190]
    password_mode = request.form.get("batch_password_mode", "auto")
    must_change = 1 if request.form.get("must_change_password") else 0
    try:
        fields, rows = read_csv_upload(request.files.get("csv_file"))
    except ValueError as exc:
        flash_ui(str(exc), "error")
        return redirect(url_for("teacher_students", **teacher_students_return_filters()))
    if not (has_csv_column(fields, "NIE", "Student ID", "student_code") and has_csv_column(fields, "Nombre", "First name") and has_csv_column(fields, "Apellido", "Last name")):
        flash_ui("El CSV debe incluir las columnas de NIE, nombre y apellido.", "error")
        return redirect(url_for("teacher_students", **teacher_students_return_filters()))
    if generate_email and not valid_email(f"sample@{domain}"):
        flash_ui("Ingresá un dominio de correo válido.", "error")
        return redirect(url_for("teacher_students", **teacher_students_return_filters()))
    if not generate_email and not ({"correo", "email", "correo_electronico"} & set(fields)):
        flash_ui("El CSV debe incluir una columna Correo cuando la generación automática está desactivada.", "error")
        return redirect(url_for("teacher_students", **teacher_students_return_filters()))
    if password_mode == "auto":
        batch_password = generate_temp_password()
    else:
        batch_password = request.form.get("batch_password", "")
        if not valid_student_password(batch_password):
            flash_ui("La contraseña debe tener al menos 8 caracteres e incluir una letra y un número.", "error")
            return redirect(url_for("teacher_students", **teacher_students_return_filters()))
    imported = 0
    skipped = []
    with get_db() as conn:
        section = conn.execute("SELECT id,name FROM sections WHERE id=%s AND is_archived=0", (section_id,)).fetchone()
        if not section:
            flash_ui("Seleccioná una sección válida para la importación.", "error")
            return redirect(url_for("teacher_students", **teacher_students_return_filters()))
        stamp = now_iso()
        for idx, row in enumerate(rows, start=2):
            nie = clean_name(csv_cell(row, "NIE", "Student ID", "student_code", "codigo"), 60)
            first = clean_name(csv_cell(row, "Nombre", "first_name"), 70)
            last = clean_name(csv_cell(row, "Apellido", "last_name"), 70)
            if not nie or not first or not last:
                skipped.append(f"Fila {idx}: faltan NIE, Nombre o Apellido" if get_ui_language() == "es" else f"Row {idx}: NIE, First name or Last name is missing")
                continue
            full_name = clean_name(f"{first} {last}", 120)
            if generate_email:
                local = re.sub(r"[^A-Za-z0-9._+-]", "", nie)
                email = normalize_email(f"{local}@{domain}") if local else ""
            else:
                email = normalize_email(csv_cell(row, "Correo", "Email", "correo_electronico"))
            if not valid_email(email):
                skipped.append(f"Fila {idx}: correo inválido para NIE {nie}" if get_ui_language() == "es" else f"Row {idx}: invalid email for NIE {nie}")
                continue
            duplicate = conn.execute(
                "SELECT id FROM students WHERE COALESCE(is_archived,0)=0 AND (student_code=%s OR email=%s )",
                (nie, email),
            ).fetchone()
            if duplicate:
                skipped.append(f"Fila {idx}: NIE o correo ya registrado ({nie})" if get_ui_language() == "es" else f"Row {idx}: NIE or email already registered ({nie})")
                continue
            try:
                with conn.transaction():
                    conn.execute(
                        """INSERT INTO students(full_name,section_id,student_code,email,password_hash,must_change_password,password_updated_at,notes,is_active,is_archived,created_at,updated_at)
                           VALUES(%s,%s,%s,%s,%s,%s,%s,%s,1,0,%s,%s)""",
                        (full_name, section_id, nie, email, generate_password_hash(batch_password), must_change, stamp, None, stamp, stamp),
                    )
                imported += 1
            except IntegrityError:
                skipped.append(f"Fila {idx}: conflicto de datos ({nie})" if get_ui_language() == "es" else f"Row {idx}: data conflict ({nie})")
        conn.commit()
    summary = {"section_id": section_id, "section": section["name"], "imported": imported, "skipped": len(skipped), "errors": skipped[:8]}
    if not imported:
        flash_ui("No se importaron estudiantes válidos.", "error")
        return render_teacher_students(import_summary=summary, filters_override=teacher_students_return_filters())
    flash_ui("Importación masiva completada", "success")
    return render_teacher_students(
        bulk_credentials={"count": imported, "password": batch_password, "section": section["name"], "section_id": section_id},
        import_summary=summary,
        filters_override=teacher_students_return_filters(),
    )


@app.post("/teacher/sections/new")
@admin_required
def teacher_section_new():
    verify_csrf()
    name = clean_name(request.form.get("name"), 60)
    description = request.form.get("description", "").strip()[:240]
    if not name:
        flash_ui("Escribí un nombre para la sección o el grupo.", "error")
        return redirect(url_for("teacher_students", **teacher_students_return_filters()))
    try:
        with get_db() as conn:
            stamp = now_iso()
            conn.execute(
                "INSERT INTO sections(name,description,is_archived,created_at,updated_at) VALUES(%s,%s,0,%s,%s)",
                (name, description, stamp, stamp),
            )
            conn.commit()
        flash_ui("Sección creada.", "success")
    except IntegrityError:
        flash_ui("Esa sección ya existe.", "error")
    return redirect(url_for("teacher_students", **teacher_students_return_filters()))


@app.post("/teacher/sections/<int:section_id>/edit")
@admin_required
def teacher_section_edit(section_id):
    verify_csrf()
    name = clean_name(request.form.get("name"), 60)
    description = request.form.get("description", "").strip()[:240]
    if not name:
        flash_ui("El nombre de la sección no puede estar vacío.", "error")
        return redirect(url_for("teacher_students", **teacher_students_return_filters()))
    try:
        with get_db() as conn:
            conn.execute(
                "UPDATE sections SET name=%s,description=%s,updated_at=%s WHERE id=%s AND is_archived=0",
                (name, description, now_iso(), section_id),
            )
            conn.commit()
        flash_ui("Sección actualizada.", "success")
    except IntegrityError:
        flash_ui("Otra sección ya usa ese nombre.", "error")
    return redirect(url_for("teacher_students", **teacher_students_return_filters()))


@app.post("/teacher/sections/<int:section_id>/archive")
@admin_required
def teacher_section_archive(section_id):
    verify_csrf()
    with get_db() as conn:
        section = conn.execute("SELECT * FROM sections WHERE id=%s AND is_archived=0", (section_id,)).fetchone()
        if not section:
            abort(404)
        students_in_section = conn.execute(
            "SELECT COUNT(*) AS n FROM students WHERE section_id=%s AND COALESCE(is_archived,0)=0", (section_id,)
        ).fetchone()["n"]
        if students_in_section:
            flash_ui("Mové o archivá a los estudiantes de esta sección antes de archivarla.", "error")
            return redirect(url_for("teacher_students", **teacher_students_return_filters()))
        conn.execute("UPDATE sections SET is_archived=1,updated_at=%s WHERE id=%s", (now_iso(), section_id))
        conn.commit()
    flash_ui("Sección archivada.", "success")
    return redirect(url_for("teacher_students", **teacher_students_return_filters()))


@app.post("/teacher/sections/<int:section_id>/restore")
@admin_required
def teacher_section_restore(section_id):
    verify_csrf()
    with get_db() as conn:
        row = conn.execute("SELECT id FROM sections WHERE id=%s AND is_archived=1", (section_id,)).fetchone()
        if not row:
            abort(404)
        try:
            conn.execute("UPDATE sections SET is_archived=0,updated_at=%s WHERE id=%s", (now_iso(), section_id))
            conn.commit()
        except IntegrityError:
            flash_ui("No pude restaurar la sección porque ya existe otra con ese nombre.", "error")
            return redirect(url_for("teacher_students", **teacher_students_return_filters()))
    flash_ui("Sección restaurada.", "success")
    return redirect(url_for("teacher_students", **teacher_students_return_filters()))


@app.post("/teacher/sections/<int:section_id>/delete")
@admin_required
def teacher_section_delete(section_id):
    verify_csrf()
    with get_db() as conn:
        section = conn.execute("SELECT id,name FROM sections WHERE id=%s AND is_archived=1", (section_id,)).fetchone()
        if not section:
            abort(404)
        student_count = conn.execute(
            "SELECT COUNT(*) AS n FROM students WHERE section_id=%s AND COALESCE(is_archived,0)=0",
            (section_id,),
        ).fetchone()["n"]
        archived_student_count = conn.execute(
            "SELECT COUNT(*) AS n FROM students WHERE section_id=%s AND COALESCE(is_archived,0)=1",
            (section_id,),
        ).fetchone()["n"]
        assignment_count = conn.execute(
            "SELECT COUNT(*) AS n FROM exam_assignments WHERE section_id=%s",
            (section_id,),
        ).fetchone()["n"]
        if student_count or archived_student_count or assignment_count:
            blockers = []
            if student_count:
                blockers.append(f"{student_count} estudiantes activos")
            if archived_student_count:
                blockers.append(f"{archived_student_count} estudiantes archivados")
            if assignment_count:
                blockers.append(f"{assignment_count} exámenes asociados")
            flash_ui("No puedo eliminar la sección porque todavía tiene " + ", ".join(blockers) + ".", "error")
            return redirect(url_for("teacher_students", **teacher_students_return_filters()))
        conn.execute("DELETE FROM sections WHERE id=%s", (section_id,))
        conn.commit()
    flash_ui("Sección eliminada definitivamente.", "success")
    return redirect(url_for("teacher_students", **teacher_students_return_filters()))


@app.post("/teacher/students/bulk")
@admin_required
def teacher_students_bulk():
    verify_csrf()
    bulk_action = request.form.get("bulk_action", "").strip()
    try:
        source_section_id = int(request.form.get("section_id", "0"))
    except ValueError:
        source_section_id = 0
    try:
        target_section_id = int(request.form.get("target_section_id", "0"))
    except ValueError:
        target_section_id = 0
    selected_ids = []
    for raw in request.form.getlist("student_ids"):
        try:
            selected_ids.append(int(raw))
        except ValueError:
            continue
    selected_ids = list(dict.fromkeys(selected_ids))
    return_filters = teacher_students_return_filters()
    if source_section_id < 1:
        flash_ui("Seleccioná una sección válida.", "error")
        return render_teacher_students(filters_override=return_filters)
    if not selected_ids:
        flash_ui("Seleccioná al menos un estudiante.", "error")
        return render_teacher_students(filters_override=return_filters)
    placeholders = ",".join(["%s"] * len(selected_ids))
    with get_db() as conn:
        source_section = conn.execute("SELECT id,name FROM sections WHERE id=%s AND is_archived=0", (source_section_id,)).fetchone()
        if not source_section:
            flash_ui("Seleccioná una sección válida.", "error")
            return render_teacher_students(filters_override=return_filters)
        selected_rows = conn.execute(
            f"SELECT id FROM students WHERE id IN ({placeholders}) AND section_id=%s AND COALESCE(is_archived,0)=0",
            (*selected_ids, source_section_id),
        ).fetchall()
        selected_ids = [int(row["id"]) for row in selected_rows]
        if not selected_ids:
            flash_ui("Seleccioná al menos un estudiante de esta sección.", "error")
            return render_teacher_students(filters_override=return_filters)
        stamp = now_iso()
        if bulk_action == "archive":
            conn.execute(
                f"UPDATE students SET is_active=0,is_archived=1,updated_at=%s WHERE id IN ({placeholders}) AND section_id=%s",
                (stamp, *selected_ids, source_section_id),
            )
            conn.commit()
            flash_ui(f"{len(selected_ids)} estudiantes archivados.", "success")
        elif bulk_action == "move":
            if target_section_id < 1 or target_section_id == source_section_id:
                flash_ui("Seleccioná una sección destino distinta.", "error")
                return render_teacher_students(filters_override=return_filters)
            target_section = conn.execute(
                "SELECT id,name FROM sections WHERE id=%s AND is_archived=0",
                (target_section_id,),
            ).fetchone()
            if not target_section:
                flash_ui("Seleccioná una sección destino válida.", "error")
                return render_teacher_students(filters_override=return_filters)
            conn.execute(
                f"UPDATE students SET section_id=%s,updated_at=%s WHERE id IN ({placeholders}) AND section_id=%s",
                (target_section_id, stamp, *selected_ids, source_section_id),
            )
            conn.commit()
            flash_ui(f"{len(selected_ids)} estudiantes movidos a {target_section['name']}.", "success")
        else:
            flash_ui("Elegí una acción masiva válida.", "error")
    return render_teacher_students(filters_override=return_filters)


@app.post("/teacher/students/new")
@admin_required
def teacher_student_new():
    verify_csrf()
    full_name = clean_name(request.form.get("full_name"), 120)
    email = normalize_email(request.form.get("email"))
    code = clean_name(request.form.get("student_code"), 60) or None
    notes = request.form.get("notes", "").strip()[:500] or None
    password_mode = request.form.get("password_mode", "auto")
    must_change = 1 if request.form.get("must_change_password") else 0
    try:
        section_id = int(request.form.get("section_id", "0"))
    except ValueError:
        section_id = 0
    if len(full_name) < 3 or section_id < 1:
        flash_ui("El nombre del estudiante y la sección son obligatorios.", "error")
        return render_teacher_students(filters_override=teacher_students_return_filters())
    if not valid_email(email):
        flash_ui("Se requiere un correo de estudiante válido.", "error")
        return render_teacher_students(filters_override=teacher_students_return_filters())
    if password_mode == "auto":
        password = generate_temp_password()
    elif password_mode == "manual":
        password = request.form.get("manual_password", "")
        if not valid_student_password(password):
            flash_ui("La contraseña debe tener al menos 8 caracteres e incluir una letra y un número.", "error")
            return render_teacher_students(filters_override=teacher_students_return_filters())
    else:
        flash_ui("Elegí un método de contraseña inicial.", "error")
        return render_teacher_students(filters_override=teacher_students_return_filters())
    try:
        with get_db() as conn:
            valid = conn.execute("SELECT 1 FROM sections WHERE id=%s AND is_archived=0", (section_id,)).fetchone()
            if not valid:
                flash_ui("Seleccioná una sección válida.", "error")
                return render_teacher_students(filters_override=teacher_students_return_filters())
            if conn.execute("SELECT 1 FROM students WHERE email=%s ", (email,)).fetchone():
                flash_ui("Ese correo ya está asignado a otro estudiante.", "error")
                return render_teacher_students(filters_override=teacher_students_return_filters())
            stamp = now_iso()
            conn.execute(
                """INSERT INTO students(full_name,section_id,student_code,email,password_hash,must_change_password,password_updated_at,notes,is_active,created_at,updated_at)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,1,%s,%s)""",
                (full_name, section_id, code, email, generate_password_hash(password), must_change, stamp, notes, stamp, stamp),
            )
            conn.commit()
        credentials = {"name": full_name, "email": email, "password": password, "section_id": section_id}
        flash_ui("Estudiante agregado. Las credenciales temporales se muestran abajo.", "success")
        return render_teacher_students(credentials=credentials, filters_override=teacher_students_return_filters())
    except IntegrityError as exc:
        if "email" in str(exc).lower():
            flash_ui("Ese correo ya está asignado a otro estudiante.", "error")
        else:
            flash_ui("Ese estudiante ya existe en la sección, o el código de estudiante ya está en uso.", "error")
    return redirect(url_for("teacher_students", **teacher_students_return_filters()))


@app.post("/teacher/students/<int:student_id>/edit")
@admin_required
def teacher_student_edit(student_id):
    verify_csrf()
    full_name = clean_name(request.form.get("full_name"), 120)
    email = normalize_email(request.form.get("email"))
    code = clean_name(request.form.get("student_code"), 60) or None
    notes = request.form.get("notes", "").strip()[:500] or None
    is_active = 1 if request.form.get("is_active") else 0
    try:
        section_id = int(request.form.get("section_id", "0"))
    except ValueError:
        section_id = 0
    if len(full_name) < 3 or section_id < 1:
        flash_ui("El nombre del estudiante y la sección son obligatorios.", "error")
        return render_teacher_students(filters_override=teacher_students_return_filters())
    if not valid_email(email):
        flash_ui("Se requiere un correo de estudiante válido.", "error")
        return render_teacher_students(filters_override=teacher_students_return_filters())
    try:
        with get_db() as conn:
            valid = conn.execute("SELECT 1 FROM sections WHERE id=%s AND is_archived=0", (section_id,)).fetchone()
            if not valid:
                flash_ui("Seleccioná una sección válida.", "error")
                return render_teacher_students(filters_override=teacher_students_return_filters())
            duplicate_email = conn.execute("SELECT id FROM students WHERE email=%s  AND id<>%s", (email, student_id)).fetchone()
            if duplicate_email:
                flash_ui("Ese correo ya está asignado a otro estudiante.", "error")
                return render_teacher_students(filters_override=teacher_students_return_filters())
            conn.execute(
                """UPDATE students SET full_name=%s,section_id=%s,student_code=%s,email=%s,notes=%s,is_active=%s,updated_at=%s
                   WHERE id=%s""",
                (full_name, section_id, code, email, notes, is_active, now_iso(), student_id),
            )
            conn.commit()
        flash_ui("Cuenta de estudiante actualizada.", "success")
    except IntegrityError as exc:
        if "email" in str(exc).lower():
            flash_ui("Ese correo ya está asignado a otro estudiante.", "error")
        else:
            flash_ui("Ese estudiante ya existe en la sección, o el código de estudiante ya está en uso.", "error")
    return redirect(url_for("teacher_students", **teacher_students_return_filters()))


@app.post("/teacher/students/<int:student_id>/password")
@admin_required
def teacher_student_password(student_id):
    verify_csrf()
    password_mode = request.form.get("password_mode", "auto")
    must_change = 1 if request.form.get("must_change_password") else 0
    if password_mode == "auto":
        password = generate_temp_password()
    elif password_mode == "manual":
        password = request.form.get("manual_password", "")
        if not valid_student_password(password):
            flash_ui("La contraseña debe tener al menos 8 caracteres e incluir una letra y un número.", "error")
            return render_teacher_students(filters_override=teacher_students_return_filters())
    else:
        flash_ui("Elegí un método de contraseña inicial.", "error")
        return render_teacher_students(filters_override=teacher_students_return_filters())
    with get_db() as conn:
        student = conn.execute("SELECT id,full_name,email,section_id FROM students WHERE id=%s", (student_id,)).fetchone()
        if not student:
            abort(404)
        if not student["email"]:
            flash_ui("Se requiere un correo de estudiante válido.", "error")
            return render_teacher_students(filters_override=teacher_students_return_filters())
        conn.execute(
            "UPDATE students SET password_hash=%s,must_change_password=%s,password_updated_at=%s,updated_at=%s WHERE id=%s",
            (generate_password_hash(password), must_change, now_iso(), now_iso(), student_id),
        )
        conn.commit()
    credentials = {"name": student["full_name"], "email": student["email"], "password": password, "section_id": student["section_id"]}
    flash_ui("Contraseña restablecida. Las nuevas credenciales se muestran abajo.", "success")
    return render_teacher_students(credentials=credentials, filters_override=teacher_students_return_filters())


@app.post("/teacher/students/<int:student_id>/toggle")
@admin_required
def teacher_student_toggle(student_id):
    verify_csrf()
    with get_db() as conn:
        row = conn.execute("SELECT is_active FROM students WHERE id=%s", (student_id,)).fetchone()
        if not row:
            abort(404)
        new_value = 0 if row["is_active"] else 1
        conn.execute("UPDATE students SET is_active=%s,updated_at=%s WHERE id=%s", (new_value, now_iso(), student_id))
        conn.commit()
    flash_ui("Estado del estudiante actualizado.", "success")
    return redirect(url_for("teacher_students", **teacher_students_return_filters()))


@app.post("/teacher/students/<int:student_id>/archive")
@admin_required
def teacher_student_archive(student_id):
    verify_csrf()
    with get_db() as conn:
        row = conn.execute("SELECT id FROM students WHERE id=%s AND COALESCE(is_archived,0)=0", (student_id,)).fetchone()
        if not row:
            abort(404)
        conn.execute(
            "UPDATE students SET is_active=0,is_archived=1,updated_at=%s WHERE id=%s",
            (now_iso(), student_id),
        )
        conn.commit()
    flash_ui("Estudiante archivado.", "success")
    return redirect(url_for("teacher_students", **teacher_students_return_filters()))


@app.post("/teacher/students/<int:student_id>/restore")
@admin_required
def teacher_student_restore(student_id):
    verify_csrf()
    with get_db() as conn:
        row = conn.execute(
            """SELECT st.id, st.section_id, sec.is_archived AS section_archived
               FROM students st JOIN sections sec ON sec.id=st.section_id
               WHERE st.id=%s AND COALESCE(st.is_archived,0)=1""",
            (student_id,),
        ).fetchone()
        if not row:
            abort(404)
        if row["section_archived"]:
            flash_ui("Primero restaurá la sección de ese estudiante.", "error")
            return redirect(url_for("teacher_students", **teacher_students_return_filters()))
        try:
            conn.execute("UPDATE students SET is_archived=0,is_active=1,updated_at=%s WHERE id=%s", (now_iso(), student_id))
            conn.commit()
        except IntegrityError:
            flash_ui("No pude restaurar el estudiante porque su correo o código ya está en uso.", "error")
            return redirect(url_for("teacher_students", **teacher_students_return_filters()))
    flash_ui("Estudiante restaurado.", "success")
    return redirect(url_for("teacher_students", **teacher_students_return_filters()))


@app.post("/teacher/students/<int:student_id>/delete")
@admin_required
def teacher_student_delete(student_id):
    verify_csrf()
    with get_db() as conn:
        student = conn.execute("SELECT id,full_name FROM students WHERE id=%s AND COALESCE(is_archived,0)=1", (student_id,)).fetchone()
        if not student:
            abort(404)
        attempt_count = conn.execute("SELECT COUNT(*) AS n FROM attempts WHERE student_id=%s", (student_id,)).fetchone()["n"]
        allocation_count = conn.execute(
            "SELECT COUNT(*) AS n FROM student_exam_allocations WHERE student_id=%s",
            (student_id,),
        ).fetchone()["n"]
        if attempt_count or allocation_count:
            flash_ui("No puedo eliminar al estudiante porque tiene exámenes o asignaciones asociadas.", "error")
            return redirect(url_for("teacher_students", **teacher_students_return_filters()))
        conn.execute("DELETE FROM students WHERE id=%s", (student_id,))
        conn.commit()
    flash_ui("Estudiante eliminado definitivamente.", "success")
    return redirect(url_for("teacher_students", **teacher_students_return_filters()))
