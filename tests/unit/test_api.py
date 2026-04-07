"""Smoke tests for the FastAPI web UI."""

import pytest
from httpx import ASGITransport, AsyncClient

from assistant.api import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_index_returns_html(client):
    """GET / returns the main page with the skill form."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "Run a Skill" in response.text
    assert "meeting_to_actions" in response.text


@pytest.mark.asyncio
async def test_history_page(client):
    """GET /history returns the history page."""
    response = await client.get("/history")
    assert response.status_code == 200
    assert "History" in response.text or "No outputs" in response.text


@pytest.mark.asyncio
async def test_usage_page(client):
    """GET /usage returns the usage page."""
    response = await client.get("/usage")
    assert response.status_code == 200
    assert "Usage" in response.text or "No usage" in response.text


@pytest.mark.asyncio
async def test_run_without_input(client):
    """POST /run with empty input returns an error message."""
    response = await client.post(
        "/run",
        data={"skill_name": "meeting_to_actions", "input_text": ""},
    )
    assert response.status_code == 200
    assert "Please paste some text" in response.text
