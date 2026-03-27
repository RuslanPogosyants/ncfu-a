import logging
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User, Student, Group, Discipline, Semester, ScheduleInstance, StudentRecord, StudentStatus, UserRole
from app.core.dependencies import get_current_user, check_admin
from app.services import biometric_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["biometric", "dashboard"])

# Ограничение размера загружаемого изображения: 10 МБ
_MAX_IMAGE_BYTES = 10 * 1024 * 1024
_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}


def _validate_image_upload(file: UploadFile) -> None:
    """Проверяет content-type загружаемого файла."""
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Неподдерживаемый тип файла: {file.content_type}. "
                   f"Допустимые форматы: JPEG, PNG, WebP, BMP.",
        )


async def _read_image_bytes(file: UploadFile) -> bytes:
    """Читает файл с проверкой максимального размера."""
    data = await file.read(_MAX_IMAGE_BYTES + 1)
    if len(data) > _MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Файл превышает максимальный допустимый размер {_MAX_IMAGE_BYTES // (1024 * 1024)} МБ.",
        )
    return data


# ── Face biometric endpoints ─────────────────────────────────────────────────

@router.post("/api/students/{student_id}/upload-face")
async def upload_student_face(
    student_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_admin(current_user)
    _validate_image_upload(file)

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Студент не найден")

    image_bytes = await _read_image_bytes(file)
    # Передаём объект студента напрямую — исключаем повторный запрос к БД в сервисе
    success = biometric_service.get_face_service().save_student_face(student, image_bytes, db)

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Не удалось распознать лицо на фото. "
                   "Убедитесь, что на фото чётко видно одно лицо, или проверьте доступность моделей dlib.",
        )

    return {"success": True, "message": f"Фото студента {student.full_name} успешно сохранено"}


@router.post("/api/schedules/{schedule_id}/recognize-attendance")
async def recognize_attendance(
    schedule_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _validate_image_upload(file)

    schedule = db.query(ScheduleInstance).filter(ScheduleInstance.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Занятие не найдено")

    template = schedule.template
    teacher_id = schedule.teacher_id if schedule.teacher_id else template.teacher_id

    if current_user.role != UserRole.ADMIN and current_user.id != teacher_id:
        raise HTTPException(status_code=403, detail="Нет прав для редактирования этого занятия")

    group_ids = [g.id for g in template.groups]
    students = db.query(Student).filter(Student.group_id.in_(group_ids)).all()

    if not students:
        raise HTTPException(status_code=404, detail="Студенты не найдены")

    image_bytes = await _read_image_bytes(file)
    return biometric_service.process_face_recognition(db, schedule, students, image_bytes)


@router.get("/api/students/{student_id}/has-face")
async def check_student_face(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Студент не найден")

    return {
        "student_id": student_id,
        "has_face": student.face_encoding is not None,
        "recognition_available": biometric_service.get_face_service().is_recognition_available,
    }


@router.get("/api/groups/{group_id}/face-stats")
async def get_group_face_stats(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    students = db.query(Student).filter(Student.group_id == group_id).all()

    total = len(students)
    with_face = sum(1 for s in students if s.face_encoding is not None)

    return {
        "group_id": group_id,
        "total_students": total,
        "students_with_face": with_face,
        "students_without_face": total - with_face,
        "percentage": (with_face / total * 100) if total > 0 else 0,
        "recognition_available": biometric_service.get_face_service().is_recognition_available,
    }


# ── Dashboard ────────────────────────────────────────────────────────────────

@router.get("/api/dashboard/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    total_students = db.query(Student).count()
    total_groups = db.query(Group).count()
    total_disciplines_count = db.query(Discipline).count()

    students_with_face = db.query(Student).filter(Student.face_encoding.isnot(None)).count()
    face_coverage = (students_with_face / total_students * 100) if total_students > 0 else 0

    date_30_days_ago = date.today() - timedelta(days=30)
    recent_instances = db.query(ScheduleInstance).filter(
        ScheduleInstance.date >= date_30_days_ago,
        ScheduleInstance.date <= date.today()
    ).all()

    total_lessons_30d = len(recent_instances)

    if total_lessons_30d > 0:
        instance_ids = [inst.id for inst in recent_instances]
        records = db.query(StudentRecord).filter(
            StudentRecord.schedule_instance_id.in_(instance_ids)
        ).all()

        total_records = len(records)
        present_statuses = {StudentStatus.PRESENT, StudentStatus.AUTO_DETECTED, StudentStatus.FINGERPRINT_DETECTED}
        present_records = len([r for r in records if r.status in present_statuses])
        attendance_rate_30d = (present_records / total_records * 100) if total_records > 0 else 0

        auto_detected = len([r for r in records if r.status == StudentStatus.AUTO_DETECTED])
        fingerprint_detected = len([r for r in records if r.status == StudentStatus.FINGERPRINT_DETECTED])
        auto_detection_rate = ((auto_detected + fingerprint_detected) / total_records * 100) if total_records > 0 else 0
    else:
        attendance_rate_30d = 0
        auto_detection_rate = 0
        total_records = 0
        instance_ids = []

    groups = db.query(Group).all()
    group_stats = []

    for group in groups[:10]:
        group_students = db.query(Student).filter(Student.group_id == group.id).all()
        if not group_students:
            continue

        student_ids = [s.id for s in group_students]

        group_records = db.query(StudentRecord).filter(
            StudentRecord.student_id.in_(student_ids),
            StudentRecord.schedule_instance_id.in_(instance_ids) if total_lessons_30d > 0 else False
        ).all()

        if group_records:
            group_total = len(group_records)
            present_statuses = {StudentStatus.PRESENT, StudentStatus.AUTO_DETECTED, StudentStatus.FINGERPRINT_DETECTED}
            group_present = len([r for r in group_records if r.status in present_statuses])
            group_rate = (group_present / group_total * 100) if group_total > 0 else 0

            group_stats.append({
                "id": group.id,
                "name": group.name,
                "attendance_rate": round(group_rate, 1),
                "total_records": group_total
            })

    group_stats.sort(key=lambda x: x['attendance_rate'], reverse=True)
    top_groups = group_stats[:3]
    bottom_groups = sorted(group_stats, key=lambda x: x['attendance_rate'])[:3]

    active_semester = db.query(Semester).filter(Semester.is_active == True).first()

    return {
        "overview": {
            "total_students": total_students,
            "total_groups": total_groups,
            "total_disciplines": total_disciplines_count,
            "students_with_face": students_with_face,
            "face_coverage_percentage": round(face_coverage, 1)
        },
        "attendance_30d": {
            "total_lessons": total_lessons_30d,
            "total_records": total_records,
            "attendance_rate": round(attendance_rate_30d, 1),
            "auto_detection_rate": round(auto_detection_rate, 1)
        },
        "top_groups": top_groups,
        "bottom_groups": bottom_groups,
        "active_semester": {
            "id": active_semester.id,
            "name": active_semester.name,
            "start_date": str(active_semester.start_date),
            "end_date": str(active_semester.end_date)
        } if active_semester else None
    }
