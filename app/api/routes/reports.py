import csv
import io
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from openpyxl import Workbook

from app.db.session import get_db
from app.models import (
    User, Group, Student, ScheduleInstance, ScheduleTemplate, StudentRecord
)
from app.core.dependencies import (
    get_current_user, ensure_report_access, restrict_to_teacher_classes
)
from app.services.report_service import build_report_rows, build_summary_stats

router = APIRouter(tags=["reports"])


@router.get("/api/reports/journal")
async def get_journal_report(
    group_id: int,
    date_from: date,
    date_to: date,
    discipline_id: Optional[int] = None,
    format: str = "csv",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ensure_report_access(current_user)

    if date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must be earlier than date_to")

    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    students = db.query(Student).filter(Student.group_id == group_id).order_by(Student.full_name).all()
    if not students:
        raise HTTPException(status_code=404, detail="Group has no students")

    instances_query = db.query(ScheduleInstance).options(
        joinedload(ScheduleInstance.template).joinedload(ScheduleTemplate.discipline),
        joinedload(ScheduleInstance.template).joinedload(ScheduleTemplate.groups),
        joinedload(ScheduleInstance.teacher)
    ).join(ScheduleInstance.template).join(ScheduleTemplate.groups).filter(
        Group.id == group_id,
        ScheduleInstance.date >= date_from,
        ScheduleInstance.date <= date_to
    )

    if discipline_id:
        instances_query = instances_query.filter(ScheduleTemplate.discipline_id == discipline_id)

    instances_query = restrict_to_teacher_classes(instances_query, current_user)
    instances = instances_query.order_by(ScheduleInstance.date, ScheduleInstance.id).distinct().all()

    if not instances:
        raise HTTPException(status_code=404, detail="No lessons found for selected filters")

    instance_ids = [inst.id for inst in instances]
    student_ids = [student.id for student in students]

    records = db.query(StudentRecord).options(joinedload(StudentRecord.student)).filter(
        StudentRecord.schedule_instance_id.in_(instance_ids),
        StudentRecord.student_id.in_(student_ids)
    ).all()
    records_map = {(r.schedule_instance_id, r.student_id): r for r in records}

    rows = build_report_rows(instances, students, records_map)
    filename_base = f"journal_{group.name}_{date_from}_{date_to}"

    if format == "json":
        return {
            "group": {"id": group.id, "name": group.name},
            "period": {"from": str(date_from), "to": str(date_to)},
            "rows": rows
        }

    if format == "xlsx":
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Журнал"
        worksheet.append(["Дата", "Дисциплина", "Тип занятия", "Студент", "Статус", "Оценка"])
        for row in rows:
            worksheet.append([
                row["date"],
                row["discipline"],
                row["lesson_type"],
                row["student"],
                row["status"],
                row["grade"] if row["grade"] is not None else ""
            ])
        stream = io.BytesIO()
        workbook.save(stream)
        stream.seek(0)
        headers = {"Content-Disposition": f"attachment; filename={filename_base}.xlsx"}
        return StreamingResponse(
            stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers
        )

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["Дата", "Дисциплина", "Тип занятия", "Студент", "Статус", "Оценка"])
    for row in rows:
        writer.writerow([
            row["date"],
            row["discipline"],
            row["lesson_type"],
            row["student"],
            row["status"],
            row["grade"] if row["grade"] is not None else ""
        ])

    headers = {"Content-Disposition": f"attachment; filename={filename_base}.csv"}
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers=headers)


@router.get("/api/reports/summary")
async def get_summary_report(
    group_id: int,
    date_from: date,
    date_to: date,
    discipline_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ensure_report_access(current_user)

    if date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must be earlier than date_to")

    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    students = db.query(Student).filter(Student.group_id == group_id).order_by(Student.full_name).all()
    if not students:
        raise HTTPException(status_code=404, detail="Group has no students")

    instances_query = db.query(ScheduleInstance).options(
        joinedload(ScheduleInstance.template).joinedload(ScheduleTemplate.discipline),
        joinedload(ScheduleInstance.template).joinedload(ScheduleTemplate.groups)
    ).join(ScheduleInstance.template).join(ScheduleTemplate.groups).filter(
        Group.id == group_id,
        ScheduleInstance.date >= date_from,
        ScheduleInstance.date <= date_to
    )

    if discipline_id:
        instances_query = instances_query.filter(ScheduleTemplate.discipline_id == discipline_id)

    instances_query = restrict_to_teacher_classes(instances_query, current_user)
    instances = instances_query.order_by(ScheduleInstance.date, ScheduleInstance.id).distinct().all()

    instance_ids = [inst.id for inst in instances]
    student_ids = [student.id for student in students]

    if not instance_ids:
        return {
            "group": {"id": group.id, "name": group.name},
            "period": {"from": str(date_from), "to": str(date_to)},
            "attendance": {"total_lessons": 0, "by_status": {}, "attendance_rate": 0},
            "grades": {"overall_average": None, "student_averages": []}
        }

    records = db.query(StudentRecord).filter(
        StudentRecord.schedule_instance_id.in_(instance_ids),
        StudentRecord.student_id.in_(student_ids)
    ).all()

    stats = build_summary_stats(instances, students, records)

    return {
        "group": {"id": group.id, "name": group.name},
        "period": {"from": str(date_from), "to": str(date_to)},
        "filters": {"discipline_id": discipline_id},
        "lessons_found": len(instance_ids),
        **stats
    }
