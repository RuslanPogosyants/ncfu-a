"""
Точка сборки FastAPI-приложения.
Только создание app, подключение роутеров и монтирование статики.
Никакой доменной логики здесь нет.
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
import fingerprint_api  # уже готовый отдельный роутер

app = FastAPI(title="University Journal System")

# Fingerprint router (собственный модуль, не трогаем)
app.include_router(fingerprint_api.router)

# Все остальные маршруты через центральный роутер
app.include_router(api_router)

# Статика — путь относительно рабочей директории запуска (как в оригинале)
app.mount("/static", StaticFiles(directory="static"), name="static")
