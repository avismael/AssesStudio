import io
from xml.sax.saxutils import escape as xml_escape

from flask import abort, redirect, render_template, request, send_file, url_for
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from psycopg import IntegrityError

from app import (
    TYPE_LABELS,
    app,
    clean_name,
    current_teacher_id,
    exam_docx_export,
    exam_export_filename,
    exam_export_payload,
    exam_markdown_export,
    exam_pdf_page_number,
    exam_row,
    flash_ui,
    get_db,
    listening_row_usable,
    localized_type_labels,
    now_iso,
    pdf_choice_letter,
    subject_teacher_clause,
    teacher_required,
    verify_csrf,
)


@app.get("/teacher/exams")
@teacher_required
def teacher_exams():
    with get_db() as conn:
        subject_filter, subject_params = subject_teacher_clause(conn, "s", current_teacher_id())
        row_params = [current_teacher_id()] + (subject_params if subject_filter else [])
        rows = conn.execute(
            f"""SELECT e.*,s.name AS subject_name,
                      (SELECT COUNT(*) FROM exam_versions v WHERE v.exam_id=e.id AND v.is_active=1) AS version_count,
                      (SELECT COUNT(*) FROM exam_assignments a WHERE a.exam_id=e.id AND a.is_active=1) AS assignment_count,
                      (SELECT COUNT(*) FROM attempts t WHERE t.exam_id=e.id AND t.status='submitted') AS result_count
               FROM exams e JOIN subjects s ON s.id=e.subject_id
               WHERE e.teacher_id=%s AND e.is_archived=0{subject_filter} ORDER BY e.updated_at DESC,e.title """,
            tuple(row_params),
        ).fetchall()
        subjects = conn.execute(
            f"SELECT * FROM subjects s WHERE s.is_archived=0{subject_filter} ORDER BY s.name ",
            tuple(subject_params),
        ).fetchall()
    return render_template("teacher/exams/index.html", rows=rows, subjects=subjects)


@app.post("/teacher/exams/new")
@teacher_required
def teacher_exam_new():
    verify_csrf()
    title = clean_name(request.form.get("title"), 160)
    description = request.form.get("description", "").strip()[:500]
    try:
        subject_id = int(request.form.get("subject_id", "0"))
    except ValueError:
        subject_id = 0
    with get_db() as conn:
        subject_filter, subject_params = subject_teacher_clause(conn, "s", current_teacher_id())
        valid = conn.execute(
            f"SELECT 1 FROM subjects s WHERE s.id=%s AND s.is_archived=0{subject_filter}",
            (subject_id, *subject_params),
        ).fetchone()
        if not title or not valid:
            flash_ui("Exam title and a valid subject are required.", "error")
            return redirect(url_for("teacher_exams"))
        exam_id = conn.execute(
            """INSERT INTO exams(teacher_id,subject_id,title,description,is_published,is_archived,created_at,updated_at)
               VALUES(%s,%s,%s,%s,0,0,%s,%s) RETURNING id""",
            (current_teacher_id(), subject_id, title, description, now_iso(), now_iso()),
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO exam_versions(exam_id,name,is_active,created_at,updated_at) VALUES(%s,%s,1,%s,%s)",
            (exam_id, "A", now_iso(), now_iso()),
        )
        conn.commit()
    flash_ui("Exam created.", "success")
    return redirect(url_for("teacher_exam_detail", exam_id=exam_id))


