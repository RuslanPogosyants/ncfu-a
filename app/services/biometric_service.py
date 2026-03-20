"""
Сервис биометрии (распознавание лиц).
Управляет thread-safe lazy-singleton FaceRecognitionService и оркестрирует
логику обновления записей посещаемости после распознавания.
"""
import logging
import threading
from sqlalchemy.orm import Session

from app.models import Student, StudentRecord, StudentStatus, ScheduleInstance

logger = logging.getLogger(__name__)

_face_service = None
_face_service_lock = threading.Lock()


def get_face_service():
    global _face_service
    if _face_service is None:
        with _face_service_lock:
            if _face_service is None:  # double-checked locking
                from face_recognition_service import FaceRecognitionService
                from app.core.config import settings
                _face_service = FaceRecognitionService(tolerance=settings.FACE_RECOGNITION_TOLERANCE)
    return _face_service


def process_face_recognition(
    db: Session,
    schedule: ScheduleInstance,
    students: list,
    image_bytes: bytes,
) -> dict:
    """
    Распознаёт студентов на фото и обновляет записи посещаемости.
    Если модели не загружены — возвращает ответ с recognized_count=0 без падения.
    """
    service = get_face_service()

    if not service.is_recognition_available:
        logger.warning(
            "recognize_students для занятия id=%s вызван в простом режиме — "
            "записи посещаемости не обновлены.",
            schedule.id,
        )
        return {
            "success": False,
            "recognized_count": 0,
            "total_students": len(students),
            "total_faces": 0,
            "recognition_rate": "0.0%",
            "updated_count": 0,
            "message": "Модели распознавания лиц недоступны. Загрузите .dat файлы.",
            "stats": service.get_recognition_stats([], 0, len(students)),
        }

    recognized_ids, total_faces = service.recognize_students(image_bytes, students)

    updated_count = 0
    for student in students:
        record = db.query(StudentRecord).filter(
            StudentRecord.student_id == student.id,
            StudentRecord.schedule_instance_id == schedule.id
        ).first()

        if student.id in recognized_ids:
            if record:
                record.status = StudentStatus.AUTO_DETECTED
            else:
                record = StudentRecord(
                    student_id=student.id,
                    schedule_instance_id=schedule.id,
                    status=StudentStatus.AUTO_DETECTED
                )
                db.add(record)
            updated_count += 1
        else:
            if not record:
                record = StudentRecord(
                    student_id=student.id,
                    schedule_instance_id=schedule.id,
                    status=StudentStatus.ABSENT
                )
                db.add(record)

    db.commit()

    stats = service.get_recognition_stats(recognized_ids, total_faces, len(students))

    return {
        "success": True,
        "recognized_count": len(recognized_ids),
        "total_students": len(students),
        "total_faces": total_faces,
        "recognition_rate": f"{stats['recognition_rate'] * 100:.1f}%",
        "updated_count": updated_count,
        "stats": stats,
    }
