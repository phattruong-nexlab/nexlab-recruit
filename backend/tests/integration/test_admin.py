"""Trang quản trị — kiểm tra qua đúng HTTP mà trình duyệt HR sẽ dùng."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from starlette.applications import Starlette

from app.application.dto.scan import ScanSummary
from app.application.use_cases.extract_resume_content import ExtractResumeContentUseCase
from app.interface.web import admin as admin_module

_PASSWORD = "hr-secret"


class FakeScan(ExtractResumeContentUseCase):
    """Chỉ cần đếm — không chạm Notion."""

    def __init__(self, pending: int) -> None:  # không gọi super()
        self._pending = pending

    async def count_pending(self) -> int:
        return self._pending

    async def execute(self, limit: int | None = None) -> ScanSummary:
        raise AssertionError("Trang quản trị KHÔNG được tự xử lý — phải giao cho job")


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> Starlette:
    monkeypatch.setenv("ADMIN_PASSWORD", _PASSWORD)
    monkeypatch.setenv("CLOUD_RUN_JOB_NAME", "")

    from config import get_settings

    get_settings.cache_clear()
    monkeypatch.setattr(admin_module, "get_extract_use_case", lambda: FakeScan(12))

    import main

    created: Starlette = main.create_app()
    get_settings.cache_clear()
    return created


def _client(app: Starlette) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_health_khong_can_dang_nhap(app: Starlette) -> None:
    async with _client(app) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_chua_dang_nhap_thi_chuyen_sang_trang_login(app: Starlette) -> None:
    async with _client(app) as client:
        response = await client.get("/admin")

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"


async def test_api_chua_dang_nhap_tra_401(app: Starlette) -> None:
    async with _client(app) as client:
        assert (await client.get("/admin/pending")).status_code == 401
        assert (await client.post("/admin/run")).status_code == 401


async def test_sai_mat_khau_bi_tu_choi(app: Starlette) -> None:
    async with _client(app) as client:
        response = await client.post("/admin/login", data={"password": "sai"})

    assert response.status_code == 401


async def test_dang_nhap_dung_roi_xem_duoc_so_cv_cho(app: Starlette) -> None:
    async with _client(app) as client:
        login = await client.post("/admin/login", data={"password": _PASSWORD})
        assert login.status_code == 303

        page = await client.get("/admin")
        assert page.status_code == 200

        pending = await client.get("/admin/pending")

    assert pending.json() == {"pending": 12}


async def test_chua_cau_hinh_job_thi_bao_loi_ro_rang(app: Starlette) -> None:
    """Không được im lặng: HR bấm nút mà không có job thì phải nói vì sao."""
    async with _client(app) as client:
        await client.post("/admin/login", data={"password": _PASSWORD})
        response = await client.post("/admin/run")

    assert response.status_code == 503
    assert "CLOUD_RUN_JOB_NAME" in response.json()["error"]


async def test_thieu_tham_so_execution(app: Starlette) -> None:
    async with _client(app) as client:
        await client.post("/admin/login", data={"password": _PASSWORD})
        response = await client.get("/admin/status")

    assert response.status_code == 400


async def test_cookie_ky_bang_mat_khau_nen_doi_mat_khau_la_het_phien(
    app: Starlette, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with _client(app) as client:
        await client.post("/admin/login", data={"password": _PASSWORD})
        assert (await client.get("/admin/pending")).status_code == 200

        from config import get_settings

        monkeypatch.setenv("ADMIN_PASSWORD", "mat-khau-moi")
        get_settings.cache_clear()

        after: Any = await client.get("/admin/pending")

    get_settings.cache_clear()
    assert after.status_code == 401