@app.get("/teacher/exams/<int:exam_id>")
@teacher_required
def teacher_exam_detail(exam_id):
    with get_db() as conn:
        exam_row_data = exam_row(conn, exam_id)
        if not exam_row_data:
            abort(404)
        exam_edit_meta = conn.execute(
            """SELECT
                   (SELECT COUNT(*) FROM exam_version_questions evq
                    JOIN exam_versions v ON v.id=evq.version_id
                    WHERE v.exam_id=%s AND v.is_active=1) AS selected_question_count,
                   (SELECT COUNT(*) FROM exam_assignments a
                    WHERE a.exam_id=%s AND a.is_active=1) AS assignment_count,
                   (SELECT COUNT(*) FROM attempts t
                    WHERE t.exam_id=%s AND t.status='submitted') AS submitted_count""",
            (exam_id, exam_id, exam_id),
        ).fetchone()
        versions = conn.execute(
            """SELECT v.*,COUNT(evq.question_id) AS question_count FROM exam_versions v
               LEFT JOIN exam_version_questions evq ON evq.version_id=v.id
               WHERE v.exam_id=%s AND v.is_active=1 GROUP BY v.id ORDER BY v.id""",
            (exam_id,),
        ).fetchall()
        archived_versions = conn.execute(
            """SELECT v.*,COUNT(evq.question_id) AS question_count FROM exam_versions v
               LEFT JOIN exam_version_questions evq ON evq.version_id=v.id
               WHERE v.exam_id=%s AND v.is_active=0 GROUP BY v.id ORDER BY v.updated_at DESC, v.id DESC""",
            (exam_id,),
        ).fetchall()
        assignments = conn.execute(
            """SELECT a.*,sec.name AS section_name,v.name AS fixed_version_name,
                      (SELECT COUNT(*) FROM attempts t WHERE t.assignment_id=a.id) AS attempt_count
               FROM exam_assignments a JOIN sections sec ON sec.id=a.section_id
               LEFT JOIN exam_versions v ON v.id=a.fixed_version_id
               WHERE a.exam_id=%s AND a.is_active=1 AND sec.is_archived=0 ORDER BY sec.name""",
            (exam_id,),
        ).fetchall()
        sections = conn.execute("SELECT * FROM sections WHERE is_archived=0 ORDER BY name ").fetchall()
        subject_filter, subject_params = subject_teacher_clause(conn, "s", current_teacher_id())
        subjects = conn.execute(
            f"SELECT * FROM subjects s WHERE s.is_archived=0{subject_filter} ORDER BY s.name",
            tuple(subject_params),
        ).fetchall()
    return render_template(
        "teacher/exams/detail.html",
        exam=exam_row_data,
        versions=versions,
        archived_versions=archived_versions,
        assignments=assignments,
        sections=sections,
        subjects=subjects,
        exam_edit_meta=exam_edit_meta,
    )


