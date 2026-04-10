from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User, Discipline, ScheduleTemplate
from app.core.dependencies import get_current_user, check_admin

router = APIRouter(tags=["disciplines"])


@router.get("/api/disciplines")
async def get_disciplines(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    disciplines = db.query(Discipline).all()
    return [{"id": d.id, "name": d.name} for d in disciplines]


# ── Admin CRUD ──────────────────────────────────────────────────────────────

@router.post("/api/admin/disciplines")
async def create_discipline(
    name: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_admin(current_user)

    clean_name = name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Discipline name cannot be empty")

    existing = db.query(Discipline).filter(func.lower(Discipline.name) == clean_name.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Discipline with this name already exists")

    discipline = Discipline(name=clean_name)
    db.add(discipline)
    db.commit()
    db.refresh(discipline)

    return {"id": discipline.id, "name": discipline.name}


@router.put("/api/admin/disciplines/{discipline_id}")
async def update_discipline(
    discipline_id: int,
    name: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_admin(current_user)

    discipline = db.query(Discipline).filter(Discipline.id == discipline_id).first()
    if not discipline:
        raise HTTPException(status_code=404, detail="Discipline not found")

    clean_name = name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Discipline name cannot be empty")

    existing = (
        db.query(Discipline)
        .filter(
            func.lower(Discipline.name) == clean_name.lower(),
            Discipline.id != discipline_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409, detail="Discipline with this name already exists"
        )

    discipline.name = clean_name
    db.commit()
    db.refresh(discipline)

    return {"id": discipline.id, "name": discipline.name}


@router.delete("/api/admin/disciplines/{discipline_id}")
async def delete_discipline(
    discipline_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_admin(current_user)

    discipline = db.query(Discipline).filter(Discipline.id == discipline_id).first()
    if not discipline:
        raise HTTPException(status_code=404, detail="Discipline not found")

    is_used_in_templates = db.query(ScheduleTemplate).filter(
        ScheduleTemplate.discipline_id == discipline_id
    ).first()
    if is_used_in_templates:
        raise HTTPException(status_code=400, detail="Discipline is used in schedule templates")

    db.delete(discipline)
    db.commit()

    return {"success": True}
