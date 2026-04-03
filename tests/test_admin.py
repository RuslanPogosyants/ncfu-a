"""Tests for admin CRUD: groups, students, disciplines."""
import pytest


# ── Groups ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_groups_empty(client, admin_token, admin):
    resp = await client.get(
        "/api/groups", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_groups_returns_list(client, admin_token, admin, group):
    resp = await client.get(
        "/api/groups", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    names = [g["name"] for g in resp.json()]
    assert "CS-101" in names


@pytest.mark.asyncio
async def test_create_group_admin(client, admin_token, admin):
    resp = await client.post(
        "/api/admin/groups",
        data={"name": "CS-202"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "CS-202"
    assert "id" in body


@pytest.mark.asyncio
async def test_create_group_teacher_forbidden(client, teacher_token, teacher):
    resp = await client.post(
        "/api/admin/groups",
        data={"name": "CS-303"},
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_group_duplicate_name(client, admin_token, admin, group):
    resp = await client.post(
        "/api/admin/groups",
        data={"name": "CS-101"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_delete_group_success(client, admin_token, admin, group):
    resp = await client.delete(
        f"/api/admin/groups/{group.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_delete_group_with_students(client, admin_token, admin, student, group):
    resp = await client.delete(
        f"/api/admin/groups/{group.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400


# ── Students ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_students_paginated(client, admin_token, admin, student):
    resp = await client.get(
        "/api/students", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "meta" in body
    assert len(body["items"]) == 1
    assert body["items"][0]["full_name"] == "Иванов Иван Иванович"


@pytest.mark.asyncio
async def test_create_student_admin(client, admin_token, admin, group):
    resp = await client.post(
        "/api/admin/students",
        data={"full_name": "Петров Петр Петрович", "group_id": group.id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["full_name"] == "Петров Петр Петрович"
    assert body["group_id"] == group.id


@pytest.mark.asyncio
async def test_create_student_teacher_forbidden(client, teacher_token, teacher, group):
    resp = await client.post(
        "/api/admin/students",
        data={"full_name": "Сидоров Сидор", "group_id": group.id},
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_student_success(client, admin_token, admin, student):
    resp = await client.delete(
        f"/api/admin/students/{student.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_delete_student_not_found(client, admin_token, admin):
    resp = await client.delete(
        "/api/admin/students/99999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


# ── Disciplines ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_disciplines_returns_list(client, admin_token, admin, discipline):
    resp = await client.get(
        "/api/disciplines", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    names = [d["name"] for d in resp.json()]
    assert "Math" in names


@pytest.mark.asyncio
async def test_create_discipline_admin(client, admin_token, admin):
    resp = await client.post(
        "/api/admin/disciplines",
        data={"name": "Физика"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Физика"


@pytest.mark.asyncio
async def test_create_discipline_duplicate(client, admin_token, admin, discipline):
    resp = await client.post(
        "/api/admin/disciplines",
        data={"name": "Math"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_delete_discipline_success(client, admin_token, admin, discipline):
    resp = await client.delete(
        f"/api/admin/disciplines/{discipline.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True
