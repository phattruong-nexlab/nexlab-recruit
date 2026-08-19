"""Cửa sổ trượt phải tính lúc CHẠY, không phải lúc cấu hình."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.application.ports.application_source import PendingFilter
from app.interface.jobs import extract_content


class SpyUseCase:
    def __init__(self) -> None:
        self.seen: PendingFilter | None = None

    async def execute(
        self, limit: int | None = None, pending_filter: PendingFilter | None = None
    ) -> Any:
        self.seen = pending_filter
        from app.application.dto.scan import ScanSummary

        return ScanSummary()


@pytest.fixture
def spy(monkeypatch: pytest.MonkeyPatch) -> SpyUseCase:
    use_case = SpyUseCase()
    monkeypatch.setattr(extract_content, "get_extract_use_case", lambda: use_case)
    return use_case


def test_khong_tham_so_thi_khong_loc(spy: SpyUseCase) -> None:
    assert extract_content.main([]) == 0
    assert spy.seen is not None
    assert spy.seen.is_empty


def test_since_days_tinh_ra_ngay_cu_the(spy: SpyUseCase) -> None:
    extract_content.main(["--since-days", "7"])

    expected = (datetime.now(UTC) - timedelta(days=7)).date().isoformat()
    assert spy.seen is not None
    assert spy.seen.since == expected


def test_since_tuong_minh_thang_since_days(spy: SpyUseCase) -> None:
    """Người dùng chỉ rõ ngày thì tôn trọng, không ghi đè bằng cửa sổ trượt."""
    extract_content.main(["--since", "2026-08-18", "--since-days", "7"])

    assert spy.seen is not None
    assert spy.seen.since == "2026-08-18"


def test_loc_theo_job(spy: SpyUseCase) -> None:
    extract_content.main(["--job", "junior-frontend"])

    assert spy.seen is not None
    assert spy.seen.job_url_contains == "junior-frontend"