@app.get("/teacher/exams/<int:exam_id>/pdf")
@teacher_required
def teacher_exam_pdf(exam_id):
    with get_db() as conn:
        exam, institution, teacher_name, rt, version_payloads = exam_export_payload(conn, exam_id)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.55 * inch,
        pageCompression=0,
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "ExamInstitution",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=12,
            textColor=colors.HexColor("#334155"),
            spaceAfter=2,
            keepWithNext=1,
        )
    )
    styles.add(ParagraphStyle("ExamTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, leading=20, spaceAfter=4, keepWithNext=1))
    styles.add(ParagraphStyle("ExamMeta", parent=styles["BodyText"], fontSize=10, leading=12, spaceAfter=1, keepWithNext=1))
    styles.add(ParagraphStyle("ExamVersion", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=14, spaceBefore=6, spaceAfter=4, keepWithNext=1))
    styles.add(ParagraphStyle("ExamSection", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=11, leading=13, spaceBefore=6, spaceAfter=4, keepWithNext=1))
    styles.add(ParagraphStyle("ExamQuestion", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=10.5, leading=13, spaceBefore=6, spaceAfter=3, keepWithNext=1))
    styles.add(ParagraphStyle("ExamChoice", parent=styles["BodyText"], fontSize=9.5, leading=11, leftIndent=12, firstLineIndent=0, spaceAfter=0, spaceBefore=0, keepWithNext=1))
    story = []
    for index, payload in enumerate(version_payloads):
        if index:
            story.append(PageBreak())
        version = payload["version"]
        questions = payload["questions"]
        story.extend(
            [
                Paragraph(xml_escape(institution), styles["ExamInstitution"]),
                Paragraph(xml_escape(exam["title"]), styles["ExamTitle"]),
                Paragraph(f"<b>{rt('Institution')}:</b> {xml_escape(institution)}", styles["ExamMeta"]),
                Paragraph(f"<b>{rt('Subject')}:</b> {xml_escape(exam['subject_name'] or '')}", styles["ExamMeta"]),
                Paragraph(f"<b>{rt('Teacher')}:</b> {xml_escape(teacher_name)}", styles["ExamMeta"]),
                Paragraph(f"<b>{rt('Version')} {xml_escape(version['name'])}</b>", styles["ExamVersion"]),
                Paragraph(f"<b>{rt('Questions')}</b> ({len(questions)})", styles["ExamSection"]),
            ]
        )
        info_table = Table(
            [
                [
                    Paragraph(f"<b>{rt('Student name')}</b>", styles["BodyText"]),
                    Paragraph("______________________________", styles["BodyText"]),
                    Paragraph(f"<b>{rt('Student ID')}</b>", styles["BodyText"]),
                    Paragraph("________________________", styles["BodyText"]),
                ],
                [
                    Paragraph(f"<b>{rt('Section')}</b>", styles["BodyText"]),
                    Paragraph("______________________________", styles["BodyText"]),
                    Paragraph(f"<b>{rt('Date')}</b>", styles["BodyText"]),
                    Paragraph("________________________", styles["BodyText"]),
                ],
            ],
            colWidths=[1.05 * inch, 2.45 * inch, 0.8 * inch, 2.0 * inch],
        )
        info_table.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        story.extend(
            [
                info_table,
                Spacer(1, 10),
                Paragraph(f"<b>{rt('Instructions')}</b>", styles["Heading3"]),
                Paragraph(
                    f"1. {rt('Use blue or black ink.')}<br/>2. {rt('Write clearly and keep your answers legible.')}<br/>3. {rt('Do not write on the answer key; this copy is for student use only.')}",
                    styles["BodyText"],
                ),
                Spacer(1, 10),
            ]
        )
        for q_index, question in enumerate(questions, start=1):
            question_block = [Spacer(1, 4), Paragraph(f"<b>{q_index}. {xml_escape(question['prompt'])}</b>", styles["ExamQuestion"])]
            if question["type"] in {"multiple_choice", "true_false", "listening"}:
                for choice_index, (_, choice_text) in enumerate(question.get("choices", [])):
                    question_block.append(Paragraph(f"<b>{pdf_choice_letter(choice_index)}.</b> {xml_escape(choice_text)}", styles["ExamChoice"]))
            elif question["type"] == "order":
                for item_id, item_text in question.get("items", []):
                    question_block.append(Paragraph(f"• {xml_escape(item_text)}", styles["ExamChoice"]))
                question_block.append(Paragraph(f"{rt('Order line')}: ________________________________________________", styles["ExamChoice"]))
            elif question["type"] == "matching":
                left_rows = [
                    [Paragraph(f"<b>{rt('Left items')}</b>", styles["ExamChoice"]), Paragraph(f"<b>{rt('Right items')}</b>", styles["ExamChoice"])]
                ]
                left_items = [text for _, text in question.get("left", [])]
                right_items = [text for _, text in question.get("right", [])]
                max_rows = max(len(left_items), len(right_items))
                for idx in range(max_rows):
                    left_text = xml_escape(left_items[idx]) if idx < len(left_items) else ""
                    right_text = xml_escape(right_items[idx]) if idx < len(right_items) else ""
                    left_rows.append([Paragraph(left_text, styles["ExamChoice"]), Paragraph(right_text, styles["ExamChoice"])])
                table = Table(left_rows, colWidths=[3.25 * inch, 3.25 * inch], repeatRows=1, splitByRow=1)
                table.setStyle(
                    TableStyle(
                        [
                            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#CBD5E1")),
                            ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E2E8F0")),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F8FAFC")),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 8),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                            ("TOPPADDING", (0, 0), (-1, -1), 5),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ]
                    )
                )
                question_block.extend([Spacer(1, 4), table])
            else:
                question_block.append(Paragraph(f"{rt('Answer line')}: ________________________________________________", styles["ExamChoice"]))
            story.append(KeepTogether(question_block))
        if index < len(version_payloads) - 1:
            story.append(Spacer(1, 8))

    doc.build(story, onFirstPage=exam_pdf_page_number, onLaterPages=exam_pdf_page_number)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=exam_export_filename(exam, "pdf"), mimetype="application/pdf")


@app.get("/teacher/exams/<int:exam_id>/markdown")
@teacher_required
def teacher_exam_markdown(exam_id):
    with get_db() as conn:
        exam, institution, teacher_name, rt, version_payloads = exam_export_payload(conn, exam_id)
    content = exam_markdown_export(exam, institution, teacher_name, rt, version_payloads)
    buffer = io.BytesIO(content.encode("utf-8"))
    return send_file(buffer, as_attachment=True, download_name=exam_export_filename(exam, "md"), mimetype="text/markdown")


