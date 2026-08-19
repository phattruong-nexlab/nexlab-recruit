"""Chép property phải deterministic và không làm hỏng dòng khi schema lệch."""

from __future__ import annotations

from typing import Any

from app.infrastructure.notion.property_copier import copy_properties

_SCHEMA = {
    "Candidate Name": "title",
    "Notes": "rich_text",
    "GPA": "number",
    "Passed": "checkbox",
    "University": "select",
    "Skils?": "multi_select",
    "Email": "email",
    "DoB": "date",
    "Bài test": "files",
    "Created time": "created_time",
}


def _source() -> dict[str, Any]:
    return {
        "Candidate Name": {"type": "title", "title": [{"plain_text": "Trần Khánh Hoà"}]},
        "Notes": {"type": "rich_text", "rich_text": [{"plain_text": "ghi chú", "href": None}]},
        "GPA": {"type": "number", "number": 3.6},
        "Passed": {"type": "checkbox", "checkbox": True},
        "University": {"type": "select", "select": {"name": "HCMUT", "color": "blue"}},
        "Skils?": {"type": "multi_select", "multi_select": [{"name": "Back-end"}]},
        "Email": {"type": "email", "email": "a@example.com"},
        "DoB": {"type": "date", "date": {"start": "1992-02-05", "end": None}},
        "Bài test": {
            "type": "files",
            "files": [
                {"type": "external", "name": "t.pdf", "external": {"url": "https://x/t.pdf"}}
            ],
        },
        "Created time": {"type": "created_time", "created_time": "2026-08-10T00:00:00.000Z"},
    }


def test_chep_dung_dang_cho_tung_kieu() -> None:
    payload, skipped = copy_properties(_source(), _SCHEMA)

    assert payload["Candidate Name"]["title"][0]["text"]["content"] == "Trần Khánh Hoà"
    assert payload["GPA"] == {"number": 3.6}
    assert payload["Passed"] == {"checkbox": True}
    assert payload["University"] == {"select": {"name": "HCMUT"}}
    assert payload["Skils?"] == {"multi_select": [{"name": "Back-end"}]}
    assert payload["Email"] == {"email": "a@example.com"}
    assert payload["DoB"] == {"date": {"start": "1992-02-05"}}
    assert payload["Bài test"]["files"][0]["external"]["url"] == "https://x/t.pdf"
    assert skipped == []


def test_bo_qua_cot_notion_tu_sinh() -> None:
    payload, _ = copy_properties(_source(), _SCHEMA)

    assert "Created time" not in payload


def test_cot_rong_khong_ghi_null() -> None:
    source = {
        "Notes": {"type": "rich_text", "rich_text": []},
        "GPA": {"type": "number", "number": None},
    }

    payload, _ = copy_properties(source, _SCHEMA)

    assert payload == {}


def test_cot_thieu_hoac_lech_kieu_bi_bao_chu_khong_im_lang() -> None:
    source = {
        "Cột lạ": {"type": "rich_text", "rich_text": [{"plain_text": "x"}]},
        "GPA": {"type": "rich_text", "rich_text": [{"plain_text": "3.6"}]},
    }

    payload, skipped = copy_properties(source, _SCHEMA)

    assert payload == {}
    assert any("lạ" in item and "không có" in item for item in skipped)
    assert any("GPA" in item for item in skipped)


def test_giu_link_trong_rich_text() -> None:
    source = {
        "Notes": {
            "type": "rich_text",
            "rich_text": [{"plain_text": "trang chủ", "href": "https://nexlab.tech"}],
        }
    }

    payload, _ = copy_properties(source, _SCHEMA)

    assert payload["Notes"]["rich_text"][0]["text"]["link"] == {"url": "https://nexlab.tech"}
