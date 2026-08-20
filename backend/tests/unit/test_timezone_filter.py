"""Ngày HR chọn phải hiểu theo giờ Việt Nam, không phải UTC."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.application.ports.application_source import VN_TZ, PendingFilter
from app.infrastructure.notion.application_source import NotionApplicationSource
from app.interface.jobs import extract_content


def test_ngay_tran_duoc_gan_offset_gio_viet_nam() -> None:
    """Không có offset thì Notion hiểu là 00:00 UTC = 07:00 sáng VN, bỏ sót 7 tiếng."""
    assert PendingFilter(since="2026-08-19").since_for_notion == "2026-08-19T00:00:00+07:00"


def test_moc_day_du_thi_giu_nguyen() -> None:
    explicit = "2026-08-19T13:30:00+07:00"

    assert PendingFilter(since=explicit).since_for_notion == explicit


def test_khong_chon_ngay_thi_khong_loc_thoi_gian() -> None:
    assert PendingFilter().since_for_notion is None


def test_filter_gui_cho_notion_mang_offset() -> None:
    source = NotionApplicationSource(api_key="x", data_source_id="ds")

    built = source._build_filter(PendingFilter(since="2026-08-19"))

    assert built["and"][1]["created_time"]["on_or_after"] == "2026-08-19T00:00:00+07:00"


def test_describe_van_hien_ngay_cho_nguoi_doc() -> None:
    """HR thấy ngày mình chọn, không phải chuỗi ISO kèm offset."""
    assert PendingFilter(since="2026-08-19").describe() == "từ 2026-08-19"


def test_since_days_dem_theo_gio_viet_nam(monkeypatch) -> None:
    """Sát nửa đêm giờ VN, ngày UTC còn lùi thêm một hôm — phải theo VN."""
    seen: dict[str, str | None] = {}

    class Spy:
        async def execute(self, limit=None, pending_filter=None):
            from app.application.dto.scan import ScanSummary

            seen["since"] = pending_filter.since if pending_filter else None
            return ScanSummary()

    monkeypatch.setattr(extract_content, "get_extract_use_case", lambda: Spy())
    extract_content.main(["--since-days", "7"])

    expected = (datetime.now(VN_TZ) - timedelta(days=7)).date().isoformat()
    assert seen["since"] == expected
