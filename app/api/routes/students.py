from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from app.db.session import get_db
from app.models import User, Student
from app.core.dependencies import get_current_user, check_admin, apply_pagination

router = APIRouter(tags=["students"])


@router.get("/api/students")
async def get_students(
    search: Optional[str] = None,
    group_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Student).options(joinedload(Student.group))

    if search:
        like_pattern = f"%{search.strip()}%"
        query = query.filter(Student.full_name.ilike(like_pattern))

    if group_id:
        query = query.filter(Student.group_id == group_id)

    query = query.order_by(Student.full_name)
    students, meta = apply_pagination(query, page, page_size)

    return {
        "items": [
            {
                "id": s.id,
                "full_name": s.full_name,
                "group_id": s.group_id,
                "group_name": s.group.name if s.group else None,
                "has_fingerprint": s.fingerprint_template is not None
            }
            for s in students
        ],
        "meta": meta
    }


# ── Admin CRUD ──────────────────────────────────────────────────────────────

@router.post("/api/admin/students")
async def create_student(
    full_name: str = Form(...),
    group_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_admin(current_user)

    student = Student(full_name=full_name, group_id=group_id)
    db.add(student)
    db.commit()
    db.refresh(student)

    return {"id": student.id, "full_name": student.full_name, "group_id": student.group_id}


@router.put("/api/admin/students/{student_id}")
async def update_student(
    student_id: int,
    full_name: Optional[str] = Form(None),
    group_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_admin(current_user)

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if full_name is not None:
        clean_name = full_name.strip()
        if not clean_name:
            raise HTTPException(status_code=400, detail="Full name cannot be empty")
        student.full_name = clean_name

    if group_id is not None:
        student.group_id = group_id

    db.commit()
    db.refresh(student)

    return {"id": student.id, "full_name": student.full_name, "group_id": student.group_id}


@router.delete("/api/admin/students/{student_id}")
async def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_admin(current_user)

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    db.delete(student)
    db.commit()

    return {"success": True}
