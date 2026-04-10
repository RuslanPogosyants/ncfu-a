from datetime import timedelta, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_

from app.db.session import get_db
from app.models import (
    User, Group, Discipline, Semester, ScheduleTemplate, ScheduleInstance,
    UserRole, LessonType, WeekType
)
from app.core.dependencies import (
    get_current_user, check_admin, apply_pagination, restrict_to_teacher_classes
)
from app.services import schedule_service

router = APIRouter(tags=["schedule"])


# ── Public / teacher endpoints ───────────────────────────────────────────────

@router.get("/api/schedules")
async def get_schedules(
    group_id: Optional[int] = None,
    discipline_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    active_semester = db.query(Semester).filter(Semester.is_active == True).first()
    if not active_semester:
        return []

    query = db.query(ScheduleInstance).filter(ScheduleInstance.semester_id == active_semester.id)
    query = query.join(ScheduleInstance.template)
    query = restrict_to_teacher_classes(query, current_user)

    if group_id:
        query = query.join(ScheduleTemplate.groups).filter(Group.id == group_id)

    if discipline_name:
        query = query.join(ScheduleTemplate.discipline).filter(Discipline.name == discipline_name)

    instances = query.all()
    result = []

    for instance in instances:
        template = instance.template
        teacher = instance.teacher if instance.teacher_id else template.teacher
        classroom = instance.classroom if instance.classroom else template.classroom

        can_edit = True
        if current_user.role == UserRole.TEACHER:
            can_edit = (teacher.id == current_user.id)

        is_past = instance.date < date.today()
        can_edit = can_edit and is_past and not instance.is_cancelled

        result.append({
            "id": instance.id,
            "discipline_id": template.discipline_id,
            "discipline": template.discipline.name,
            "classroom": classroom,
            "teacher": teacher.full_name,
            "teacher_id": teacher.id,
            "lesson_type": template.lesson_type.value,
            "date": str(instance.date),
            "time_start": template.time_start,
            "time_end": template.time_end,
            "is_stream": template.is_stream,
            "is_cancelled": instance.is_cancelled,
            "is_past": is_past,
            "groups": [{"id": g.id, "name": g.name} for g in template.groups],
            "can_edit": can_edit,
            "week_type": template.week_type.value
        })

    return result


@router.get("/api/my-schedule")
async def get_my_schedule(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    teacher_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Schedule available only for teachers and admins")

    if date_from is None:
        date_from = date.today()
    if date_to is None:
        date_to = date_from + timedelta(days=7)

    if date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must be earlier than date_to")

    query = db.query(ScheduleInstance).options(
        joinedload(ScheduleInstance.template).joinedload(ScheduleTemplate.discipline),
        joinedload(ScheduleInstance.template).joinedload(ScheduleTemplate.groups),
        joinedload(ScheduleInstance.teacher)
    ).join(ScheduleInstance.template).filter(
        ScheduleInstance.date >= date_from,
        ScheduleInstance.date <= date_to
    )

    if current_user.role == UserRole.ADMIN:
        if teacher_id:
            query = query.filter(
                or_(
                    ScheduleInstance.teacher_id == teacher_id,
                    and_(
                        ScheduleInstance.teacher_id.is_(None),
                        ScheduleTemplate.teacher_id == teacher_id
                    )
                )
            )
    else:
        query = restrict_to_teacher_classes(query, current_user)

    instances = query.order_by(ScheduleInstance.date, ScheduleTemplate.time_start).all()

    schedule = []
    today = date.today()
    for instance in instances:
        template = instance.template
        teacher = instance.teacher if instance.teacher_id else template.teacher
        classroom = instance.classroom if instance.classroom else template.classroom
        is_past = instance.date < today
        can_mark = (
            (current_user.role == UserRole.ADMIN or (teacher and teacher.id == current_user.id))
            and is_past
            and not instance.is_cancelled
        )
        schedule.append({
            "id": instance.id,
            "date": str(instance.date),
            "time_start": template.time_start,
            "time_end": template.time_end,
            "discipline": template.discipline.name,
            "lesson_type": template.lesson_type.value,
            "classroom": classroom,
            "groups": [{"id": g.id, "name": g.name} for g in template.groups],
            "is_cancelled": instance.is_cancelled,
            "is_past": is_past,
            "can_mark": can_mark,
            "teacher": teacher.full_name if teacher else None
        })

    return {
        "items": schedule,
        "meta": {
            "date_from": str(date_from),
            "date_to": str(date_to),
            "count": len(schedule)
        }
    }


@router.get("/api/schedules/{schedule_id}")
async def get_schedule_detail(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    instance = db.query(ScheduleInstance).options(
        joinedload(ScheduleInstance.template).joinedload(ScheduleTemplate.discipline),
        joinedload(ScheduleInstance.template).joinedload(ScheduleTemplate.groups),
        joinedload(ScheduleInstance.teacher)
    ).filter(ScheduleInstance.id == schedule_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Schedule not found")

    template = instance.template
    teacher = instance.teacher if instance.teacher_id else template.teacher
    classroom = instance.classroom if instance.classroom else template.classroom
    is_past = instance.date < date.today()
    can_mark = (
        (current_user.role == UserRole.ADMIN or (teacher and teacher.id == current_user.id))
        and is_past
        and not instance.is_cancelled
    )

    if current_user.role == UserRole.TEACHER and (not teacher or teacher.id != current_user.id):
        raise HTTPException(status_code=403, detail="You can only view your own classes")

    return {
        "id": instance.id,
        "date": str(instance.date),
        "time_start": template.time_start,
        "time_end": template.time_end,
        "discipline": template.discipline.name,
        "discipline_id": template.discipline_id,
        "lesson_type": template.lesson_type.value,
        "classroom": classroom,
        "groups": [{"id": g.id, "name": g.name} for g in template.groups],
        "teacher": teacher.full_name if teacher else None,
        "is_cancelled": instance.is_cancelled,
        "is_past": is_past,
        "can_mark": can_mark
    }


@router.get("/api/semesters")
async def get_semesters(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    semesters = db.query(Semester).all()
    return [{
        "id": s.id,
        "name": s.name,
        "start_date": str(s.start_date),
        "end_date": str(s.end_date),
        "is_active": s.is_active
    } for s in semesters]


# ── Admin CRUD ───────────────────────────────────────────────────────────────

@router.post("/api/admin/semesters")
async def create_semester(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_admin(current_user)

    data = await request.json()

    try:
        start_date = date.fromisoformat(data['start_date']) if isinstance(data['start_date'], str) else data['start_date']
        end_date = date.fromisoformat(data['end_date']) if isinstance(data['end_date'], str) else data['end_date']
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")

    if start_date >= end_date:
        raise HTTPException(status_code=400, detail="Start date must be earlier than end date")

    if data.get('is_active', False):
        db.query(Semester).update({Semester.is_active: False})

    semester = Semester(
        name=data['name'],
        start_date=start_date,
        end_date=end_date,
        is_active=data.get('is_active', False)
    )
    db.add(semester)
    db.commit()
    db.refresh(semester)

    return {"id": semester.id, "name": semester.name, "success": True}


@router.post("/api/admin/semesters/{semester_id}/activate")
async def activate_semester(
    semester_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_admin(current_user)

    semester = db.query(Semester).filter(Semester.id == semester_id).first()
    if not semester:
        raise HTTPException(status_code=404, detail="Semester not found")

    db.query(Semester).update({Semester.is_active: False})
    semester.is_active = True
    db.commit()

    return {"success": True}


@router.delete("/api/admin/semesters/{semester_id}")
async def delete_semester(
    semester_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_admin(current_user)

    semester = db.query(Semester).filter(Semester.id == semester_id).first()
    if not semester:
        raise HTTPException(status_code=404, detail="Semester not found")

    db.delete(semester)
    db.commit()

    return {"success": True}


@router.get("/api/admin/teachers")
async def get_teachers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_admin(current_user)

    teachers = db.query(User).filter(User.role == UserRole.TEACHER).all()
    return [{"id": t.id, "full_name": t.full_name} for t in teachers]


@router.get("/api/admin/schedule-templates")
async def get_schedule_templates(
    discipline_id: Optional[int] = None,
    teacher_id: Optional[int] = None,
    group_id: Optional[int] = None,
    week_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_admin(current_user)

    active_semester = db.query(Semester).filter(Semester.is_active == True).first()
    if not active_semester:
        return {"items": [], "meta": {"page": 1, "page_size": page_size, "total": 0, "pages": 1}}

    query = db.query(ScheduleTemplate).options(
        joinedload(ScheduleTemplate.groups),
        joinedload(ScheduleTemplate.discipline),
        joinedload(ScheduleTemplate.teacher)
    ).filter(ScheduleTemplate.semester_id == active_semester.id)

    if discipline_id:
        query = query.filter(ScheduleTemplate.discipline_id == discipline_id)

    if teacher_id:
        query = query.filter(ScheduleTemplate.teacher_id == teacher_id)

    if group_id:
        query = query.join(ScheduleTemplate.groups).filter(Group.id == group_id)

    if week_type:
        try:
            week_type_enum = WeekType(week_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid week type")
        else:
            if week_type_enum != WeekType.BOTH:
                query = query.filter(
                    or_(
                        ScheduleTemplate.week_type == week_type_enum,
                        ScheduleTemplate.week_type == WeekType.BOTH
                    )
                )

    query = query.order_by(ScheduleTemplate.day_of_week, ScheduleTemplate.time_start)
    templates, meta = apply_pagination(query, page, page_size)

    return {
        "items": [{
            "id": t.id,
            "discipline": t.discipline.name,
            "discipline_id": t.discipline_id,
            "teacher": t.teacher.full_name,
            "teacher_id": t.teacher_id,
            "lesson_type": t.lesson_type.value,
            "classroom": t.classroom,
            "day_of_week": t.day_of_week,
            "time_start": t.time_start,
            "time_end": t.time_end,
            "week_type": t.week_type.value,
            "groups": [{"id": g.id, "name": g.name} for g in t.groups]
        } for t in templates],
        "meta": meta
    }


@router.post("/api/admin/schedule-templates")
async def create_schedule_template(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_admin(current_user)

    data = await request.json()

    active_semester = db.query(Semester).filter(Semester.is_active == True).first()
    if not active_semester:
        raise HTTPException(status_code=400, detail="No active semester")

    template = ScheduleTemplate(
        semester_id=active_semester.id,
        discipline_id=data['discipline_id'],
        teacher_id=data['teacher_id'],
        lesson_type=LessonType(data['lesson_type']),
        classroom=data['classroom'],
        day_of_week=data['day_of_week'],
        time_start=data['time_start'],
        time_end=data['time_end'],
        week_type=WeekType(data['week_type']),
        is_stream=False
    )

    for group_id in data['group_ids']:
        group = db.query(Group).filter(Group.id == group_id).first()
        if group:
            template.groups.append(group)

    db.add(template)
    db.commit()
    db.refresh(template)

    return {"id": template.id, "success": True}


@router.delete("/api/admin/schedule-templates/{template_id}")
async def delete_schedule_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_admin(current_user)

    template = db.query(ScheduleTemplate).filter(ScheduleTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    db.delete(template)
    db.commit()

    return {"success": True}


@router.post("/api/admin/generate-instances")
async def generate_schedule_instances(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_admin(current_user)

    active_semester = db.query(Semester).filter(Semester.is_active == True).first()
    if not active_semester:
        raise HTTPException(status_code=400, detail="No active semester")

    instances_count = schedule_service.generate_instances(db, active_semester)

    return {"success": True, "count": instances_count}
