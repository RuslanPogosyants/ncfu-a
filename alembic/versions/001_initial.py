"""Initial schema — all tables

Revision ID: 001
Revises:
Create Date: 2026-04-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("hashed_password", sa.String(), nullable=True),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("role", sa.Enum("admin", "teacher", name="userrole"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_groups_id", "groups", ["id"], unique=False)
    op.create_index("ix_groups_name", "groups", ["name"], unique=True)

    op.create_table(
        "disciplines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_disciplines_id", "disciplines", ["id"], unique=False)
    op.create_index("ix_disciplines_name", "disciplines", ["name"], unique=True)

    op.create_table(
        "semesters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_semesters_id", "semesters", ["id"], unique=False)
    op.create_index("ix_semesters_name", "semesters", ["name"], unique=False)

    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("face_encoding", sa.String(), nullable=True),
        sa.Column("fingerprint_template", sa.String(), nullable=True),
        sa.Column("group_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_students_id", "students", ["id"], unique=False)
    op.create_index("ix_students_full_name", "students", ["full_name"], unique=False)
    op.create_index("ix_students_group_id", "students", ["group_id"], unique=False)

    op.create_table(
        "teacher_disciplines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=True),
        sa.Column("discipline_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["discipline_id"], ["disciplines.id"]),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_teacher_disciplines_id", "teacher_disciplines", ["id"], unique=False)

    op.create_table(
        "schedule_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("semester_id", sa.Integer(), nullable=True),
        sa.Column("discipline_id", sa.Integer(), nullable=True),
        sa.Column("classroom", sa.String(), nullable=True),
        sa.Column("teacher_id", sa.Integer(), nullable=True),
        sa.Column(
            "lesson_type",
            sa.Enum("Л", "С", "ЛР", name="lessontype"),
            nullable=True,
        ),
        sa.Column("day_of_week", sa.Integer(), nullable=True),
        sa.Column("time_start", sa.String(), nullable=True),
        sa.Column("time_end", sa.String(), nullable=True),
        sa.Column(
            "week_type",
            sa.Enum("even", "odd", "both", name="weektype"),
            nullable=True,
        ),
        sa.Column("is_stream", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["discipline_id"], ["disciplines.id"]),
        sa.ForeignKeyConstraint(["semester_id"], ["semesters.id"]),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_schedule_templates_id", "schedule_templates", ["id"], unique=False)

    op.create_table(
        "template_groups",
        sa.Column("schedule_template_id", sa.Integer(), nullable=True),
        sa.Column("group_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["schedule_template_id"], ["schedule_templates.id"]),
    )

    op.create_table(
        "schedule_instances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=True),
        sa.Column("semester_id", sa.Integer(), nullable=True),
        sa.Column("date", sa.Date(), nullable=True),
        sa.Column("classroom", sa.String(), nullable=True),
        sa.Column("teacher_id", sa.Integer(), nullable=True),
        sa.Column("is_cancelled", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["semester_id"], ["semesters.id"]),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["template_id"], ["schedule_templates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_schedule_instances_id", "schedule_instances", ["id"], unique=False)
    op.create_index("ix_schedule_instances_date", "schedule_instances", ["date"], unique=False)
    op.create_index(
        "ix_schedule_instances_semester_id", "schedule_instances", ["semester_id"], unique=False
    )

    op.create_table(
        "student_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=True),
        sa.Column("schedule_instance_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "present", "absent", "excused", "auto_detected", "fingerprint_detected",
                name="studentstatus",
            ),
            nullable=True,
        ),
        sa.Column("grade", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["schedule_instance_id"], ["schedule_instances.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_student_records_id", "student_records", ["id"], unique=False)


def downgrade() -> None:
    op.drop_table("student_records")
    op.drop_table("schedule_instances")
    op.drop_table("template_groups")
    op.drop_table("schedule_templates")
    op.drop_table("teacher_disciplines")
    op.drop_table("students")
    op.drop_table("semesters")
    op.drop_table("disciplines")
    op.drop_table("groups")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS lessontype")
    op.execute("DROP TYPE IF EXISTS weektype")
    op.execute("DROP TYPE IF EXISTS studentstatus")
