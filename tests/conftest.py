"""
Shared fixtures for all test modules.

Environment variables are set BEFORE any app imports so that pydantic-settings
picks up the test database URL and secret key at Settings() construction time.
"""
import os

# Force test environment BEFORE importing anything from app.*
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")

from datetime import date, timedelta

import pytest
from httpx import AsyncClient, ASGITransport

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.main import app
from app.models import (
    Discipline,
    Group,
    LessonType,
    ScheduleInstance,
    ScheduleTemplate,
    Semester,
    Student,
    User,
    UserRole,
    WeekType,
)
from app.core.security import create_access_token, get_password_hash


# ── Table lifecycle ──────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_tables():
    """Drop and recreate all tables before every test for full isolation."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


# ── DB session ───────────────────────────────────────────────────────────────

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ── HTTP client ──────────────────────────────────────────────────────────────

@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ── Users ────────────────────────────────────────────────────────────────────

@pytest.fixture
def admin(db):
    user = User(
        username="admin",
        hashed_password=get_password_hash("adminpass"),
        full_name="Admin User",
        role=UserRole.ADMIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def teacher(db):
    user = User(
        username="teacher",
        hashed_password=get_password_hash("teacherpass"),
        full_name="Teacher User",
        role=UserRole.TEACHER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_token(admin):
    return create_access_token(data={"sub": admin.username})


@pytest.fixture
def teacher_token(teacher):
    return create_access_token(data={"sub": teacher.username})


# ── Domain data ───────────────────────────────────────────────────────────────

@pytest.fixture
def group(db):
    g = Group(name="CS-101")
    db.add(g)
    db.commit()
    db.refresh(g)
    return g


@pytest.fixture
def student(db, group):
    s = Student(full_name="Иванов Иван Иванович", group_id=group.id)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@pytest.fixture
def discipline(db):
    d = Discipline(name="Math")
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


@pytest.fixture
def semester(db):
    s = Semester(
        name="Весна 2026",
        start_date=date(2026, 2, 1),
        end_date=date(2026, 6, 30),
        is_active=True,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@pytest.fixture
def schedule_template(db, semester, discipline, teacher, group):
    t = ScheduleTemplate(
        semester_id=semester.id,
        discipline_id=discipline.id,
        teacher_id=teacher.id,
        lesson_type=LessonType.LECTURE,
        classroom="101",
        day_of_week=0,
        time_start="09:00",
        time_end="10:30",
        week_type=WeekType.BOTH,
        is_stream=False,
    )
    t.groups.append(group)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@pytest.fixture
def past_instance(db, schedule_template, semester):
    inst = ScheduleInstance(
        template_id=schedule_template.id,
        semester_id=semester.id,
        date=date.today() - timedelta(days=7),
        is_cancelled=False,
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst
