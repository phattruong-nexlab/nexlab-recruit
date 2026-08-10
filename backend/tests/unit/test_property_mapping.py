"""Mapping sang Notion phải deterministic và tự khớp theo kiểu cột."""

from __future__ import annotations

from app.domain.entities.candidate import Candidate
from app.domain.entities.experience import Experience
from app.domain.value_objects.employment_period import EmploymentPeriod
from app.domain.value_objects.skill_set import SkillSet
from app.infrastructure.notion.property_mapping import build_properties

_CANDIDATE = Candidate(
    full_name="Trần Khánh Hoà",
    applied_job="Senior Data Engineer",
    university="Đại học Bách Khoa",
    gpa=3.6,
    skills=SkillSet.from_raw(["Python", "SQL"]),
    certificates=["AWS Certified"],
    languages=["Tiếng Việt"],
    email="a@example.com",
    phone="+84900000000",
    experiences=[
        Experience(
            company="Nexlab",
            position="Data Engineer",
            period=EmploymentPeriod(start_year=2020, end_year=2024),
        )
    ],
)


def test_dung_payload_theo_dung_kieu_cot() -> None:
    schema = {
        "Candidate Name": "title",
        "University": "rich_text",
        "GPA": "number",
        "Skill": "multi_select",
        "Email": "email",
        "Phone": "phone_number",
    }

    properties, skipped = build_properties(_CANDIDATE, schema)

    assert properties["Candidate Name"]["title"][0]["text"]["content"] == "Trần Khánh Hoà"
    assert properties["University"]["rich_text"][0]["text"]["content"] == "Đại học Bách Khoa"
    assert properties["GPA"] == {"number": 3.6}
    assert properties["Skill"] == {"multi_select": [{"name": "Python"}, {"name": "SQL"}]}
    assert properties["Email"] == {"email": "a@example.com"}
    assert properties["Phone"] == {"phone_number": "+84900000000"}
    assert "Applied Job" in " ".join(skipped)  # không có trong schema -> báo, không im lặng


def test_cung_cot_doi_kieu_thi_payload_doi_theo() -> None:
    """Đổi Skill từ multi_select sang rich_text trên Notion không phải sửa code."""
    properties, _ = build_properties(_CANDIDATE, {"Skill": "rich_text"})

    assert properties["Skill"]["rich_text"][0]["text"]["content"] == "Python, SQL"


def test_bo_qua_gia_tri_rong_thay_vi_ghi_null() -> None:
    empty = Candidate(full_name="A")
    properties, _ = build_properties(empty, {"Candidate Name": "title", "GPA": "number"})

    assert "GPA" not in properties


def test_cat_rich_text_qua_dai_theo_gioi_han_notion() -> None:
    long_desc = Candidate(
        experiences=[Experience(company="X", description="y" * 5000)],
    )
    properties, _ = build_properties(long_desc, {"Experience": "rich_text"})

    assert len(properties["Experience"]["rich_text"][0]["text"]["content"]) == 2000


def test_bo_dau_phay_trong_ten_option_multi_select() -> None:
    """Notion cấm dấu phẩy trong tên option."""
    candidate = Candidate(certificates=["TOEIC 900, Reading"])
    properties, _ = build_properties(candidate, {"Certificate": "multi_select"})

    assert properties["Certificate"]["multi_select"] == [{"name": "TOEIC 900  Reading"}]


def test_bo_qua_cot_notion_tu_sinh() -> None:
    """created_time/formula/rollup ghi vào là Notion trả 400 — phải chặn từ trước."""
    properties, skipped = build_properties(
        _CANDIDATE, {"Candidate Name": "title", "GPA": "formula"}
    )

    assert "GPA" not in properties
    assert any("GPA" in item and "formula" in item for item in skipped)
    assert "Candidate Name" in properties  # cột ghi được vẫn ghi bình thường


def test_ghi_link_cv_vao_cot_files() -> None:
    candidate = Candidate(source_file_url="https://file.notion.so/cv.pdf")

    properties, _ = build_properties(candidate, {"Resume, CL": "files"})

    assert properties["Resume, CL"]["files"] == [
        {"type": "external", "name": "CV", "external": {"url": "https://file.notion.so/cv.pdf"}}
    ]
