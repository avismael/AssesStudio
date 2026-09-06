from flask import abort, render_template, url_for

from app import (
    app,
    get_db,
    setting,
    teacher_required,
    teacher_reports_section_rows,
    teacher_section_report_rows,
    teacher_section_subject_report_rows,
    teacher_student_report_rows,
)


@app.get("/teacher/reports")
@teacher_required
def teacher_reports():
    with get_db() as conn:
        institution = setting(conn, "institution_name")
        sections, is_admin = teacher_reports_section_rows(conn)
    return render_template(
        "teacher/reports/index.html",
        institution=institution,
        sections=sections,
        is_admin=is_admin,
        back_url=url_for("teacher_students") if is_admin else url_for("teacher"),
        back_label="Volver al padrón" if is_admin else "Volver al panel",
    )


@app.get("/teacher/reports/student/<int:student_id>")
@teacher_required
def teacher_student_report(student_id):
    with get_db() as conn:
        institution = setting(conn, "institution_name")
        student, rows, is_admin = teacher_student_report_rows(conn, student_id)
        if not student:
            abort(404)
    return render_template(
        "teacher/reports/report.html",
        mode="student",
        report_title=student["full_name"],
        report_subtitle=f"NIE {student['student_code']} · {student['section_name']}",
        institution=institution,
        student=student,
        rows=rows,
        is_admin=is_admin,
        scope_note="Documento emitido con los datos visibles para tu cuenta." if not is_admin else "Documento emitido con acceso completo de administración.",
        back_url=url_for("teacher_section_report", section_id=student["section_id"]),
    )


@app.get("/teacher/reports/section/<int:section_id>")
@teacher_required
def teacher_section_report(section_id):
    with get_db() as conn:
        institution = setting(conn, "institution_name")
        section, subjects, is_admin = teacher_section_report_rows(conn, section_id)
        if not section:
            abort(404)
    return render_template(
        "teacher/reports/section.html",
        institution=institution,
        section=section,
        subjects=subjects,
        is_admin=is_admin,
        back_url=url_for("teacher_reports"),
    )


@app.get("/teacher/reports/section/<int:section_id>/subject/<int:subject_id>")
@teacher_required
def teacher_section_subject_report(section_id, subject_id):
    with get_db() as conn:
        institution = setting(conn, "institution_name")
        section, subject, evaluation, rows, is_admin = teacher_section_subject_report_rows(conn, section_id, subject_id)
        if not section or not subject:
            abort(404)
    return render_template(
        "teacher/reports/report.html",
        mode="subject",
        report_title=f"{section['name']} · {subject['name']}",
        report_subtitle=f"Evaluación: {evaluation['title']}" if evaluation else "Sin evaluación disponible",
        institution=institution,
        section=section,
        subject=subject,
        evaluation=evaluation,
        rows=rows,
        is_admin=is_admin,
        scope_note="Documento emitido con los datos visibles para tu cuenta." if not is_admin else "Documento emitido con acceso completo de administración.",
        back_url=url_for("teacher_section_report", section_id=section_id),
    )
