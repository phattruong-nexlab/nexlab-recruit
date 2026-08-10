"""Kiểm tra MCP server qua đúng giao thức HTTP mà agent sẽ dùng."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
import pytest
from starlette.applications import Starlette

from app.application.dto.parse_cv import ParseCvResult
from app.application.use_cases.parse_cv import ParseCvUseCase
from app.interface.mcp import server as server_module
from tests.conftest import FakeDownloader, FakeExtractor, FakePublisher, FakeReader

_TOKEN = "test-token"
_MCP_HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {_TOKEN}",
}
_INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1"},
    },
}


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch, extracted_cv: Any) -> Starlette:
    monkeypatch.setenv("MCP_AUTH_TOKEN", _TOKEN)
    monkeypatch.setenv("GEMINI_API_KEY", "fake")

    from config import get_settings

    get_settings.cache_clear()

    def fake_use_case() -> ParseCvUseCase:
        return ParseCvUseCase(
            downloader=FakeDownloader(),
            reader=FakeReader(),
            extractor=FakeExtractor(extracted_cv),
            publisher=FakePublisher(page_id="page-xyz"),
        )

    monkeypatch.setattr(server_module, "get_parse_cv_use_case", fake_use_case)

    import main

    created: Starlette = main.create_app()
    get_settings.cache_clear()
    return created


@asynccontextmanager
async def running(app: Starlette) -> AsyncIterator[httpx.AsyncClient]:
    """Chạy lifespan + client trong CÙNG một task.

    Không tách ra fixture async được: pytest-asyncio chạy setup và teardown ở hai
    task khác nhau, làm vỡ cancel scope của anyio mà MCP session manager dùng.
    """
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            yield http


async def _call(http: httpx.AsyncClient, method: str, params: Any = None) -> dict[str, Any]:
    body: dict[str, Any] = {"jsonrpc": "2.0", "id": 2, "method": method}
    if params is not None:
        body["params"] = params
    response = await http.post("/mcp/", json=body, headers=_MCP_HEADERS)
    response.raise_for_status()
    return _parse_body(response)


def _parse_body(response: httpx.Response) -> dict[str, Any]:
    """Server có thể trả JSON thuần hoặc SSE tuỳ negotiation."""
    if response.headers.get("content-type", "").startswith("text/event-stream"):
        for line in response.text.splitlines():
            if line.startswith("data: "):
                return dict(json.loads(line[6:]))
        raise AssertionError(f"SSE không có data: {response.text!r}")
    return dict(response.json())


async def test_health_khong_can_token(app: Starlette) -> None:
    async with running(app) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_thieu_token_bi_tu_choi(app: Starlette) -> None:
    async with running(app) as client:
        response = await client.post("/mcp/", json=_INITIALIZE)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


async def test_sai_token_bi_tu_choi(app: Starlette) -> None:
    headers = _MCP_HEADERS | {"Authorization": "Bearer sai-token"}

    async with running(app) as client:
        response = await client.post("/mcp/", json=_INITIALIZE, headers=headers)

    assert response.status_code == 401


async def test_expose_dung_tool_parse_cv(app: Starlette) -> None:
    async with running(app) as client:
        await _call(client, "initialize", _INITIALIZE["params"])
        body = await _call(client, "tools/list")

    tools = {tool["name"]: tool for tool in body["result"]["tools"]}
    assert "parse_cv" in tools

    schema = tools["parse_cv"]["inputSchema"]
    assert schema["required"] == ["file_url"]
    assert set(schema["properties"]) == {
        "file_url",
        "job_url",
        "email",
        "phone",
        "created_time",
    }


async def test_goi_tool_tra_ve_bay_nhom_thong_tin(app: Starlette) -> None:
    async with running(app) as client:
        await _call(client, "initialize", _INITIALIZE["params"])
        body = await _call(
            client,
            "tools/call",
            {
                "name": "parse_cv",
                "arguments": {
                    "file_url": "https://file.notion.so/cv.pdf",
                    "job_url": "https://nexlab.tech/jobs/senior-data-engineer",
                    "email": "a@example.com",
                },
            },
        )

    result = body["result"]
    assert result.get("isError") is not True
    data = result["structuredContent"]
    assert data["full_name"] == "Trần Khánh Hoà"
    assert data["applied_job"] == "Senior Data Engineer"
    assert data["university"] == "Đại học Bách Khoa"
    assert data["gpa"] == 3.6
    assert data["skills"] == ["Python", "SQL"]
    assert data["certificates"] == ["AWS Certified"]
    assert data["languages"] == ["Tiếng Việt", "English"]
    assert data["published"] is True
    assert data["notion_page_id"] == "page-xyz"


async def test_ket_qua_khop_dto_use_case() -> None:
    """Bảo vệ khỏi việc thêm field vào DTO mà quên expose ra tool."""
    tool_fields = set(server_module.ParseCvOut.model_fields)
    dto_fields = set(ParseCvResult.__dataclass_fields__)

    assert dto_fields <= tool_fields
