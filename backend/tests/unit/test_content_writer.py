"""Notion giới hạn 2000 ký tự mỗi text object — nội dung dài phải cắt mảnh."""

from __future__ import annotations

from app.infrastructure.notion.content_writer import MAX_CONTENT_CHARS, to_rich_text


def test_ngan_thi_mot_manh() -> None:
    items = to_rich_text("nội dung ngắn")

    assert len(items) == 1
    assert items[0]["text"]["content"] == "nội dung ngắn"


def test_dai_thi_cat_thanh_nhieu_manh_2000() -> None:
    items = to_rich_text("a" * 5000)

    assert len(items) == 3
    assert [len(i["text"]["content"]) for i in items] == [2000, 2000, 1000]


def test_ghep_lai_khong_mat_ky_tu() -> None:
    content = "".join(str(i % 10) for i in range(4321))

    assert "".join(i["text"]["content"] for i in to_rich_text(content)) == content


def test_vuot_tran_thi_cat_bot_duoi() -> None:
    items = to_rich_text("a" * (MAX_CONTENT_CHARS + 5000))

    assert len(items) == 100
    assert sum(len(i["text"]["content"]) for i in items) == MAX_CONTENT_CHARS