@app.get("/teacher/exams/<int:exam_id>/docx")
@teacher_required
def teacher_exam_docx(exam_id):
    with get_db() as conn:
        exam, institution, teacher_name, rt, version_payloads = exam_export_payload(conn, exam_id)
    buffer = exam_docx_export(exam, institution, teacher_name, rt, version_payloads)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=exam_export_filename(exam, "docx"),
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.post("/teacher/exams/<int:exam_id>/edit")
@teacher_required
def teacher_exam_edit(exam_id):
    verify_csrf()
    title = clean_name(request.form.get("title"), 160)
    description = request.form.get("description", "").strip()[:500]
    try:
        subject_id = int(request.form.get("subject_id", "0"))
    except ValueError:
        subject_id = 0
    if not title:
        flash_ui("Exam title is required.", "error")
        return redirect(url_for("teacher_exam_detail", exam_id=exam_id))
    with get_db() as conn:
        exam = exam_row(conn, exam_id)
        if not exam:
            abort(404)
        subject = conn.execute("SELECT id FROM subjects WHERE id=%s AND teacher_id=%s AND is_archived=0", (subject_id, current_teacher_id())).fetchone()
        if not subject:
            flash_ui("Choose a valid subject.", "error")
            return redirect(url_for("teacher_exam_detail", exam_id=exam_id))
        submitted_count = conn.execute(
            "SELECT COUNT(*) AS n FROM attempts WHERE exam_id=%s AND status='submitted'",
            (exam_id,),
        ).fetchone()["n"]
        if subject_id != int(exam["subject_id"]) and submitted_count:
            flash_ui("You cannot change the subject after students have submitted results.", "error")
            return redirect(url_for("teacher_exam_detail", exam_id=exam_id))
        conn.execute("UPDATE exams SET subject_id=%s,title=%s,description=%s,updated_at=%s WHERE id=%s", (subject_id, title, description, now_iso(), exam_id))
        conn.commit()
    flash_ui("Exam updated.", "success")
    return redirect(url_for("teacher_exam_detail", exam_id=exam_id))


@app.post("/teacher/exams/<int:exam_id>/publish")
@teacher_required
def teacher_exam_publish(exam_id):
    verify_csrf()
    with get_db() as conn:
        exam = exam_row(conn, exam_id)
        if not exam:
            abort(404)
        new_value = 0 if exam["is_published"] else 1
        if new_value:
            valid_versions = conn.execute(
                """SELECT COUNT(*) AS n FROM exam_versions v WHERE v.exam_id=%s AND v.is_active=1
                AND EXISTS(SELECT 1 FROM exam_version_questions q WHERE q.version_id=v.id)""",
                (exam_id,),
            ).fetchone()["n"]
            if not valid_versions:
                flash_ui("Add questions to at least one active version before publishing.", "error")
                return redirect(url_for("teacher_exam_detail", exam_id=exam_id))
        conn.execute("UPDATE exams SET is_published=%s,updated_at=%s WHERE id=%s", (new_value, now_iso(), exam_id))
        conn.commit()
    flash_ui("Exam updated.", "success")
    return redirect(url_for("teacher_exam_detail", exam_id=exam_id))


@app.post("/teacher/exams/<int:exam_id>/archive")
@teacher_required
def teacher_exam_archive(exam_id):
    verify_csrf()
    with get_db() as conn:
        if not exam_row(conn, exam_id):
            abort(404)
        conn.execute("UPDATE exams SET is_published=0,is_archived=1,updated_at=%s WHERE id=%s", (now_iso(), exam_id))
        conn.execute("UPDATE exam_assignments SET is_active=0,updated_at=%s WHERE exam_id=%s", (now_iso(), exam_id))
        conn.commit()
    flash_ui("Exam archived.", "success")
    return redirect(url_for("teacher_exams"))


