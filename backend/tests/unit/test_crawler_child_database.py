"""Cấu trúc thật ở nexlab: Job Post → mỗi dòng có bảng lồng "Job Application" → ứng viên → CV.

Không đi xuyên qua bảng lồng thì không tìm thấy CV nào.
"""

from __future__ import annotations

from typing import Any

import pytest

from scripts.download_notion_files import Crawler


def _page(page_id: str, title: str, cv: str | None = None) -> dict[str, Any]:
    props: dict[str, Any] = {"Name": {"type": "title", "title": [{"plain_text": title}]}}
    if cv:
        props["CV"] = {
            "type": "files",
            "files": [{"type": "file", "name": cv, "file": {"url": f"https://x/{cv}"}}],
        }
    return {"id": page_id, "properties": props}


# Job Post (bảng gốc) -> 1 dòng "PM/BA Senior" -> bảng lồng "Job Application" -> 2 ứng viên
_JOB_POST_DB = "db-jobpost"
_APPLICATION_DB = "db-application"

_DATA_SOURCES = {_JOB_POST_DB: "ds-jobpost", _APPLICATION_DB: "ds-application"}

_ROWS: dict[str, list[dict[str, Any]]] = {
    "ds-jobpost": [_page("page-job-1", "PM/BA Senior")],
    "ds-application": [
        _page("page-cand-1", "Ha Thi Ngoc Thao", cv="thao_cv.pdf"),
        _page("page-cand-2", "Ma Ngoc Nha Vy", cv="vy_cv.pdf"),
    ],
}

_BLOCKS: dict[str, list[dict[str, Any]]] = {
    # Trong trang job post có một bảng lồng
    "page-job-1": [{"id": _APPLICATION_DB, "type": "child_database", "has_children": True}],
    "page-cand-1": [],
    "page-cand-2": [],
}


class FakeNotion:
    """Giả lập đủ 4 endpoint mà Crawler dùng."""

    def __init__(self) -> None:
        outer = self

        class Databases:
            def retrieve(self, database_id: str) -> Any:
                outer.calls.append(f"databases.retrieve:{database_id}")
                if database_id not in _DATA_SOURCES:
                    raise AssertionError(f"database lạ: {database_id}")
                return {"data_sources": [{"id": _DATA_SOURCES[database_id], "name": "x"}]}

        class DataSources:
            def query(
                self, data_source_id: str, start_cursor: str | None = None, page_size: int = 100
            ) -> Any:
                outer.calls.append(f"query:{data_source_id}")
                return {"results": _ROWS[data_source_id], "has_more": False, "next_cursor": None}

        class Children:
            def list(
                self, block_id: str, start_cursor: str | None = None, page_size: int = 100
            ) -> Any:
                return {
                    "results": _BLOCKS.get(block_id, []),
                    "has_more": False,
                    "next_cursor": None,
                }

        self.calls: list[str] = []
        self.databases = Databases()
        self.data_sources = DataSources()
        self.blocks = type("Blocks", (), {"children": Children()})()


def test_di_xuyen_bang_long_lay_duoc_cv_cua_ung_vien() -> None:
    crawler = Crawler(FakeNotion())  # type: ignore[arg-type]

    crawler.crawl_database(_JOB_POST_DB)

    assert sorted(f.file_name for f in crawler.files) == ["thao_cv.pdf", "vy_cv.pdf"]
    assert sorted(f.page_title for f in crawler.files) == ["Ha Thi Ngoc Thao", "Ma Ngoc Nha Vy"]


def test_tat_co_bang_long_thi_khong_thay_gi() -> None:
    crawler = Crawler(FakeNotion(), follow_child_databases=False)  # type: ignore[arg-type]

    crawler.crawl_database(_JOB_POST_DB)

    assert crawler.files == []


def test_khong_query_lai_bang_da_tham() -> None:
    """Notion cho nhúng chéo — phải chống lặp vô hạn."""
    client = FakeNotion()
    crawler = Crawler(client)  # type: ignore[arg-type]

    crawler.crawl_database(_JOB_POST_DB)
    crawler.crawl_database(_APPLICATION_DB)  # đã thăm ở lượt trên

    assert client.calls.count(f"query:{_DATA_SOURCES[_APPLICATION_DB]}") == 1


@pytest.mark.parametrize("run_twice", [False, True])
def test_khong_lay_trung_khi_crawl_lai_cung_page(run_twice: bool) -> None:
    crawler = Crawler(FakeNotion())  # type: ignore[arg-type]

    crawler.crawl_database(_JOB_POST_DB)
    if run_twice:
        crawler.crawl_page(_ROWS["ds-application"][0])

    assert len(crawler.files) == 2
