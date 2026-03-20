"""
Сервис построения отчётов.
Содержит логику агрегации данных для журнала и сводного отчёта.
"""
from typing import List, Optional

from app.models import StudentStatus
from app.core.dependencies import STATUS_LABELS, PRESENT_STATUSES


def build_report_rows(instances, students, records_map) -> List[dict]:
    """Формирует плоский список строк для CSV/XLSX/JSON-экспорта."""
    rows = []
    for instance in instances:
        template = instance.template
        discipline_name = template.discipline.name
        for student in students:
            record = records_map.get((instance.id, student.id))
            status = record.status if record else None
            status_label = STATUS_LABELS.get(status, "Не отмечено")
            grade = record.grade if record else None

            rows.append({
                "date": str(instance.date),
                "lesson_type": template.lesson_type.value,
                "discipline": discipline_name,
                "student": student.full_name,
                "status": status_label,
                "status_code": status.value if status else None,
                "grade": grade
            })
    return rows


def build_summary_stats(instances, students, records) -> dict:
    """
    Агрегирует статистику посещаемости и оценок по группе за период.
    Возвращает dict с attendance и grades блоками.
    """
    instance_ids = [inst.id for inst in instances]
    total_possible_records = len(instance_ids) * len(students)

    attendance_stats = {
        StudentStatus.PRESENT.value: 0,
        StudentStatus.ABSENT.value: 0,
        StudentStatus.EXCUSED.value: 0,
        StudentStatus.AUTO_DETECTED.value: 0,
        StudentStatus.FINGERPRINT_DETECTED.value: 0,
        "missing": 0
    }

    grade_map = {student.id: [] for student in students}

    for record in records:
        attendance_stats[record.status.value] += 1
        if record.grade is not None:
            grade_map[record.student_id].append(record.grade)

    attendance_stats["missing"] = max(0, total_possible_records - len(records))

    present_total = (
        attendance_stats[StudentStatus.PRESENT.value] +
        attendance_stats[StudentStatus.AUTO_DETECTED.value] +
        attendance_stats[StudentStatus.FINGERPRINT_DETECTED.value]
    )
    attendance_rate = present_total / total_possible_records if total_possible_records else 0

    student_averages = []
    overall_grades = []
    for student in students:
        grades = grade_map[student.id]
        if grades:
            avg = sum(grades) / len(grades)
            student_averages.append({
                "student_id": student.id,
                "student_name": student.full_name,
                "average_grade": round(avg, 2),
                "grades_count": len(grades)
            })
            overall_grades.extend(grades)
        else:
            student_averages.append({
                "student_id": student.id,
                "student_name": student.full_name,
                "average_grade": None,
                "grades_count": 0
            })

    overall_average = round(sum(overall_grades) / len(overall_grades), 2) if overall_grades else None

    return {
        "attendance": {
            "total_possible": total_possible_records,
            "by_status": attendance_stats,
            "attendance_rate": round(attendance_rate, 3)
        },
        "grades": {
            "overall_average": overall_average,
            "student_averages": student_averages
        }
    }
