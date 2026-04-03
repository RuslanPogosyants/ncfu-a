"""Tests for attendance records endpoints."""
from datetime import date, timedelta

import pytest

from app.models import ScheduleInstance


@pytest.mark.asyncio
async def test_get_records_empty(client, admin_token, admin, past_instance, student):
    resp = await client.get(
        f"/api/schedules/{past_instance.id}/records",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["student_id"] == student.id
    assert body[0]["record_id"] is None


@pytest.mark.asyncio
async def test_get_records_teacher_own_class(
    client, teacher_token, teacher, past_instance, student
):
    resp = await client.get(
        f"/api/schedules/{past_instance.id}/records",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_records_teacher_other_class(
    client, db, teacher_token, teacher, past_instance
):
    """Teacher cannot view records for another teacher's class."""
    from app.models import User, UserRole
    from app.core.security import get_password_hash

    other = User(
        username="other_teacher",
        hashed_password=get_password_hash("pass"),
        full_name="Other Teacher",
        role=UserRole.TEACHER,
    )
    db.add(other)
    db.commit()
    db.refresh(other)

    # Assign the instance explicitly to `other`
    past_instance.teacher_id = other.id
    db.commit()

    resp = await client.get(
        f"/api/schedules/{past_instance.id}/records",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_records_not_found(client, admin_token, admin):
    resp = await client.get(
        "/api/schedules/99999/records",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_record_past_instance(
    client, admin_token, admin, past_instance, student
):
    resp = await client.post(
        "/api/records",
        data={
            "student_id": student.id,
            "schedule_id": past_instance.id,
            "status": "absent",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "absent"
    assert body["student_id"] == student.id


@pytest.mark.asyncio
async def test_create_record_future_instance_forbidden(
    client, admin_token, admin, db, schedule_template, semester, student
):
    future = ScheduleInstance(
        template_id=schedule_template.id,
        semester_id=semester.id,
        date=date.today() + timedelta(days=7),
        is_cancelled=False,
    )
    db.add(future)
    db.commit()
    db.refresh(future)

    resp = await client.post(
        "/api/records",
        data={"student_id": student.id, "schedule_id": future.id, "status": "present"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_record_cancelled_instance_forbidden(
    client, admin_token, admin, db, schedule_template, semester, student
):
    cancelled = ScheduleInstance(
        template_id=schedule_template.id,
        semester_id=semester.id,
        date=date.today() - timedelta(days=3),
        is_cancelled=True,
    )
    db.add(cancelled)
    db.commit()
    db.refresh(cancelled)

    resp = await client.post(
        "/api/records",
        data={
            "student_id": student.id,
            "schedule_id": cancelled.id,
            "status": "present",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_existing_record(
    client, admin_token, admin, past_instance, student
):
    """Posting twice should update the existing record, not create a duplicate."""
    await client.post(
        "/api/records",
        data={
            "student_id": student.id,
            "schedule_id": past_instance.id,
            "status": "present",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.post(
        "/api/records",
        data={
            "student_id": student.id,
            "schedule_id": past_instance.id,
            "status": "absent",
            "grade": "4",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "absent"
    assert body["grade"] == 4

    # Verify via GET that only one record exists
    records_resp = await client.get(
        f"/api/schedules/{past_instance.id}/records",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    records = records_resp.json()
    student_records = [r for r in records if r["student_id"] == student.id]
    assert len(student_records) == 1
    assert student_records[0]["status"] == "absent"
