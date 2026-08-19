"""HR chọn giờ dạng HH:MM, không phải gõ cron."""

from __future__ import annotations

import pytest

from app.domain.exceptions import DomainError
from app.infrastructure.gcp.scheduler import Schedule, to_daily_cron


@pytest.mark.parametrize(
    ("time_of_day", "cron"),
    [
        ("02:00", "0 2 * * *"),
        ("18:30", "30 18 * * *"),
        ("00:05", "5 0 * * *"),
        ("23:59", "59 23 * * *"),
    ],
)
def test_doi_gio_thanh_cron(time_of_day: str, cron: str) -> None:
    assert to_daily_cron(time_of_day) == cron


@pytest.mark.parametrize("value", ["", "2", "25:00", "12:60", "ab:cd", "2:00:00"])
def test_gio_khong_hop_le_bi_tu_choi(value: str) -> None:
    with pytest.raises(DomainError):
        to_daily_cron(value)


@pytest.mark.parametrize(
    ("cron", "expected"),
    [("0 2 * * *", "02:00"), ("30 18 * * *", "18:30"), ("5 0 * * *", "00:05")],
)
def test_doc_nguoc_cron_thanh_gio(cron: str, expected: str) -> None:
    assert Schedule(cron=cron, timezone="Asia/Ho_Chi_Minh", enabled=True).time_of_day == expected


@pytest.mark.parametrize("cron", ["*/15 * * * *", "0 2 * * 1", "0 2 1 * *"])
def test_cron_phuc_tap_khong_ep_ve_gio(cron: str) -> None:
    """Lịch không phải 'mỗi ngày một lần' thì hiển thị nguyên cron, không đoán bừa."""
    assert Schedule(cron=cron, timezone="UTC", enabled=True).time_of_day is None
