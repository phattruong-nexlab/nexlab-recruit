"""Nhân bản hàng loạt: một dòng hỏng không được làm chết cả lượt."""

from __future__ import annotations

from app.application.ports.application_source import PendingApplication
from app.application.use_cases.mirror_applications import MirrorApplicationsUseCase
from tests.conftest import FakeDownloader, FakeMirror, FakeSource, make_application


def _use_case(
    items: list[PendingApplication],
    mirror: FakeMirror | None = None,
    downloader: FakeDownloader | None = None,
) -> MirrorApplicationsUseCase:
    return MirrorApplicationsUseCase(
        source=FakeSource(items),
        downloader=downloader or FakeDownloader(),
        mirror=mirror or FakeMirror(),
        concurrency=3,
    )


async def test_nhan_ban_het_cac_dong(applications: list[PendingApplication]) -> None:
    mirror = FakeMirror()

    summary = await _use_case(applications, mirror).execute()

    assert summary.total == 5
    assert summary.succeeded == 5
    assert len(mirror.rows) == 5


async def test_cv_duoc_tai_va_dua_sang_mirror(applications: list[PendingApplication]) -> None:
    mirror = FakeMirror()
    downloader = FakeDownloader()

    await _use_case(applications, mirror, downloader).execute()

    assert len(downloader.calls) == 5
    assert all(cv is not None for _, cv in mirror.rows)


async def test_dong_chua_dinh_cv_van_duoc_nhan_ban() -> None:
    """Chép được cột nào hay cột đó; lượt sau CV về thì chép lại."""
    mirror = FakeMirror()
    downloader = FakeDownloader()

    summary = await _use_case([make_application(1, with_cv=False)], mirror, downloader).execute()

    assert summary.succeeded == 1
    assert downloader.calls == []  # không có link thì không gọi tải
    assert mirror.rows[0][1] is None


async def test_tai_cv_loi_van_chep_cac_cot_con_lai(
    applications: list[PendingApplication],
) -> None:
    mirror = FakeMirror()

    summary = await _use_case(applications, mirror, FakeDownloader(should_fail=True)).execute()

    assert summary.succeeded == 5
    assert all(cv is None for _, cv in mirror.rows)


async def test_ghi_notion_loi_thi_dem_la_that_bai(
    applications: list[PendingApplication],
) -> None:
    summary = await _use_case(applications, FakeMirror(should_fail=True)).execute()

    assert summary.failed == 5
    assert summary.succeeded == 0
    assert "CandidatePublishError" in summary.failures[0].reason


async def test_limit_chi_lam_n_dong_dau(applications: list[PendingApplication]) -> None:
    mirror = FakeMirror()

    summary = await _use_case(applications, mirror).execute(limit=2)

    assert summary.total == 2
    assert len(mirror.rows) == 2
