from __future__ import annotations

import pytest

from app.domain.exceptions import InvalidEmploymentPeriodError
from app.domain.value_objects.employment_period import EmploymentPeriod


def test_khoang_thoi_gian_hop_le_tinh_duoc_so_nam() -> None:
    period = EmploymentPeriod(start_year=2020, end_year=2024)
    assert period.duration_years == 4


def test_thieu_nam_thi_khong_doan() -> None:
    assert EmploymentPeriod(start_year=2020).duration_years is None


def test_dang_lam_viec_thi_end_year_phai_none() -> None:
    with pytest.raises(InvalidEmploymentPeriodError):
        EmploymentPeriod(start_year=2020, end_year=2024, is_current=True)


def test_end_year_khong_duoc_nho_hon_start_year() -> None:
    with pytest.raises(InvalidEmploymentPeriodError):
        EmploymentPeriod(start_year=2024, end_year=2020)
