from __future__ import annotations

from app.domain.value_objects.skill_set import SkillSet


def test_bo_trung_khong_phan_biet_hoa_thuong_va_giu_thu_tu() -> None:
    skills = SkillSet.from_raw(["Python", " python ", "SQL", "", None])  # type: ignore[list-item]
    assert skills.as_list() == ["Python", "SQL"]


def test_raw_none_tra_ve_rong() -> None:
    assert len(SkillSet.from_raw(None)) == 0