@app.post("/teacher/exams/<int:exam_id>/versions/new")
@teacher_required
def teacher_exam_version_new(exam_id):
    verify_csrf()
    name = clean_name(request.form.get("name"), 60)
    if not name:
        flash_ui("Version name is required.", "error")
        return redirect(url_for("teacher_exam_detail", exam_id=exam_id))
    try:
        with get_db() as conn:
            if not exam_row(conn, exam_id):
                abort(404)
            version_id = conn.execute(
                "INSERT INTO exam_versions(exam_id,name,is_active,created_at,updated_at) VALUES(%s,%s,1,%s,%s) RETURNING id",
                (exam_id, name, now_iso(), now_iso()),
            ).fetchone()["id"]
            conn.commit()
    except IntegrityError:
        flash_ui("A version with that name already exists.", "error")
        return redirect(url_for("teacher_exam_detail", exam_id=exam_id))
    flash_ui("Version created.", "success")
    return redirect(url_for("teacher_exam_version_questions", exam_id=exam_id, version_id=version_id))


@app.post("/teacher/exams/<int:exam_id>/versions/<int:version_id>/edit")
@teacher_required
def teacher_exam_version_edit(exam_id, version_id):
    verify_csrf()
    name = clean_name(request.form.get("name"), 60)
    if not name:
        flash_ui("Version name is required.", "error")
        return redirect(url_for("teacher_exam_detail", exam_id=exam_id))
    try:
        with get_db() as conn:
            if not exam_row(conn, exam_id):
                abort(404)
            row = conn.execute("SELECT 1 FROM exam_versions WHERE id=%s AND exam_id=%s AND is_active=1", (version_id, exam_id)).fetchone()
            if not row:
                abort(404)
            conn.execute("UPDATE exam_versions SET name=%s,updated_at=%s WHERE id=%s", (name, now_iso(), version_id))
            conn.commit()
    except IntegrityError:
        flash_ui("A version with that name already exists.", "error")
        return redirect(url_for("teacher_exam_detail", exam_id=exam_id))
    flash_ui("Exam updated.", "success")
    return redirect(url_for("teacher_exam_detail", exam_id=exam_id))


@app.post("/teacher/exams/<int:exam_id>/versions/<int:version_id>/duplicate")
@teacher_required
def teacher_exam_version_duplicate(exam_id, version_id):
    verify_csrf()
    with get_db() as conn:
        if not exam_row(conn, exam_id):
            abort(404)
        src = conn.execute("SELECT * FROM exam_versions WHERE id=%s AND exam_id=%s AND is_active=1", (version_id, exam_id)).fetchone()
        if not src:
            abort(404)
        base = src["name"] + " copy"
        name = base
        i = 2
        while conn.execute("SELECT 1 FROM exam_versions WHERE exam_id=%s AND name=%s ", (exam_id, name)).fetchone():
            name = f"{base} {i}"
            i += 1
        new_id = conn.execute(
            "INSERT INTO exam_versions(exam_id,name,is_active,created_at,updated_at) VALUES(%s,%s,1,%s,%s) RETURNING id",
            (exam_id, name, now_iso(), now_iso()),
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO exam_version_questions(version_id,question_id,position) SELECT %s,question_id,position FROM exam_version_questions WHERE version_id=%s",
            (new_id, version_id),
        )
        conn.commit()
    flash_ui("Version duplicated.", "success")
    return redirect(url_for("teacher_exam_version_questions", exam_id=exam_id, version_id=new_id))


@app.post("/teacher/exams/<int:exam_id>/versions/<int:version_id>/archive")
@teacher_required
def teacher_exam_version_archive(exam_id, version_id):
    verify_csrf()
    with get_db() as conn:
        exam = exam_row(conn, exam_id)
        version = conn.execute("SELECT * FROM exam_versions WHERE id=%s AND exam_id=%s AND is_active=1", (version_id, exam_id)).fetchone()
        if not exam or not version:
            abort(404)
        fixed_use = conn.execute(
            "SELECT 1 FROM exam_assignments WHERE exam_id=%s AND fixed_version_id=%s AND version_mode='fixed' AND is_active=1 LIMIT 1",
            (exam_id, version_id),
        ).fetchone()
        if fixed_use:
            flash_ui("This version is used by an active fixed assignment. Change or remove that assignment before archiving it.", "error")
            return redirect(url_for("teacher_exam_detail", exam_id=exam_id))
        if exam["is_published"]:
            active_assignment = conn.execute("SELECT 1 FROM exam_assignments WHERE exam_id=%s AND is_active=1 LIMIT 1", (exam_id,)).fetchone()
            if active_assignment:
                usable_after = conn.execute(
                    """SELECT COUNT(*) AS n FROM exam_versions v
                       WHERE v.exam_id=%s AND v.is_active=1 AND v.id<>%s
                         AND EXISTS(SELECT 1 FROM exam_version_questions q WHERE q.version_id=v.id)""",
                    (exam_id, version_id),
                ).fetchone()["n"]
                if not usable_after:
                    flash_ui("A published exam with active assignments must keep at least one usable version.", "error")
                    return redirect(url_for("teacher_exam_detail", exam_id=exam_id))
        conn.execute("UPDATE exam_versions SET is_active=0,updated_at=%s WHERE id=%s", (now_iso(), version_id))
        conn.commit()
    flash_ui("Version archived.", "success")
    return redirect(url_for("teacher_exam_detail", exam_id=exam_id))


