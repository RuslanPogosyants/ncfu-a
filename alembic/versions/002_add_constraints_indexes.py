"""Add unique constraint and indexes

Revision ID: 002
Revises: 001
Create Date: 2026-04-09

Adds:
  - UNIQUE constraint on student_records(student_id, schedule_instance_id)
  - Index on student_records.student_id
  - Index on student_records.schedule_instance_id
"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Unique constraint: one attendance record per student per lesson
    op.create_unique_constraint(
        "uq_student_record",
        "student_records",
        ["student_id", "schedule_instance_id"],
    )

    # Indexes for frequent query patterns
    op.create_index(
        "ix_student_records_student_id",
        "student_records",
        ["student_id"],
        unique=False,
    )
    op.create_index(
        "ix_student_records_schedule_instance_id",
        "student_records",
        ["schedule_instance_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_student_records_schedule_instance_id", table_name="student_records")
    op.drop_index("ix_student_records_student_id", table_name="student_records")
    op.drop_constraint("uq_student_record", "student_records", type_="unique")
