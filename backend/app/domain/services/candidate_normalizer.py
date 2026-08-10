"""Domain service: chuẩn hoá dữ liệu ứng viên sau khi LLM trích xuất.

Thuần nghiệp vụ, không I/O.
"""

from __future__ import annotations

from app.domain.entities.candidate import Candidate

_MAX_DESCRIPTION_CHARS = 1500
_MIN_GPA = 0.0
_MAX_GPA = 10.0


def normalize(candidate: Candidate) -> Candidate:
    """Trim chuỗi, bỏ experience không có tên công ty, loại GPA vô lý."""
    candidate.full_name = _clean(candidate.full_name)
    candidate.university = _clean(candidate.university)
    candidate.applied_job = _clean(candidate.applied_job)

    if candidate.gpa is not None and not _MIN_GPA <= candidate.gpa <= _MAX_GPA:
        candidate.gpa = None

    candidate.certificates = _clean_list(candidate.certificates)
    candidate.languages = _clean_list(candidate.languages)

    candidate.experiences = [exp for exp in candidate.experiences if (exp.company or "").strip()]
    for exp in candidate.experiences:
        exp.company = exp.company.strip()
        exp.position = (exp.position or "").strip()
        exp.description = (exp.description or "").strip()[:_MAX_DESCRIPTION_CHARS]

    candidate.reindex_experiences()
    return candidate


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _clean_list(values: list[str]) -> list[str]:
    """Trim, bỏ rỗng, bỏ trùng (không phân biệt hoa thường), giữ thứ tự."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = (value or "").strip()
        if not item or item.casefold() in seen:
            continue
        seen.add(item.casefold())
        result.append(item)
    return result
