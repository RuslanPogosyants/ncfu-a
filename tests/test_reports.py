"""Tests for /api/reports/journal and /api/reports/summary."""
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── Journal report ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_journal_report_json(
    client, admin_token, admin, past_instance, student, group, discipline
):
    resp = await client.get(
        "/api/reports/journal",
        params={
            "group_id": group.id,
            "date_from": "2026-01-01",
            "date_to": "2026-12-31",
            "format": "json",
        },
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["group"]["id"] == group.id
    assert "rows" in body
    assert len(body["rows"]) >= 1


@pytest.mark.asyncio
async def test_journal_report_csv(
    client, admin_token, admin, past_instance, student, group
):
    resp = await client.get(
        "/api/reports/journal",
        params={
            "group_id": group.id,
            "date_from": "2026-01-01",
            "date_to": "2026-12-31",
            "format": "csv",
        },
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_journal_report_group_not_found(client, admin_token, admin):
    resp = await client.get(
        "/api/reports/journal",
        params={"group_id": 99999, "date_from": "2026-01-01", "date_to": "2026-12-31"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_journal_report_invalid_date_range(
    client, admin_token, admin, group, student
):
    resp = await client.get(
        "/api/reports/journal",
        params={
            "group_id": group.id,
            "date_from": "2026-12-31",
            "date_to": "2026-01-01",
        },
        headers=_auth(admin_token),
    )
    assert resp.status_code == 400


# ── Summary report ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_summary_report_with_data(
    client, admin_token, admin, past_instance, student, group
):
    resp = await client.get(
        "/api/reports/summary",
        params={
            "group_id": group.id,
            "date_from": "2026-01-01",
            "date_to": "2026-12-31",
        },
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["group"]["id"] == group.id
    assert "attendance" in body or "lessons_found" in body


@pytest.mark.asyncio
async def test_summary_report_no_lessons(
    client, admin_token, admin, group, student
):
    """With a group that has students but no schedule instances in range → empty stats."""
    resp = await client.get(
        "/api/reports/summary",
        params={
            "group_id": group.id,
            "date_from": "2020-01-01",
            "date_to": "2020-01-31",
        },
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    # When no instances exist the route returns early with attendance.total_lessons == 0
    assert body["attendance"]["total_lessons"] == 0
