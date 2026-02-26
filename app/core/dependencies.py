import math
from typing import Optional
from fastapi import HTTPException
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from app.models import UserRole, StudentStatus, ScheduleInstance, ScheduleTemplate, User

# Re-export get_current_user so route modules have a single import point
from app.core.security import get_current_user  # noqa: F401

MAX_PAGE_SIZE = 100
MIN_GRADE = 2
MAX_GRADE_ALLOWED = 5

STATUS_LABELS = {
    StudentStatus.PRESENT: "Присутствовал",
    StudentStatus.ABSENT: "Отсутствовал",
    StudentStatus.EXCUSED: "Уважительная причина",
    StudentStatus.AUTO_DETECTED: "Присутствовал (авто)",
    StudentStatus.FINGERPRINT_DETECTED: "Присутствовал (отпечаток)"
}

PRESENT_STATUSES = {StudentStatus.PRESENT, StudentStatus.AUTO_DETECTED, StudentStatus.FINGERPRINT_DETECTED}


def normalize_pagination(page: int, page_size: int):
    page = max(1, page or 1)
    page_size = max(1, min(page_size or 20, MAX_PAGE_SIZE))
    return page, page_size


def apply_pagination(query, page: int, page_size: int):
    page, page_size = normalize_pagination(page, page_size)
    total = query.count()
    pages = max(1, math.ceil(total / page_size)) if total else 1
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, {
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": pages
    }


def restrict_to_teacher_classes(query, current_user: User):
    if current_user.role != UserRole.TEACHER:
        return query
    return query.filter(
        or_(
            ScheduleInstance.teacher_id == current_user.id,
            and_(
                ScheduleInstance.teacher_id.is_(None),
                ScheduleTemplate.teacher_id == current_user.id
            )
        )
    )


def validate_grade_value(grade: Optional[float]) -> Optional[int]:
    if grade is None:
        return None
    if not float(grade).is_integer():
        raise HTTPException(status_code=400, detail="Grade must be an integer value")
    grade_int = int(grade)
    if grade_int < MIN_GRADE or grade_int > MAX_GRADE_ALLOWED:
        raise HTTPException(
            status_code=400,
            detail=f"Grade must be between {MIN_GRADE} and {MAX_GRADE_ALLOWED}"
        )
    return grade_int


def check_admin(current_user: User):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")


def ensure_report_access(current_user: User):
    if current_user.role not in (UserRole.ADMIN, UserRole.TEACHER):
        raise HTTPException(status_code=403, detail="Reports available for teachers and admins only")
