# Student Attendance System

Web application for automated student attendance tracking built with FastAPI.
Supports manual entry, biometric identification (face, fingerprint),
schedule management, and report generation.

---

## Features

- JWT-based authentication with role model (admin / teacher).
- Groups, students, disciplines and semester management.
- Flexible schedule: templates + auto-generated instances.
- Attendance recording per class (present / absent / late / excused).
- Grade entry alongside attendance status.
- Biometric identification — face recognition via dlib + ESP32/AS608 fingerprint reader.
- Reports: attendance journal (CSV / XLSX / JSON) and summary statistics.
- Dashboard with aggregated metrics.
- Public share-access for pages.
- Docker-first setup with Nginx reverse proxy.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn (ASGI) |
| ORM | SQLAlchemy 2.0 (sync) |
| Database | PostgreSQL 16 |
| Migrations | Alembic |
| Authentication | JWT (python-jose) + bcrypt |
| Templates | Jinja2 |
| Frontend | Vanilla JS |
| Reverse Proxy | Nginx |
| Containerisation | Docker + Docker Compose |
| Tests | pytest + pytest-asyncio + httpx |
| Linting | Ruff |
| Biometrics | face-recognition (dlib), OpenCV, Pillow |

---

## Architecture

Docker Compose brings up three services:

| Service | Description |
|---|---|
| `db` | PostgreSQL 16 — persistent volume `postgres_data` |
| `web` | FastAPI application (Uvicorn, port 8888 internally) |
| `nginx` | Reverse proxy — `http://localhost:8090` → web |

```
Browser / API client
       │
    Nginx :8090
       │
    FastAPI :8888
       │
  PostgreSQL :5432
```

---

## Quick Start (Docker — recommended)

### 1. Clone the repository

```bash
git clone <repo-url>
cd ncfu-a
```

### 2. Create `.env`

```bash
cp .env.example .env
# Set at least SECRET_KEY
```

Minimal `.env`:
```env
SECRET_KEY=your-secret-key-min-32-chars
DATABASE_URL=postgresql://ncfu:ncfu_password@db:5432/ncfu_attendance
```

### 3. Start

```bash
docker compose up --build -d
```

App is available at `http://localhost:8090`.  
Swagger UI: `http://localhost:8090/docs`.

### 4. Initialise database

```bash
docker compose exec web python init_db.py
```

Creates tables and seeds test accounts.

### 5. Log in

| Role | Login | Password |
|---|---|---|
| Administrator | `admin` | `admin123` |
| Teacher | `ivanov` | `teacher123` |
| Teacher | `petrova` | `teacher123` |

---

## Local Run (without Docker)

### Requirements

- Python 3.11+
- PostgreSQL 16+ (or use `DATABASE_URL=sqlite:///./university.db` for SQLite)

### Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SECRET_KEY=dev-secret-key
export DATABASE_URL=sqlite:///./university.db

# Initialise DB and seed data
python init_db.py

# Start server
uvicorn main:app --host 0.0.0.0 --port 8888 --reload
```

App available at `http://localhost:8888`.  
Swagger UI: `http://localhost:8888/docs`.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | **yes** | — | JWT signing secret (min 32 chars) |
| `DATABASE_URL` | no | `postgresql://ncfu:ncfu_password@db:5432/ncfu_attendance` | Database connection URL |
| `ALGORITHM` | no | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | `30` | Token lifetime (minutes) |
| `FACE_RECOGNITION_TOLERANCE` | no | `0.6` | Face recognition threshold (0–1) |

> Before deploying to production, change `SECRET_KEY` and all database credentials.

---

## Database Migrations

Migrations are managed with Alembic.

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply all pending migrations
alembic upgrade head

# Roll back one step
alembic downgrade -1
```

---

## API

### Base URL

- Local (no Nginx): `http://localhost:8888`
- Docker (with Nginx): `http://localhost:8090`

### Authentication

All protected endpoints require:
```
Authorization: Bearer <jwt>
```

Obtain a token via `POST /token`.

### Endpoints

#### Auth

| Method | Path | Access | Description |
|---|---|---|---|
| `POST` | `/token` | public | Login — returns JWT |
| `GET` | `/api/me` | any | Current user info |

#### Groups & Students

| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/api/groups` | any | List groups |
| `GET` | `/api/groups/{id}/students` | any | Students in group |
| `GET` | `/api/students` | any | Students (search, pagination) |
| `POST` | `/api/admin/students` | admin | Create student |
| `DELETE` | `/api/admin/students/{id}` | admin | Delete student |
| `POST` | `/api/admin/groups` | admin | Create group |
| `DELETE` | `/api/admin/groups/{id}` | admin | Delete group |

#### Disciplines & Semesters

| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/api/disciplines` | any | List disciplines |
| `POST` | `/api/admin/disciplines` | admin | Create discipline |
| `DELETE` | `/api/admin/disciplines/{id}` | admin | Delete discipline |
| `GET` | `/api/semesters` | any | List semesters |
| `POST` | `/api/admin/semesters` | admin | Create semester |
| `POST` | `/api/admin/semesters/{id}/activate` | admin | Activate semester |
| `DELETE` | `/api/admin/semesters/{id}` | admin | Delete semester |

