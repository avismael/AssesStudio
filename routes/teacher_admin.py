from flask import abort, flash, redirect, render_template, request, session, url_for
from psycopg import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app import (
    DEFAULT_SETTINGS,
    SUPPORTED_UI_LANGUAGES,
    admin_required,
    app,
    bump_rules_version,
    clean_name,
    current_teacher_id,
    flash_ui,
    get_db,
    now_iso,
    normalize_email,
    setting,
    teacher_required,
    tr,
    valid_email,
    valid_student_password,
    verify_csrf,
)


@app.get("/teacher/users")
@admin_required
def teacher_users():
    with get_db() as conn:
        rows = conn.execute("SELECT id,full_name,email,role,is_active,last_login_at,created_at FROM teachers ORDER BY is_active DESC, full_name ").fetchall()
    return render_template("teacher/users.html", rows=rows)


@app.post("/teacher/users/new")
@admin_required
def teacher_user_new():
    verify_csrf()
    name = clean_name(request.form.get("full_name"), 120)
    email = normalize_email(request.form.get("email"))
    password = request.form.get("password", "")
    role = request.form.get("role", "teacher")
    if role not in {"teacher", "admin"}:
        role = "teacher"
    if len(name) < 2 or not valid_email(email):
        flash_ui("Teacher name and a valid email are required.", "error")
        return redirect(url_for("teacher_users"))
    if not valid_student_password(password):
        flash_ui("Password must be at least 8 characters and include at least one letter and one number.", "error")
        return redirect(url_for("teacher_users"))
    try:
        with get_db() as conn:
            conn.execute(
                """INSERT INTO teachers(full_name,email,password_hash,role,is_active,must_change_password,created_at,updated_at)
                   VALUES(%s,%s,%s,%s,1,0,%s,%s)""",
                (name, email, generate_password_hash(password), role, now_iso(), now_iso()),
            )
            conn.commit()
    except IntegrityError:
        flash_ui("That email address is already assigned to another teacher.", "error")
        return redirect(url_for("teacher_users"))
    flash_ui("Teacher account created.", "success")
    return redirect(url_for("teacher_users"))


@app.post("/teacher/users/<int:teacher_id>/edit")
@admin_required
def teacher_user_edit(teacher_id):
    verify_csrf()
    name = clean_name(request.form.get("full_name"), 120)
    email = normalize_email(request.form.get("email"))
    role = request.form.get("role", "teacher")
    if role not in {"teacher", "admin"}:
        role = "teacher"
    if len(name) < 2 or not valid_email(email):
        flash_ui("Teacher name and a valid email are required.", "error")
        return redirect(url_for("teacher_users"))
    with get_db() as conn:
        account = conn.execute("SELECT * FROM teachers WHERE id=%s", (teacher_id,)).fetchone()
        if not account:
            abort(404)
        if account["role"] == "admin" and role != "admin":
            admin_count = conn.execute("SELECT COUNT(*) AS n FROM teachers WHERE role='admin' AND is_active=1").fetchone()["n"]
            if admin_count <= 1:
                flash_ui("At least one active administrator is required.", "error")
                return redirect(url_for("teacher_users"))
        try:
            conn.execute("UPDATE teachers SET full_name=%s,email=%s,role=%s,updated_at=%s WHERE id=%s", (name, email, role, now_iso(), teacher_id))
            conn.commit()
        except IntegrityError:
            conn.rollback()
            flash_ui("That email address is already assigned to another teacher.", "error")
            return redirect(url_for("teacher_users"))
    if teacher_id == current_teacher_id():
        session["teacher_name"] = name
        session["teacher_role"] = role
    flash_ui("Teacher account updated.", "success")
    return redirect(url_for("teacher_users"))


@app.post("/teacher/users/<int:teacher_id>/password")
@admin_required
def teacher_user_password(teacher_id):
    verify_csrf()
    password = request.form.get("password", "")
    if not valid_student_password(password):
        flash_ui("Password must be at least 8 characters and include at least one letter and one number.", "error")
        return redirect(url_for("teacher_users"))
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM teachers WHERE id=%s", (teacher_id,)).fetchone():
            abort(404)
        conn.execute("UPDATE teachers SET password_hash=%s,updated_at=%s WHERE id=%s", (generate_password_hash(password), now_iso(), teacher_id))
        conn.commit()
    flash_ui("Teacher password reset.", "success")
    return redirect(url_for("teacher_users"))


