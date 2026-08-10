from __future__ import annotations

import pytest

from app.domain.services.applied_job import from_job_url


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://nexlab.tech/jobs/senior-data-engineer", "Senior Data Engineer"),
        ("https://nexlab.tech/jobs/intern-ai-engineer", "Intern AI Engineer"),
        ("https://nexlab.tech/jobs/pm-ba-senior/", "PM BA Senior"),
        ("/jobs/hr-specialist", "HR Specialist"),
        ("senior_backend_engineer", "Senior Backend Engineer"),
    ],
)
def test_suy_ten_vi_tri_tu_slug(url: str, expected: str) -> None:
    assert from_job_url(url) == expected


@pytest.mark.parametrize("url", [None, "", "   ", "https://nexlab.tech/"])
def test_khong_suy_duoc_thi_tra_none(url: str | None) -> None:
    assert from_job_url(url) is None
