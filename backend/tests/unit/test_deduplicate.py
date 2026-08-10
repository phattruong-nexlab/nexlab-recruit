"""Cùng một CV hay bị đính CẢ ở property lẫn trong nội dung trang."""

from __future__ import annotations

from pathlib import Path

from scripts.download_notion_files import NotionFile, _unique_path, deduplicate


def _file(page_id: str, name: str, source: str, query: str = "") -> NotionFile:
    return NotionFile(
        page_id=page_id,
        page_title="PM HIS senior",
        source=source,
        file_name=name,
        url=f"https://prod-files.notion-static.com/{name}{query}",
        is_external=False,
    )


def test_bo_ban_trung_du_chu_ky_url_khac_nhau() -> None:
    """Notion trả link có chữ ký khác nhau cho cùng một file — so sánh theo path."""
    files = [
        _file("page-1", "cv.pdf", "CV", query="?X-Amz-Signature=aaa"),
        _file("page-1", "cv.pdf", "block:pdf", query="?X-Amz-Signature=bbb"),
    ]

    unique = deduplicate(files)

    assert len(unique) == 1
    assert unique[0].source == "CV"  # giữ bản gặp trước


def test_cung_ten_file_o_hai_page_khac_nhau_thi_giu_ca_hai() -> None:
    files = [_file("page-1", "cv.pdf", "CV"), _file("page-2", "cv.pdf", "CV")]

    assert len(deduplicate(files)) == 2


def test_hai_file_khac_nhau_trung_ten_thi_them_hau_to() -> None:
    output_dir = Path("/out")
    taken: set[str] = set()

    first = _unique_path(output_dir, "a__b__cv.pdf", taken)
    second = _unique_path(output_dir, "a__b__cv.pdf", taken)
    third = _unique_path(output_dir, "a__b__cv.pdf", taken)

    assert first.name == "a__b__cv.pdf"
    assert second.name == "a__b__cv-2.pdf"
    assert third.name == "a__b__cv-3.pdf"
