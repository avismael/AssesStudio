"""Teacher-owned subjects and categories.

Revision ID: 20260902_0001
Revises: 20260816_0001
"""

from alembic import op


revision = "20260902_0001"
down_revision = "20260816_0001"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.exec_driver_sql("ALTER TABLE subjects ADD COLUMN teacher_id BIGINT")
    conn.exec_driver_sql("ALTER TABLE categories ADD COLUMN teacher_id BIGINT")
    conn.exec_driver_sql("ALTER TABLE subjects DROP CONSTRAINT IF EXISTS subjects_name_key")

    teachers = [row["id"] for row in conn.exec_driver_sql("SELECT id FROM teachers ORDER BY id").mappings().all()]
    subject_rows = conn.exec_driver_sql("SELECT * FROM subjects ORDER BY id").mappings().all()
    category_rows = conn.exec_driver_sql("SELECT * FROM categories ORDER BY id").mappings().all()
    question_rows = conn.exec_driver_sql("SELECT id,teacher_id,subject_id,category_id FROM question_bank ORDER BY id").mappings().all()
    exam_rows = conn.exec_driver_sql("SELECT id,teacher_id,subject_id FROM exams ORDER BY id").mappings().all()

    subject_map = {}
    for teacher_id in teachers:
        for subject in subject_rows:
            new_id = conn.exec_driver_sql(
                """INSERT INTO subjects(teacher_id,name,description,is_archived,created_at,updated_at)
                   VALUES(%s,%s,%s,%s,%s,%s) RETURNING id""",
                (teacher_id, subject["name"], subject["description"], subject["is_archived"], subject["created_at"], subject["updated_at"]),
            ).scalar_one()
            subject_map[(teacher_id, subject["id"])] = new_id

    category_map = {}
    for teacher_id in teachers:
        for category in category_rows:
            new_id = conn.exec_driver_sql(
                """INSERT INTO categories(teacher_id,subject_id,name,description,sort_order,is_archived,created_at,updated_at)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (
                    teacher_id,
                    subject_map[(teacher_id, category["subject_id"])],
                    category["name"],
                    category["description"],
                    category["sort_order"],
                    category["is_archived"],
                    category["created_at"],
                    category["updated_at"],
                ),
            ).scalar_one()
            category_map[(teacher_id, category["id"])] = new_id

    for question in question_rows:
        conn.exec_driver_sql(
            "UPDATE question_bank SET subject_id=%s, category_id=%s WHERE id=%s",
            (
                subject_map[(question["teacher_id"], question["subject_id"])],
                category_map[(question["teacher_id"], question["category_id"])],
                question["id"],
            ),
        )

    for exam in exam_rows:
        conn.exec_driver_sql(
            "UPDATE exams SET subject_id=%s WHERE id=%s",
            (subject_map[(exam["teacher_id"], exam["subject_id"])] , exam["id"]),
        )

    conn.exec_driver_sql("DELETE FROM categories WHERE teacher_id IS NULL")
    conn.exec_driver_sql("DELETE FROM subjects WHERE teacher_id IS NULL")

    conn.exec_driver_sql("ALTER TABLE subjects ALTER COLUMN teacher_id SET NOT NULL")
    conn.exec_driver_sql("ALTER TABLE categories ALTER COLUMN teacher_id SET NOT NULL")
    conn.exec_driver_sql("ALTER TABLE subjects ADD CONSTRAINT subjects_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES teachers(id)")
    conn.exec_driver_sql("ALTER TABLE categories ADD CONSTRAINT categories_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES teachers(id)")
    conn.exec_driver_sql("ALTER TABLE subjects ADD CONSTRAINT subjects_teacher_name_key UNIQUE (teacher_id, name)")
    conn.exec_driver_sql("ALTER TABLE categories ADD CONSTRAINT categories_teacher_subject_name_key UNIQUE (teacher_id, subject_id, name)")
    conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS idx_subjects_teacher ON subjects(teacher_id, is_archived, name)")
    conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS idx_categories_teacher ON categories(teacher_id, subject_id, is_archived, sort_order, name)")


def downgrade():
    conn = op.get_bind()
    conn.exec_driver_sql("DROP INDEX IF EXISTS idx_categories_teacher")
    conn.exec_driver_sql("DROP INDEX IF EXISTS idx_subjects_teacher")
    conn.exec_driver_sql("ALTER TABLE categories DROP CONSTRAINT IF EXISTS categories_teacher_subject_name_key")
    conn.exec_driver_sql("ALTER TABLE subjects DROP CONSTRAINT IF EXISTS subjects_teacher_name_key")
    conn.exec_driver_sql("ALTER TABLE categories DROP CONSTRAINT IF EXISTS categories_teacher_id_fkey")
    conn.exec_driver_sql("ALTER TABLE subjects DROP CONSTRAINT IF EXISTS subjects_teacher_id_fkey")
    conn.exec_driver_sql("ALTER TABLE categories DROP COLUMN IF EXISTS teacher_id")
    conn.exec_driver_sql("ALTER TABLE subjects DROP COLUMN IF EXISTS teacher_id")
    conn.exec_driver_sql("ALTER TABLE subjects ADD CONSTRAINT subjects_name_key UNIQUE (name)")
