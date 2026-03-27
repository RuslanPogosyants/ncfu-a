from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User, Student, ScheduleInstance, StudentRecord, StudentStatus, UserRole
from app.core.dependencies import get_current_user
from app.services import attendance_service

router = APIRouter(tags=["attendance"])


@router.get("/api/schedules/{schedule_id}/records")
async def get_schedule_records(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    instance = db.query(ScheduleInstance).filter(ScheduleInstance.id == schedule_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Schedule not found")

    template = instance.template

    if current_user.role == UserRole.TEACHER:
        assigned_teacher = instance.teacher if instance.teacher_id else template.teacher
        if not assigned_teacher or assigned_teacher.id != current_user.id:
            raise HTTPException(status_code=403, detail="You can only view records for your own classes")

    students = []
    for group in template.groups:
        students.extend(db.query(Student).filter(Student.group_id == group.id).all())

    existing_records = db.query(StudentRecord).filter(
        StudentRecord.schedule_instance_id == schedule_id
    ).all()
    records_dict = {r.student_id: r for r in existing_records}

    result = []
    for student in students:
        record = records_dict.get(student.id)
        result.append({
            "student_id": student.id,
            "student_name": student.full_name,
            "group_name": student.group.name,
            "status": record.status.value if record else StudentStatus.PRESENT.value,
            "grade": record.grade if record else None,
            "record_id": record.id if record else None
        })

    return result


@router.post("/api/records")
async def create_or_update_record(
    student_id: int = Form(...),
    schedule_id: int = Form(...),
    status: str = Form(...),
    grade: Optional[float] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return attendance_service.create_or_update_record(
        db=db,
        schedule_id=schedule_id,
        student_id=student_id,
        status=status,
        grade=grade,
        current_user=current_user,
    )
