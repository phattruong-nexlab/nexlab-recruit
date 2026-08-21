"""Chọn đúng file trong cột `Resume, CL` khi ứng viên đính kèm nhiều file."""

from __future__ import annotations

from typing import Any

from app.infrastructure.notion.application_source import _cv_file_url


def _page(*files: tuple[str, str]) -> dict[str, Any]:
    """Dựng page Notion với các file external (Tally đính kèm kiểu này)."""
    return {
        "properties": {
            "Resume, CL": {
                "files": [
                    {"type": "external", "name": name, "external": {"url": url}}
                    for name, url in files
                ]
            }
        }
    }


def test_cover_letter_dung_truoc_thi_van_lay_dung_cv() -> None:
    """Chính là bug: 22/35 dòng nhiều file có cover letter ở vị trí đầu."""
    page = _page(
        ("LonYarHao_CoverLetter.pdf", "https://x/cl.pdf"),
        ("LON_YAR_HAO_CV.pdf", "https://x/cv.pdf"),
    )

    assert _cv_file_url(page) == "https://x/cv.pdf"


def test_cv_dung_truoc_thi_lay_luon() -> None:
    page = _page(
        ("Dinh_Dao_Quoc_Thinh_Backend_CV.pdf", "https://x/cv.pdf"),
        ("Dinh_Dao_Quoc_Thinh_coverletter.pdf", "https://x/cl.pdf"),
    )

    assert _cv_file_url(page) == "https://x/cv.pdf"


def test_chi_co_cover_letter_thi_coi_nhu_chua_co_cv() -> None:
    """Không được ghi nội dung cover letter vào `Resume Content`."""
    page = _page(("Cover Letter.docx", "https://x/cl.docx"))

    assert _cv_file_url(page) is None


def test_file_gop_ca_cv_lan_cover_letter_thi_van_doc() -> None:
    page = _page(("CV + Cover Letter.pdf", "https://x/gop.pdf"))

    assert _cv_file_url(page) == "https://x/gop.pdf"


def test_file_do_notion_luu_cung_nhan_duoc() -> None:
    page = {
        "properties": {
            "Resume, CL": {
                "files": [
                    {"type": "file", "name": "cover_letter.pdf", "file": {"url": "https://x/cl"}},
                    {"type": "file", "name": "resume.pdf", "file": {"url": "https://x/cv"}},
                ]
            }
        }
    }

    assert _cv_file_url(page) == "https://x/cv"


def test_cot_rong() -> None:
    assert _cv_file_url({"properties": {"Resume, CL": {"files": []}}}) is None
    assert _cv_file_url({"properties": {}}) is None