@app.post("/teacher/users/<int:teacher_id>/toggle")
@admin_required
def teacher_user_toggle(teacher_id):
    verify_csrf()
    if teacher_id == current_teacher_id():
        flash_ui("You cannot disable your own active session.", "error")
        return redirect(url_for("teacher_users"))
    with get_db() as conn:
        account = conn.execute("SELECT * FROM teachers WHERE id=%s", (teacher_id,)).fetchone()
        if not account:
            abort(404)
        new_value = 0 if account["is_active"] else 1
        if not new_value and account["role"] == "admin":
            admin_count = conn.execute("SELECT COUNT(*) AS n FROM teachers WHERE role='admin' AND is_active=1").fetchone()["n"]
            if admin_count <= 1:
                flash_ui("At least one active administrator is required.", "error")
                return redirect(url_for("teacher_users"))
        conn.execute("UPDATE teachers SET is_active=%s,updated_at=%s WHERE id=%s", (new_value, now_iso(), teacher_id))
        conn.commit()
    flash_ui("Teacher account enabled." if new_value else "Teacher account disabled.", "success")
    return redirect(url_for("teacher_users"))


@app.route("/teacher/account/password", methods=["GET", "POST"])
@teacher_required
def teacher_account_password():
    teacher_id = current_teacher_id()
    if request.method == "POST":
        verify_csrf()
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        with get_db() as conn:
            account = conn.execute("SELECT * FROM teachers WHERE id=%s", (teacher_id,)).fetchone()
            if not account or not check_password_hash(account["password_hash"], current_password):
                flash_ui("Your current password is incorrect.", "error")
            elif new_password != confirm_password:
                flash_ui("The new passwords do not match.", "error")
            elif not valid_student_password(new_password):
                flash_ui("Password must be at least 8 characters and include at least one letter and one number.", "error")
            else:
                conn.execute("UPDATE teachers SET password_hash=%s,updated_at=%s WHERE id=%s", (generate_password_hash(new_password), now_iso(), teacher_id))
                conn.commit()
                flash_ui("Password updated successfully.", "success")
                return redirect(url_for("teacher"))
    return render_template("teacher/password.html")


@app.route("/teacher/setup", methods=["GET", "POST"])
@admin_required
def teacher_setup():
    if request.method == "POST":
        verify_csrf()
        institution = " ".join(request.form.get("institution_name", "").strip().split())
        subtitle = request.form.get("assessment_subtitle", "").strip()
        ui_language = request.form.get("ui_language", "es").strip().lower()
        rules_es = request.form.get("student_rules_es", "").strip()[:5000]
        rules_en = request.form.get("student_rules_en", "").strip()[:5000]
        rules_version = clean_name(request.form.get("rules_version"), 40)
        require_rules = "1" if request.form.get("require_rules_acknowledgment") else "0"
        if ui_language not in SUPPORTED_UI_LANGUAGES:
            ui_language = "es"
        try:
            plays = max(1, min(5, int(request.form.get("listening_max_plays", "2"))))
        except ValueError:
            plays = 2
        if not institution or not rules_es or not rules_en or not rules_version:
            flash_ui("Institution and both usage-rule translations are required.", "error")
        else:
            with get_db() as conn:
                rules_changed = (
                    rules_es != setting(conn, "student_rules_es")
                    or rules_en != setting(conn, "student_rules_en")
                )
                if rules_changed:
                    rules_version = bump_rules_version(setting(conn, "rules_version"))
                values = {"institution_name": institution, "assessment_subtitle": subtitle,
                          "listening_max_plays": str(plays), "ui_language": ui_language,
                          "student_rules_es": rules_es, "student_rules_en": rules_en,
                          "rules_version": rules_version, "require_rules_acknowledgment": require_rules,
                          "rules_updated_at": now_iso()}
                for key, value in values.items():
                    conn.execute("INSERT INTO app_settings(key,value) VALUES(%s,%s) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
                conn.commit()
            flash(tr("Assessment settings saved.", language=ui_language), "success")
            session.pop("_assessment_ui_language", None)
            return redirect(url_for("teacher_setup"))
    with get_db() as conn:
        settings = {key: setting(conn, key) for key in DEFAULT_SETTINGS}
        exam_count = conn.execute("SELECT COUNT(*) AS n FROM exams WHERE is_archived=0").fetchone()["n"]
        published_count = conn.execute("SELECT COUNT(*) AS n FROM exams WHERE is_archived=0 AND is_published=1").fetchone()["n"]
    return render_template("teacher/setup.html", settings=settings, exam_count=exam_count, published_count=published_count)
