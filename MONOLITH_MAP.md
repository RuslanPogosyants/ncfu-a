# MONOLITH_MAP.md — Карта монолита main.py

Файл: `main.py` (~1406 строк)

---

## Блоки монолита

### 1. App Bootstrap (строки 1–44)
- Импорты FastAPI, SQLAlchemy, auth, models, face_recognition_service
- Создание `app = FastAPI(...)`
- `app.include_router(fingerprint_api.router)`
- Mount `/static`
- Инициализация `Jinja2Templates`
- Lazy-singleton `face_service` + `get_face_service()`
- Константы: `MAX_PAGE_SIZE`, `MIN_GRADE`, `MAX_GRADE_ALLOWED`
- `Base.metadata.create_all(bind=engine)` — создание таблиц при старте

### 2. Вспомогательные функции (строки 46–101)
- `normalize_pagination(page, page_size)` — нормализация параметров пагинации
- `apply_pagination(query, page, page_size)` — выполнение пагинированного запроса
- `restrict_to_teacher_classes(query, current_user)` — фильтрация запросов для teacher-роли
- `STATUS_LABELS` — dict: StudentStatus → строка на русском
- `PRESENT_STATUSES` — множество "присутственных" статусов
- `validate_grade_value(grade)` — валидация оценки (целое 2–5)

### 3. Страничные маршруты (строки 103–161)
URL | Handler
`GET /` | `welcome_page` → `welcome.html`
`GET /schedule` | `schedule_page` → `schedule.html`
`GET /login` | `login_page` → `login.html`
`GET /admin` | `admin_page` → `admin.html`
`GET /journal` | `journal_page` → `journal.html`
`GET /dashboard` | `dashboard_page` → `dashboard.html`
`GET /attendance` | `attendance_page` → `attendance.html`

### 4. Auth / Token (строки 118–141)
URL | Handler
`POST /token` | `login` — OAuth2 login, возвращает JWT
`GET /api/me` | `read_users_me` — текущий пользователь

### 5. Группы (строки 165–175)
URL | Handler
`GET /api/groups` | `get_groups`
`GET /api/groups/{group_id}/students` | `get_group_students`

### 6. Расписание — чтение (строки 178–395)
URL | Handler
`GET /api/schedules` | `get_schedules` — список с фильтрами (group_id, discipline_name)
`GET /api/my-schedule` | `get_my_schedule` — расписание учителя за диапазон дат
`GET /api/schedules/{schedule_id}` | `get_schedule_detail` — детали занятия
`GET /api/schedules/{schedule_id}/records` | `get_schedule_records` — список студентов с посещаемостью

### 7. Посещаемость — запись (строки 398–452)
URL | Handler
`POST /api/records` | `create_or_update_record` — создание/обновление записи (Form data)

### 8. Справочники (строки 455–506)
URL | Handler
`GET /api/disciplines` | `get_disciplines`
`GET /api/students` | `get_students` — с поиском и пагинацией
`GET /api/semesters` | `get_semesters`

### 9. Admin CRUD (строки 510–918)
Функция-guard: `check_admin(current_user)` (стр. 510)

URL | Handler
`POST /api/admin/students` | `create_student`
`DELETE /api/admin/students/{student_id}` | `delete_student`
`POST /api/admin/groups` | `create_group`
`DELETE /api/admin/groups/{group_id}` | `delete_group`
`POST /api/admin/disciplines` | `create_discipline`
`DELETE /api/admin/disciplines/{discipline_id}` | `delete_discipline`
`POST /api/admin/semesters` | `create_semester`
`POST /api/admin/semesters/{semester_id}/activate` | `activate_semester`
`DELETE /api/admin/semesters/{semester_id}` | `delete_semester`
`GET /api/admin/teachers` | `get_teachers`
`GET /api/admin/schedule-templates` | `get_schedule_templates`
`POST /api/admin/schedule-templates` | `create_schedule_template`
`DELETE /api/admin/schedule-templates/{template_id}` | `delete_schedule_template`
`POST /api/admin/generate-instances` | `generate_schedule_instances` ← **нетривиальная логика**

### 10. Отчёты (строки 923–1173)
Функция-guard: `ensure_report_access(current_user)` (стр. 923)
Функция-helper: `build_report_rows(instances, students, records_map)` (стр. 928)

URL | Handler
`GET /api/reports/journal` | `get_journal_report` — выгрузка CSV/XLSX/JSON
`GET /api/reports/summary` | `get_summary_report` — агрегированная статистика

### 11. Биометрия — лицо (строки 1177–1300)
URL | Handler
`POST /api/students/{student_id}/upload-face` | `upload_student_face`
`POST /api/schedules/{schedule_id}/recognize-attendance` | `recognize_attendance` ← **нетривиальная оркестрация**
`GET /api/students/{student_id}/has-face` | `check_student_face`
`GET /api/groups/{group_id}/face-stats` | `get_group_face_stats`

### 12. Дашборд (строки 1304–1399)
URL | Handler
`GET /api/dashboard/stats` | `get_dashboard_stats` ← **нетривиальная агрегация**

### 13. Запуск сервера (строки 1402–1404)
```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)
```

---

## Уже вынесенные файлы (до рефакторинга)

Файл | Назначение
`auth.py` | JWT, bcrypt, `get_current_user`
`database.py` | engine, SessionLocal, Base, get_db
`models.py` | все SQLAlchemy-модели (8 enum + 9 таблиц)
`schemas.py` | все Pydantic-схемы
`fingerprint_api.py` | APIRouter `/api/fingerprint/*` (уже отдельный)
`face_recognition_service.py` | FaceRecognitionService (dlib)
`init_db.py` | скрипт инициализации тестовых данных

---

## Целевая декомпозиция

Блок монолита | Куда переносится
App Bootstrap | `app/main.py`
Вспомогательные функции | `app/core/dependencies.py`
Страничные маршруты | `app/api/routes/pages.py`
Auth/Token | `app/api/routes/auth.py`
Группы (чтение) | `app/api/routes/groups.py`
Студенты (чтение) | `app/api/routes/students.py`
Дисциплины (чтение) | `app/api/routes/disciplines.py`
Семестры (чтение) | `app/api/routes/schedule.py`
Расписание — чтение | `app/api/routes/schedule.py`
Посещаемость — запись | `app/api/routes/attendance.py`
Admin CRUD (студенты, группы, дисциплины) | доменные route-файлы
Admin CRUD (семестры, шаблоны) | `app/api/routes/schedule.py`
generate-instances логика | `app/services/schedule_service.py`
Отчёты — логика | `app/services/report_service.py`
Отчёты — маршруты | `app/api/routes/reports.py`
Биометрия — оркестрация | `app/services/biometric_service.py`
Биометрия — маршруты | `app/api/routes/biometric.py`
Дашборд | `app/api/routes/biometric.py` (или отдельный)
database.py | `app/db/session.py` + `app/db/base.py`
auth.py | `app/core/security.py`
