from __future__ import annotations

import pytest

from scripts.download_notion_files import NotionFile, normalize_notion_id

_EXPECTED = "25d2c7d6-a903-802d-a4a8-cba604f09689"


@pytest.mark.parametrize(
    "raw",
    [
        "25d2c7d6a903802da4a8cba604f09689",
        "25d2c7d6-a903-802d-a4a8-cba604f09689",
        "  25d2c7d6a903802da4a8cba604f09689  ",
        (
            "https://app.notion.com/p/nexlabtechnology/25d2c7d6a903802da4a8cba604f09689"
            "?v=25d2c7d6a9038078a8cf000c3d78bc6b&source=copy_link"
        ),
    ],
)
def test_chap_nhan_ca_url_lan_id_tho(raw: str) -> None:
    assert normalize_notion_id(raw) == _EXPECTED


def test_khong_lay_nham_view_id_trong_query_string() -> None:
    """`?v=` cũng là một id 32 ký tự — không được nhận nhầm nó là database id."""
    url = "https://app.notion.com/p/ws/25d2c7d6a903802da4a8cba604f09689?v=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    assert normalize_notion_id(url) == _EXPECTED


@pytest.mark.parametrize("raw", ["", "khong-phai-id", "https://app.notion.com/p/ws/abc"])
def test_id_khong_hop_le_thi_bao_loi(raw: str) -> None:
    with pytest.raises(ValueError):
        normalize_notion_id(raw)


def test_ten_file_local_gom_tieu_de_id_va_ten_goc() -> None:
    item = NotionFile(
        page_id="25d2c7d6-a903-802d-a4a8-cba604f09689",
        page_title="Nguyễn Văn A / PM",  # dấu "/" không hợp lệ trong tên file
        source="CV",
        file_name="cv final.pdf",
        url="https://example.com/cv.pdf",
        is_external=False,
    )
    assert item.local_name == "Nguyễn Văn A _ PM__25d2c7d6__cv final.pdf"


def test_url_peek_lay_id_trang_o_query_p_khong_lay_bang_nen() -> None:
    """URL peek: path là bảng nền, `p=` mới là trang đang mở."""
    url = (
        "https://app.notion.com/p/nexlabtechnology/25d2c7d6a903802da4a8cba604f09689"
        "?v=25d2c7d6a9038078a8cf000c3d78bc6b&p=3b22c7d6a9038085b4b3c92004ca13f4&pm=s"
    )
    assert normalize_notion_id(url) == "3b22c7d6-a903-8085-b4b3-c92004ca13f4"
