"""
Сервис записи посещаемости.
Содержит логику создания/обновления StudentRecord с проверками прав доступа.
"""
from datetime import date
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import ScheduleInstance, StudentRecord, StudentStatus, UserRole, User
from app.core.dependencies import validate_grade_value


def create_or_update_record(
    db: Session,
    schedule_id: int,
    student_id: int,
    status: str,
    grade: Optional[float],
    current_user: User,
) -> dict:
    """
    Создаёт или обновляет запись посещаемости студента на занятии.
    Проверяет, что занятие прошло и не отменено, и что учитель редактирует только своё занятие.
    """
    instance = db.query(ScheduleInstance).filter(ScheduleInstance.id == schedule_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if instance.date >= date.today():
        raise HTTPException(status_code=403, detail="Cannot edit future classes")

    if instance.is_cancelled:
        raise HTTPException(status_code=403, detail="Cannot edit cancelled classes")

    template = instance.template
    teacher = instance.teacher if instance.teacher_id else template.teacher

    if current_user.role == UserRole.TEACHER:
        if teacher.id != current_user.id:
            raise HTTPException(status_code=403, detail="You can only edit records for your own classes")

    record = db.query(StudentRecord).filter(
        StudentRecord.student_id == student_id,
        StudentRecord.schedule_instance_id == schedule_id
    ).first()

    grade_value = validate_grade_value(grade)

    if record:
        record.status = StudentStatus(status)
        record.grade = grade_value
    else:
        record = StudentRecord(
            student_id=student_id,
            schedule_instance_id=schedule_id,
            status=StudentStatus(status),
            grade=grade_value
        )
        db.add(record)

    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "student_id": record.student_id,
        "schedule_instance_id": record.schedule_instance_id,
        "status": record.status.value,
        "grade": record.grade
    }
