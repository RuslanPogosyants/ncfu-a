"""Tests for /token and /api/me endpoints."""
import pytest


@pytest.mark.asyncio
async def test_login_admin_success(client, admin):
    resp = await client.post(
        "/token", data={"username": "admin", "password": "adminpass"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_teacher_success(client, teacher):
    resp = await client.post(
        "/token", data={"username": "teacher", "password": "teacherpass"}
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client, admin):
    resp = await client.post(
        "/token", data={"username": "admin", "password": "wrongpass"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client):
    resp = await client.post(
        "/token", data={"username": "nobody", "password": "pass"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_admin(client, admin, admin_token):
    resp = await client.get(
        "/api/me", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "admin"
    assert body["role"] == "admin"


@pytest.mark.asyncio
async def test_me_teacher(client, teacher, teacher_token):
    resp = await client.get(
        "/api/me", headers={"Authorization": f"Bearer {teacher_token}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "teacher"
    assert body["role"] == "teacher"


@pytest.mark.asyncio
async def test_me_no_token(client):
    resp = await client.get("/api/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_invalid_token(client):
    resp = await client.get(
        "/api/me", headers={"Authorization": "Bearer totally.invalid.token"}
    )
    assert resp.status_code == 401
