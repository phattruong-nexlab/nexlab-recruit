"""Gộp nhiều bảng nguồn: tổng phải đúng và limit không được nhân lên."""

from __future__ import annotations

from app.application.composite_source import CompositeApplicationSource
from app.application.ports.application_source import PendingFilter
from tests.conftest import FakeSource, make_application


def _source(prefix: str, n: int, job: str = "/jobs/be") -> FakeSource:
    items = [make_application(i, job_url=job) for i in range(n)]
    for item in items:
        item.source_page_id = f"{prefix}-{item.source_page_id}"
    return FakeSource(items)


async def test_gop_du_ca_hai_bang() -> None:
    composite = CompositeApplicationSource([_source("a", 3), _source("b", 2)])

    pending = await composite.list_pending()

    assert len(pending) == 5
    assert {p.source_page_id.split("-")[0] for p in pending} == {"a", "b"}


async def test_limit_ap_len_tong_khong_phai_tung_bang() -> None:
    """Truyền limit xuống từng bảng thì 2 bảng x limit 3 = 6, vượt yêu cầu."""
    composite = CompositeApplicationSource([_source("a", 5), _source("b", 5)])

    pending = await composite.list_pending(limit=3)

    assert len(pending) == 3


async def test_dem_gop_ca_hai_bang() -> None:
    composite = CompositeApplicationSource([_source("a", 4), _source("b", 6)])

    assert await composite.count_pending() == 10


async def test_bo_loc_ap_cho_moi_bang() -> None:
    composite = CompositeApplicationSource(
        [_source("a", 3, job="/jobs/frontend"), _source("b", 3, job="/jobs/backend")]
    )

    pending = await composite.list_pending(
        pending_filter=PendingFilter(job_url_contains="frontend")
    )

    assert len(pending) == 3
    assert all("frontend" in p.job_url for p in pending)


async def test_mot_bang_rong_khong_anh_huong() -> None:
    composite = CompositeApplicationSource([_source("a", 0), _source("b", 2)])

    assert len(await composite.list_pending()) == 2
