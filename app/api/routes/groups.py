from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User, Group, Student, ScheduleTemplate
from app.core.dependencies import get_current_user, check_admin

router = APIRouter(tags=["groups"])


@router.get("/api/groups")
async def get_groups(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    groups = db.query(Group).all()
    return [{"id": g.id, "name": g.name} for g in groups]


@router.get("/api/groups/{group_id}/students")
async def get_group_students(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    students = db.query(Student).filter(Student.group_id == group_id).all()
    return [
        {
            "id": s.id,
            "full_name": s.full_name,
            "group_id": s.group_id,
            "group_name": s.group.name,
            "has_fingerprint": s.fingerprint_template is not None
        }
        for s in students
    ]


# ── Admin CRUD ──────────────────────────────────────────────────────────────

@router.post("/api/admin/groups")
async def create_group(
    name: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_admin(current_user)

    clean_name = name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Group name cannot be empty")

    existing = db.query(Group).filter(func.lower(Group.name) == clean_name.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Group with this name already exists")

    group = Group(name=clean_name)
    db.add(group)
    db.commit()
    db.refresh(group)

    return {"id": group.id, "name": group.name}


@router.put("/api/admin/groups/{group_id}")
async def update_group(
    group_id: int,
    name: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_admin(current_user)

    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    clean_name = name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Group name cannot be empty")

    existing = (
        db.query(Group)
        .filter(func.lower(Group.name) == clean_name.lower(), Group.id != group_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Group with this name already exists")

    group.name = clean_name
    db.commit()
    db.refresh(group)

    return {"id": group.id, "name": group.name}


@router.delete("/api/admin/groups/{group_id}")
async def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_admin(current_user)

    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    has_students = db.query(Student.id).filter(Student.group_id == group_id).first()
    if has_students:
        raise HTTPException(status_code=400, detail="Cannot delete group with assigned students")

    is_used_in_templates = (
        db.query(ScheduleTemplate).join(ScheduleTemplate.groups).filter(Group.id == group_id).first()
    )
    if is_used_in_templates:
        raise HTTPException(status_code=400, detail="Group is used in schedule templates")

    db.delete(group)
    db.commit()

    return {"success": True}
