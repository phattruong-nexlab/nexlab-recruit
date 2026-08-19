"""Notion đếm độ dài theo UTF-16, không theo ký tự Unicode."""

from __future__ import annotations

from app.infrastructure.notion.content_writer import (
    MAX_CONTENT_CHARS,
    to_rich_text,
    utf16_len,
)

_LIMIT = 2000


def _widths(items: list[dict[str, str]]) -> list[int]:
    return [utf16_len(i["text"]["content"]) for i in items]


def test_ngan_thi_mot_manh() -> None:
    items = to_rich_text("nội dung ngắn")

    assert len(items) == 1
    assert items[0]["text"]["content"] == "nội dung ngắn"


def test_dai_thi_cat_thanh_nhieu_manh() -> None:
    items = to_rich_text("a" * 5000)

    assert _widths(items) == [2000, 2000, 1000]


def test_ghep_lai_khong_mat_ky_tu() -> None:
    content = "".join(str(i % 10) for i in range(4321))

    assert "".join(i["text"]["content"] for i in to_rich_text(content)) == content


def test_emoji_tinh_hai_don_vi_utf16() -> None:
    """Cắt theo len() của Python sẽ ra 2010 và Notion từ chối."""
    content = "a" * 1990 + "🙂" * 10  # 2000 ký tự Python, 2010 đơn vị UTF-16

    items = to_rich_text(content)

    assert all(w <= _LIMIT for w in _widths(items))
    assert "".join(i["text"]["content"] for i in items) == content


def test_khong_cat_giua_mot_emoji() -> None:
    content = "a" * 1999 + "🙂🙂"

    items = to_rich_text(content)

    for item in items:
        assert "\ud83d" not in item["text"]["content"]  # nửa surrogate pair
    assert "".join(i["text"]["content"] for i in items) == content


def test_vuot_tran_thi_cat_bot_duoi() -> None:
    items = to_rich_text("a" * (MAX_CONTENT_CHARS + 5000))

    assert len(items) == 100
    assert sum(_widths(items)) == MAX_CONTENT_CHARS