@app.post("/teacher/exams/<int:exam_id>/versions/<int:version_id>/restore")
@teacher_required
def teacher_exam_version_restore(exam_id, version_id):
    verify_csrf()
    with get_db() as conn:
        if not exam_row(conn, exam_id):
            abort(404)
        version = conn.execute("SELECT 1 FROM exam_versions WHERE id=%s AND exam_id=%s AND is_active=0", (version_id, exam_id)).fetchone()
        if not version:
            abort(404)
        conn.execute("UPDATE exam_versions SET is_active=1,updated_at=%s WHERE id=%s", (now_iso(), version_id))
        conn.commit()
    flash_ui("Version restored.", "success")
    return redirect(url_for("teacher_exam_detail", exam_id=exam_id))


@app.get("/teacher/exams/<int:exam_id>/versions/<int:version_id>/questions")
@teacher_required
def teacher_exam_version_questions(exam_id, version_id):
    search = request.args.get("q", "").strip()
    cat = request.args.get("category", "").strip()
    typ = request.args.get("type", "").strip()
    with get_db() as conn:
        exam = exam_row(conn, exam_id)
        version = conn.execute("SELECT * FROM exam_versions WHERE id=%s AND exam_id=%s AND is_active=1", (version_id, exam_id)).fetchone()
        if not exam or not version:
            abort(404)
        clauses = ["q.subject_id=%s", "q.teacher_id=%s", "q.is_archived=0", "c.is_archived=0"]
        params = [exam["subject_id"], current_teacher_id()]
        if search:
            clauses.append("q.prompt ILIKE %s")
            params.append(f"%{search}%")
        if cat.isdigit():
            clauses.append("q.category_id=%s")
            params.append(int(cat))
        if typ in TYPE_LABELS:
            clauses.append("q.type=%s")
            params.append(typ)
        rows = conn.execute(
            f"""SELECT q.*,c.name AS category_name,s.name AS subject_name,
                CASE WHEN evq.question_id IS NULL THEN 0 ELSE 1 END AS selected
                FROM question_bank q JOIN categories c ON c.id=q.category_id JOIN subjects s ON s.id=q.subject_id
                LEFT JOIN exam_version_questions evq ON evq.version_id=%s AND evq.question_id=q.id
                WHERE {' AND '.join(clauses)} ORDER BY selected DESC,c.sort_order,c.name,q.type,q.updated_at DESC""",
            [version_id, *params],
        ).fetchall()
        categories = conn.execute(
            "SELECT * FROM categories WHERE subject_id=%s AND teacher_id=%s AND is_archived=0 ORDER BY sort_order,name",
            (exam["subject_id"], current_teacher_id()),
        ).fetchall()
        selected_ids = [r["question_id"] for r in conn.execute("SELECT question_id FROM exam_version_questions WHERE version_id=%s ORDER BY position", (version_id,)).fetchall()]
        unavailable_ids = {r["id"] for r in rows if not listening_row_usable(r)}
    return render_template(
        "teacher/exams/version_questions.html",
        exam=exam,
        version=version,
        rows=rows,
        categories=categories,
        selected_ids=selected_ids,
        unavailable_ids=unavailable_ids,
        type_labels=localized_type_labels(),
        filters={"q": search, "category": cat, "type": typ},
    )


