"""Bộ lọc chỉ THU HẸP phạm vi, không phải cơ chế chống trùng."""

from __future__ import annotations

from app.application.ports.application_source import PendingFilter
from app.infrastructure.notion.application_source import NotionApplicationSource


def _source() -> NotionApplicationSource:
    return NotionApplicationSource(api_key="x", data_source_id="ds")


def test_khong_loc_gi_thi_chi_kiem_tra_cot_dich_rong() -> None:
    built = _source()._build_filter(PendingFilter())

    assert built == {"property": "Resume Content", "rich_text": {"is_empty": True}}


def test_loc_theo_ngay() -> None:
    built = _source()._build_filter(PendingFilter(since="2026-08-18"))

    assert built["and"][0]["property"] == "Resume Content"
    # Có offset giờ VN — xem test_timezone_filter.py để biết vì sao.
    assert built["and"][1] == {
        "property": "Created time",
        "created_time": {"on_or_after": "2026-08-18T00:00:00+07:00"},
    }


def test_loc_theo_job() -> None:
    built = _source()._build_filter(PendingFilter(job_url_contains="junior-frontend"))

    assert built["and"][1] == {
        "property": "Job URL",
        "rich_text": {"contains": "junior-frontend"},
    }


def test_loc_ca_hai_thi_dieu_kien_cot_dich_van_con() -> None:
    """Bỏ mất điều kiện này là làm lại từ đầu những CV đã xong."""
    built = _source()._build_filter(PendingFilter(since="2026-08-18", job_url_contains="backend"))

    assert len(built["and"]) == 3
    assert built["and"][0] == {"property": "Resume Content", "rich_text": {"is_empty": True}}


def test_mo_ta_pham_vi_cho_nguoi_doc() -> None:
    assert PendingFilter().describe() == "tất cả"
    assert PendingFilter(since="2026-08-18").describe() == "từ 2026-08-18"
    assert "backend" in PendingFilter(job_url_contains="backend").describe()
