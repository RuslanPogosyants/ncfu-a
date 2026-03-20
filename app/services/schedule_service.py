"""
Сервис генерации экземпляров расписания.
Содержит нетривиальную логику обхода дат семестра и создания ScheduleInstance.
"""
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.models import Semester, ScheduleTemplate, ScheduleInstance, WeekType


def _get_week_number(d: date, start: date) -> int:
    return (d - start).days // 7


def _is_week_type_match(week_num: int, week_type: WeekType) -> bool:
    if week_type == WeekType.BOTH:
        return True
    elif week_type == WeekType.EVEN:
        return week_num % 2 == 0
    else:
        return week_num % 2 == 1


def generate_instances(db: Session, active_semester: Semester) -> int:
    """
    Удаляет будущие экземпляры активного семестра и генерирует новые
    по шаблонам расписания. Возвращает количество созданных экземпляров.
    """
    db.query(ScheduleInstance).filter(
        ScheduleInstance.semester_id == active_semester.id,
        ScheduleInstance.date >= date.today()
    ).delete()

    templates = db.query(ScheduleTemplate).filter(
        ScheduleTemplate.semester_id == active_semester.id
    ).all()

    instances_count = 0
    current_date = date.today()

    while current_date <= active_semester.end_date:
        week_num = _get_week_number(current_date, active_semester.start_date)
        day_of_week = current_date.weekday()

        for template in templates:
            if template.day_of_week == day_of_week and _is_week_type_match(week_num, template.week_type):
                existing = db.query(ScheduleInstance).filter(
                    ScheduleInstance.template_id == template.id,
                    ScheduleInstance.date == current_date
                ).first()

                if not existing:
                    instance = ScheduleInstance(
                        template_id=template.id,
                        semester_id=active_semester.id,
                        date=current_date,
                        is_cancelled=False
                    )
                    db.add(instance)
                    instances_count += 1

        current_date += timedelta(days=1)

    db.commit()
    return instances_count