@app.post("/teacher/exams/<int:exam_id>/versions/<int:version_id>/questions")
@teacher_required
def teacher_exam_version_questions_save(exam_id, version_id):
    verify_csrf()
    ids = []
    for qid in request.form.getlist("question_ids"):
        if qid and qid not in ids:
            ids.append(qid)
    with get_db() as conn:
        exam = exam_row(conn, exam_id)
        version = conn.execute("SELECT 1 FROM exam_versions WHERE id=%s AND exam_id=%s AND is_active=1", (version_id, exam_id)).fetchone()
        if not exam or not version:
            abort(404)
        valid = []
        if ids:
            ph = ",".join("%s" for _ in ids)
            candidate_rows = conn.execute(
                f"SELECT * FROM question_bank WHERE id IN ({ph}) AND teacher_id=%s AND subject_id=%s AND is_archived=0",
                [*ids, current_teacher_id(), exam["subject_id"]],
            ).fetchall()
            valid = [r["id"] for r in candidate_rows if listening_row_usable(r)]
        conn.execute("DELETE FROM exam_version_questions WHERE version_id=%s", (version_id,))
        for pos, qid in enumerate(ids):
            if qid in valid:
                conn.execute("INSERT INTO exam_version_questions(version_id,question_id,position) VALUES(%s,%s,%s)", (version_id, qid, pos))
        conn.execute("UPDATE exam_versions SET updated_at=%s WHERE id=%s", (now_iso(), version_id))
        conn.execute("UPDATE exams SET updated_at=%s WHERE id=%s", (now_iso(), exam_id))
        conn.commit()
    flash_ui("Question selection saved.", "success")
    return redirect(url_for("teacher_exam_version_questions", exam_id=exam_id, version_id=version_id))


@app.post("/teacher/exams/<int:exam_id>/assign")
@teacher_required
def teacher_exam_assign(exam_id):
    verify_csrf()
    try:
        section_id = int(request.form.get("section_id", "0"))
    except ValueError:
        section_id = 0
    mode = request.form.get("version_mode", "random")
    if mode not in {"random", "fixed"}:
        mode = "random"
    fixed = None
    if mode == "fixed":
        try:
            fixed = int(request.form.get("fixed_version_id", "0"))
        except ValueError:
            fixed = None
    with get_db() as conn:
        exam = exam_row(conn, exam_id)
        section = conn.execute("SELECT 1 FROM sections WHERE id=%s AND is_archived=0", (section_id,)).fetchone()
        if not exam or not section:
            flash_ui("Choose a valid section.", "error")
            return redirect(url_for("teacher_exam_detail", exam_id=exam_id))
        if mode == "fixed":
            valid = conn.execute(
                """SELECT 1 FROM exam_versions v WHERE v.id=%s AND v.exam_id=%s AND v.is_active=1
                AND EXISTS(SELECT 1 FROM exam_version_questions q WHERE q.version_id=v.id)""",
                (fixed, exam_id),
            ).fetchone()
            if not valid:
                flash_ui("Choose a valid fixed version.", "error")
                return redirect(url_for("teacher_exam_detail", exam_id=exam_id))
        conn.execute(
            """INSERT INTO exam_assignments(exam_id,section_id,version_mode,fixed_version_id,is_active,created_at,updated_at)
            VALUES(%s,%s,%s,%s,1,%s,%s) ON CONFLICT(exam_id,section_id) DO UPDATE SET version_mode=excluded.version_mode,
            fixed_version_id=excluded.fixed_version_id,is_active=1,updated_at=excluded.updated_at""",
            (exam_id, section_id, mode, fixed, now_iso(), now_iso()),
        )
        conn.commit()
    flash_ui("Assignment saved.", "success")
    return redirect(url_for("teacher_exam_detail", exam_id=exam_id))


@app.post("/teacher/exams/<int:exam_id>/assignments/<int:assignment_id>/remove")
@teacher_required
def teacher_exam_assignment_remove(exam_id, assignment_id):
    verify_csrf()
    with get_db() as conn:
        if not exam_row(conn, exam_id):
            abort(404)
        row = conn.execute("SELECT * FROM exam_assignments WHERE id=%s AND exam_id=%s", (assignment_id, exam_id)).fetchone()
        if not row:
            abort(404)
        conn.execute("UPDATE exam_assignments SET is_active=0,updated_at=%s WHERE id=%s", (now_iso(), assignment_id))
        conn.commit()
    flash_ui("Assignment removed.", "success")
    return redirect(url_for("teacher_exam_detail", exam_id=exam_id))
