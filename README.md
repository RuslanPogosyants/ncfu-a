# Система учёта посещаемости студентов

Веб-приложение для автоматизированного учёта посещаемости на базе FastAPI.
Поддерживает ручной учёт, биометрическую идентификацию (лицо, отпечаток пальца),
управление расписанием и формирование отчётов.

---

## Что умеет приложение

- Авторизация через JWT с ролевой моделью (администратор / преподаватель).
- Управление группами, студентами, дисциплинами и семестрами.
- Гибкое расписание: шаблоны + автогенерация занятий.
- Учёт посещаемости на каждом занятии (присутствует / отсутствует / опоздал / уважительная причина).
- Выставление оценок одновременно с отметкой посещаемости.
- Биометрическая идентификация — распознавание лиц (dlib) и считыватель отпечатков ESP32/AS608.
- Отчёты: журнал посещаемости (CSV / XLSX / JSON) и сводная статистика.
- Дашборд с агрегированными показателями.

---

## Технологии

| Слой | Стек |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn (ASGI) |
| ORM | SQLAlchemy 2.0 |
| База данных | PostgreSQL 16 |
| Миграции | Alembic |
| Аутентификация | JWT (python-jose) + bcrypt |
| Шаблоны | Jinja2 |
| Frontend | Vanilla JS |
| Reverse Proxy | Nginx |
| Контейнеризация | Docker + Docker Compose |
| Тесты | pytest + pytest-asyncio + httpx |
| Линтинг | Ruff |
| Биометрия | face-recognition (dlib), OpenCV, Pillow |

---

## Архитектура сервисов

В Docker-режиме поднимаются 3 сервиса:

| Сервис | Описание |
|---|---|
| `db` | PostgreSQL 16 — данные в volume `postgres_data` |
| `web` | FastAPI-приложение (Uvicorn, порт 8888 внутри сети) |
| `nginx` | Reverse proxy — `http://localhost:8090` → web |

```
Браузер / API-клиент
        │
     Nginx :8090
        │
    FastAPI :8888
        │
  PostgreSQL :5432
```

---

## Быстрый старт (Docker — рекомендуется)

### 1. Клонировать репозиторий

```bash
git clone <repo-url>
cd ncfu-a
```

### 2. Создать `.env`

```bash
cp .env.example .env
# Обязательно задать SECRET_KEY
```

Минимальный `.env`:
```env
SECRET_KEY=your-secret-key-min-32-chars
DATABASE_URL=postgresql://ncfu:ncfu_password@db:5432/ncfu_attendance
```

### 3. Запустить

```bash
docker compose up --build -d
```

Приложение доступно на `http://localhost:8090`.
Swagger UI: `http://localhost:8090/docs`.

### 4. Инициализировать базу данных

```bash
docker compose exec web python init_db.py
```

Создаст таблицы и тестовые учётные записи.

### 5. Войти в систему

| Роль | Логин | Пароль |
|---|---|---|
| Администратор | `admin` | `admin123` |
| Преподаватель | `ivanov` | `teacher123` |
| Преподаватель | `petrova` | `teacher123` |

---

## Локальный запуск без Docker

### Требования

- Python 3.11+
- PostgreSQL 16+ (или SQLite — задать `DATABASE_URL=sqlite:///./university.db`)

### Установка

```bash
# Создать виртуальное окружение
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows

# Установить зависимости
pip install -r requirements.txt

# Задать переменные окружения
export SECRET_KEY=dev-secret-key
export DATABASE_URL=sqlite:///./university.db

# Инициализировать БД и заполнить тестовыми данными
python init_db.py

# Запустить сервер
uvicorn main:app --host 0.0.0.0 --port 8888 --reload
```

Приложение доступно на `http://localhost:8888`.
Swagger UI: `http://localhost:8888/docs`.

---

## Переменные окружения

| Переменная | Обязательна | По умолчанию | Описание |
|---|---|---|---|
| `SECRET_KEY` | **да** | — | Секрет подписи JWT (мин. 32 символа) |
| `DATABASE_URL` | нет | `postgresql://ncfu:ncfu_password@db:5432/ncfu_attendance` | URL базы данных |
| `ALGORITHM` | нет | `HS256` | Алгоритм JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | нет | `30` | Время жизни токена (мин) |
| `FACE_RECOGNITION_TOLERANCE` | нет | `0.6` | Порог распознавания лиц (0–1) |

> Перед деплоем в продакшен обязательно смените `SECRET_KEY` и пароли базы данных.

---

## Миграции базы данных

Миграции управляются через Alembic.

```bash
# Создать новую миграцию
alembic revision --autogenerate -m "описание"

# Применить все миграции
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1
```

---

## API

### Базовый URL

- Локально без Nginx: `http://localhost:8888`
- Docker с Nginx: `http://localhost:8090`

### Авторизация

Все защищённые эндпоинты требуют заголовок:
```
Authorization: Bearer <jwt>
```

Токен получается через `POST /token`.

### Эндпоинты

#### Авторизация

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| `POST` | `/token` | публичный | Вход — возвращает JWT |
| `GET` | `/api/me` | любой | Данные текущего пользователя |

#### Группы и студенты

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| `GET` | `/api/groups` | любой | Список групп |
| `GET` | `/api/groups/{id}/students` | любой | Студенты группы |
| `GET` | `/api/students` | любой | Студенты (поиск, пагинация) |
| `POST` | `/api/admin/students` | admin | Создать студента |
| `DELETE` | `/api/admin/students/{id}` | admin | Удалить студента |
| `POST` | `/api/admin/groups` | admin | Создать группу |
| `DELETE` | `/api/admin/groups/{id}` | admin | Удалить группу |