#### Schedule

| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/api/schedules` | any | Schedule with filters |
| `GET` | `/api/my-schedule` | teacher/admin | Teacher's schedule |
| `GET` | `/api/schedules/{id}` | any | Class details |
| `GET` | `/api/admin/schedule-templates` | admin | Schedule templates |
| `POST` | `/api/admin/schedule-templates` | admin | Create template |
| `DELETE` | `/api/admin/schedule-templates/{id}` | admin | Delete template |
| `POST` | `/api/admin/generate-instances` | admin | Generate classes from templates |

#### Attendance

| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/api/schedules/{id}/records` | any | Attendance records for class |
| `POST` | `/api/records` | teacher/admin | Save / update attendance record |

#### Reports

| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/api/reports/journal` | teacher/admin | Journal export (CSV / XLSX / JSON) |
| `GET` | `/api/reports/summary` | teacher/admin | Aggregated statistics |
| `GET` | `/api/dashboard/stats` | any | Dashboard metrics |

#### Biometrics

| Method | Path | Access | Description |
|---|---|---|---|
| `POST` | `/api/students/{id}/upload-face` | admin | Upload face photo |
| `GET` | `/api/students/{id}/has-face` | any | Check face enrolled |
| `GET` | `/api/groups/{id}/face-stats` | any | Face enrollment stats for group |
| `POST` | `/api/schedules/{id}/recognize-attendance` | teacher/admin | Auto-mark attendance via face recognition |
| `POST` | `/api/fingerprint/*` | teacher/admin | Fingerprint reader integration (ESP32/AS608) |

Full interactive docs: `http://localhost:8090/docs`

---

## Biometrics

### Face Recognition

Uses the `face-recognition` library (dlib). Requires `.dat` model files in the project root
(`dlib_face_recognition_resnet_model_v1.dat`, `shape_predictor_68_face_landmarks.dat`).  
When dlib models are absent the service falls back to **simple mode** (graceful degradation).

### Fingerprint (ESP32 / AS608)

An external ESP32 microcontroller with an AS608 fingerprint sensor exposes a small REST API.
Configure the sensor IP in the environment; `fingerprint_api.py` proxies all reader calls.
See hardware documentation for wiring and firmware.

---

## Tests

49 tests covering auth, CRUD for all entities, schedule generation, attendance and reports.

```bash
# Docker
docker compose run --rm -e SECRET_KEY=test -e DATABASE_URL=sqlite:///:memory: web pytest tests/ -v

# Local (SQLite in-memory)
SECRET_KEY=test DATABASE_URL=sqlite:///:memory: pytest tests/ -v
```

---

## Linting

```bash
# Check
ruff check .

# Auto-fix
ruff check . --fix

# Format
ruff format .
```

---

## CI/CD

GitHub Actions workflow (`.github/workflows/tests.yml`) runs on every push and PR to `main`/`master`:

1. Builds the Docker image.
2. Runs the full test suite inside the container against SQLite in-memory.

---

## Project Structure

```
ncfu-a/
├── app/
│   ├── api/
│   │   ├── routes/              # Route handlers per domain
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
│   │   ├── config.py            # Settings via pydantic-settings
│   │   ├── security.py          # JWT, bcrypt
│   │   └── dependencies.py      # Shared FastAPI dependencies
│   ├── db/
│   │   ├── base.py              # DeclarativeBase
│   │   └── session.py           # Engine + SessionLocal
│   ├── models.py                # SQLAlchemy models
│   ├── schemas.py               # Pydantic schemas
│   ├── services/                # Business logic
│   │   ├── attendance_service.py
│   │   ├── report_service.py
│   │   ├── schedule_service.py
│   │   └── biometric_service.py
│   └── main.py                  # FastAPI application factory
├── templates/                   # Jinja2 HTML templates
├── static/                      # JS, CSS
├── tests/                       # pytest suite
├── alembic/                     # Database migrations
├── nginx/
│   └── nginx.conf
├── .github/
│   └── workflows/
│       └── tests.yml            # CI/CD
├── main.py                      # Compatibility entrypoint
├── face_recognition_service.py  # dlib face recognition wrapper
├── fingerprint_api.py           # ESP32/AS608 router
├── init_db.py                   # Database seed script
├── docker-compose.yml
├── Dockerfile
├── alembic.ini
├── requirements.txt
├── ruff.toml
└── pytest.ini
```
