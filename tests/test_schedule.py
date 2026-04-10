"""Tests for semester and schedule-template management."""
import pytest


# ── Semesters ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_semesters_empty(client, admin_token, admin):
    resp = await client.get(
        "/api/semesters", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_semesters_returns_list(client, admin_token, admin, semester):
    resp = await client.get(
        "/api/semesters", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    names = [s["name"] for s in resp.json()]
    assert "Весна 2026" in names


@pytest.mark.asyncio
async def test_create_semester_admin(client, admin_token, admin):
    resp = await client.post(
        "/api/admin/semesters",
        json={"name": "Осень 2026", "start_date": "2026-09-01", "end_date": "2027-01-31"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Осень 2026"
    assert body["success"] is True


@pytest.mark.asyncio
async def test_create_semester_teacher_forbidden(client, teacher_token, teacher):
    resp = await client.post(
        "/api/admin/semesters",
        json={"name": "X", "start_date": "2026-09-01", "end_date": "2027-01-31"},
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_semester_invalid_dates(client, admin_token, admin):
    resp = await client.post(
        "/api/admin/semesters",
        json={"name": "Bad", "start_date": "2026-12-01", "end_date": "2026-09-01"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_delete_semester(client, admin_token, admin, semester):
    resp = await client.delete(
        f"/api/admin/semesters/{semester.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_delete_semester_not_found(client, admin_token, admin):
    resp = await client.delete(
        "/api/admin/semesters/99999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


# ── Schedule templates ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_templates_no_active_semester(client, admin_token, admin):
    resp = await client.get(
        "/api/admin/schedule-templates",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_get_templates_with_data(client, admin_token, admin, schedule_template):
    resp = await client.get(
        "/api/admin/schedule-templates",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["discipline"] == "Math"


@pytest.mark.asyncio
async def test_create_template(
    client, admin_token, admin, semester, discipline, teacher, group
):
    resp = await client.post(
        "/api/admin/schedule-templates",
        json={
            "discipline_id": discipline.id,
            "teacher_id": teacher.id,
            "lesson_type": "Л",
            "classroom": "201",
            "day_of_week": 1,
            "time_start": "10:00",
            "time_end": "11:30",
            "week_type": "both",
            "group_ids": [group.id],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_generate_instances(client, admin_token, admin, schedule_template):
    resp = await client.post(
        "/api/admin/generate-instances",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["count"] >= 0
