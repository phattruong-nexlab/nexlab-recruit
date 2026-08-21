"""Phân biệt CV / cover letter — tên file lấy từ dữ liệu thật trên Notion."""

from __future__ import annotations

import pytest

from app.domain.cv_files import is_cover_letter


@pytest.mark.parametrize(
    "name",
    [
        "Cover Letter.pdf",
        "cover_letter.pdf",
        "CoverLetter.docx",
        "CoverLetter_to_Nexlab.pdf",
        "Huy Nguyen - Fullstack Engineer - Cover Letter.pdf",
        "Cover_Letter_Nexlab_Tran_Van_Than.pdf",
        "VO NHAN QUYEN - Reference Letter.pdf",
        # "TopCV" không được tính là CV: có chữ cái đứng ngay trước "CV".
        "Do-Thi-Hong-Nhung-CoverLetter-TopCV.vn-220126.114926.pdf",
    ],
)
def test_cover_letter_thuan_thi_bo(name: str) -> None:
    assert is_cover_letter(name) is True


@pytest.mark.parametrize(
    "name",
    [
        "LON_YAR_HAO_CV.pdf",
        "resume.pdf",
        "Nguyen Le Nhat Dang Quang_Resume_BA.pdf",
        "CV-VO-THANG-NHAN-Technical-BA.docx",
        "2352378_HoMinhHuy.pdf",
        "AI Engineer_La Cam Huy.pdf",
    ],
)
def test_cv_thi_giu(name: str) -> None:
    assert is_cover_letter(name) is False


@pytest.mark.parametrize(
    "name",
    [
        "CV + Cover Letter.pdf",
        "CV_and_Cover_Letter_Nexlab.pdf",
        "CaoHoangNguyen_NexLab_CV_CoverLetter.pdf",
        "Bùi Nguyễn Thùy Linh _ CV&CoverLetter_NexLab.pdf",
        "CV_LE DUC PHAT & Cover Letter.pdf",
        "An-Do-Resume-n-Cover-Letter.zip",
    ],
)
def test_file_gop_ca_hai_thi_van_doc(name: str) -> None:
    """Bỏ những file này là mất luôn CV của ứng viên — 30 dòng trên bảng thật."""
    assert is_cover_letter(name) is False


def test_khong_co_ten_thi_cu_doc() -> None:
    """Thà đọc thừa còn hơn bỏ sót CV vì Notion không trả tên file."""
    assert is_cover_letter("") is False
