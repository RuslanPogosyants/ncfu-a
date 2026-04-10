"""
Централизованная сборка всех route-модулей приложения.
Никакой доменной логики и SQLAlchemy-запросов здесь нет.
"""
from fastapi import APIRouter

from app.api.routes import (
    auth,
    pages,
    groups,
    students,
    disciplines,
    schedule,
    attendance,
    reports,
    biometric,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(pages.router)
api_router.include_router(groups.router)
api_router.include_router(students.router)
api_router.include_router(disciplines.router)
api_router.include_router(schedule.router)
api_router.include_router(attendance.router)
api_router.include_router(reports.router)
api_router.include_router(biometric.router)