#### Дисциплины и семестры

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| `GET` | `/api/disciplines` | любой | Список дисциплин |
| `POST` | `/api/admin/disciplines` | admin | Создать дисциплину |
| `DELETE` | `/api/admin/disciplines/{id}` | admin | Удалить дисциплину |
| `GET` | `/api/semesters` | любой | Список семестров |
| `POST` | `/api/admin/semesters` | admin | Создать семестр |
| `POST` | `/api/admin/semesters/{id}/activate` | admin | Активировать семестр |
| `DELETE` | `/api/admin/semesters/{id}` | admin | Удалить семестр |

#### Расписание

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| `GET` | `/api/schedules` | любой | Расписание с фильтрами |
| `GET` | `/api/my-schedule` | teacher/admin | Расписание преподавателя |
| `GET` | `/api/schedules/{id}` | любой | Детали занятия |
| `GET` | `/api/admin/schedule-templates` | admin | Шаблоны расписания |
| `POST` | `/api/admin/schedule-templates` | admin | Создать шаблон |
| `DELETE` | `/api/admin/schedule-templates/{id}` | admin | Удалить шаблон |
| `POST` | `/api/admin/generate-instances` | admin | Сгенерировать занятия из шаблонов |

#### Посещаемость

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| `GET` | `/api/schedules/{id}/records` | любой | Записи посещаемости занятия |
| `POST` | `/api/records` | teacher/admin | Сохранить / обновить запись |

#### Отчёты

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| `GET` | `/api/reports/journal` | teacher/admin | Журнал (CSV / XLSX / JSON) |
| `GET` | `/api/reports/summary` | teacher/admin | Сводная статистика |
| `GET` | `/api/dashboard/stats` | любой | Метрики дашборда |

#### Биометрия

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| `POST` | `/api/students/{id}/upload-face` | admin | Загрузить фото студента |
| `GET` | `/api/students/{id}/has-face` | любой | Проверить наличие фото |
| `GET` | `/api/groups/{id}/face-stats` | любой | Статистика регистрации лиц по группе |
| `POST` | `/api/schedules/{id}/recognize-attendance` | teacher/admin | Авто-отметка через распознавание лиц |
| `POST` | `/api/fingerprint/*` | teacher/admin | Интеграция со считывателем ESP32/AS608 |

Полная интерактивная документация: `http://localhost:8090/docs`

---

## Биометрия

### Распознавание лиц

Используется библиотека `face-recognition` (dlib). Требует файлы моделей в корне проекта
(`dlib_face_recognition_resnet_model_v1.dat`, `shape_predictor_68_face_landmarks.dat`).
При отсутствии моделей сервис автоматически переключается в **simple mode** (graceful degradation).

### Отпечаток пальца (ESP32 / AS608)

Внешний микроконтроллер ESP32 с датчиком AS608 предоставляет REST API.
`fingerprint_api.py` проксирует все вызовы к считывателю.
Схему подключения и прошивку см. в аппаратной документации.

---

## Тесты

49 тестов: авторизация, CRUD групп/студентов/дисциплин, расписание, посещаемость, отчёты.

```bash
# Docker
docker compose run --rm -e SECRET_KEY=test -e DATABASE_URL=sqlite:///:memory: web pytest tests/ -v

# Локально (SQLite in-memory)
SECRET_KEY=test DATABASE_URL=sqlite:///:memory: pytest tests/ -v
```

---

## Линтинг

```bash
# Проверка
ruff check .

# Автоисправление
ruff check . --fix

# Форматирование
ruff format .
```

---

## CI/CD

GitHub Actions workflow (`.github/workflows/tests.yml`) запускается при каждом push и PR в `main`/`master`:

1. Сборка Docker-образа.
2. Запуск полного набора тестов внутри контейнера против SQLite in-memory.

---

## Структура проекта

```
ncfu-a/
├── app/
│   ├── api/
│   │   ├── routes/              # Маршруты по доменам
│   │   │   ├── auth.py
│   │   │   ├── pages.py
│   │   │   ├── groups.py
│   │   │   ├── students.py
│   │   │   ├── disciplines.py
│   │   │   ├── schedule.py
│   │   │   ├── attendance.py
│   │   │   ├── reports.py
│   │   │   └── biometric.py
│   │   └── router.py
│   ├── core/
│   │   ├── config.py            # Настройки через pydantic-settings
│   │   ├── security.py          # JWT, bcrypt
│   │   └── dependencies.py      # Общие зависимости FastAPI
│   ├── db/
│   │   ├── base.py              # DeclarativeBase
│   │   └── session.py           # Engine + SessionLocal
│   ├── models.py                # SQLAlchemy-модели
│   ├── schemas.py               # Pydantic-схемы
│   ├── services/                # Бизнес-логика
│   │   ├── attendance_service.py
│   │   ├── report_service.py
│   │   ├── schedule_service.py
│   │   └── biometric_service.py
│   └── main.py                  # Фабрика FastAPI-приложения
├── templates/                   # Jinja2 HTML-шаблоны
├── static/                      # JS, CSS
├── tests/                       # pytest
├── alembic/                     # Миграции БД
├── nginx/
│   └── nginx.conf
├── .github/
│   └── workflows/
│       └── tests.yml            # CI/CD
├── main.py                      # Точка входа (совместимость)
├── face_recognition_service.py  # Обёртка над dlib
├── fingerprint_api.py           # Роутер ESP32/AS608
├── init_db.py                   # Скрипт инициализации данных
├── docker-compose.yml
├── Dockerfile
├── alembic.ini
├── requirements.txt
├── ruff.toml
└── pytest.ini
```
