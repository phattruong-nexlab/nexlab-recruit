"""Ánh xạ field domain → property Notion. Thuần code, KHÔNG dùng LLM.

Quyết định "field nào vào cột nào" nằm ở `FIELD_TO_COLUMN` — chốt một lần lúc
thiết kế. Lúc chạy chỉ điền vào chỗ đã định sẵn, cùng đầu vào luôn ra cùng payload.

Dạng payload phụ thuộc KIỂU của cột (title/rich_text/select/number/...), nên
`build_properties` đọc schema thật của bảng đích rồi dựng đúng dạng — đổi kiểu cột
trên Notion không phải sửa code.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.domain.entities.candidate import Candidate

logger = logging.getLogger(__name__)

# Notion từ chối rich_text dài quá 2000 ký tự trong một text object.
_MAX_RICH_TEXT = 2000


def _value_of(candidate: Candidate) -> dict[str, Any]:
    """Giá trị thô của từng field, trước khi bọc theo kiểu property."""
    return {
        "full_name": candidate.full_name,
        "applied_job": candidate.applied_job,
        "university": candidate.university,
        "gpa": candidate.gpa,
        "experience": candidate.experiences_as_text() or None,
        "skills": candidate.skills.as_list(),
        "certificates": candidate.certificates,
        "languages": candidate.languages,
        "email": candidate.email,
        "phone": candidate.phone,
        "job_url": candidate.job_url,
        "applied_at": candidate.applied_at,
        "cv_url": candidate.source_file_url,
        "years_of_experience": candidate.total_experience_years,
        "source_id": candidate.source_page_id,
        "scan_status": "Đã quét",
        "scanned_at": datetime.now(UTC).isoformat(),
    }


# field domain -> TÊN CỘT trên bảng Notion đích ("Candidate CV Scan Results").
# Sửa vế phải cho khớp bảng thật; cột nào không tồn tại sẽ bị bỏ qua kèm cảnh báo.
FIELD_TO_COLUMN: dict[str, str] = {
    "full_name": "Candidate Name",
    "applied_job": "Applied Job",
    "university": "University",
    "gpa": "GPA",
    "experience": "Experience",
    "skills": "Skill",
    "certificates": "Certificate",
    "languages": "Language",
    "email": "Email",
    "phone": "Phone",
    "cv_url": "Resume, CL",
    "source_id": "Source ID",
    "scan_status": "Scan status",
    "scanned_at": "Scanned at",
    # Bảng đích không có cột cho các field dưới đây; giữ lại để nếu sau này thêm
    # cột thì chỉ cần đặt đúng tên là chạy, không phải sửa code.
    "job_url": "Job URL",
    "years_of_experience": "YOE",
}

# Notion tự sinh, KHÔNG ghi được. Ghi vào là 400 Bad Request.
READ_ONLY_TYPES = frozenset(
    {
        "created_time",
        "created_by",
        "last_edited_time",
        "last_edited_by",
        "formula",
        "rollup",
        "unique_id",
    }
)


def build_properties(
    candidate: Candidate, schema: dict[str, str]
) -> tuple[dict[str, Any], list[str]]:
    """Dựng payload `properties` cho pages.create.

    Args:
        schema: map tên cột -> kiểu property, đọc từ data_sources.retrieve.

    Returns:
        (properties, các cột đã bỏ qua vì không có trong bảng đích hoặc kiểu lạ)
    """
    values = _value_of(candidate)
    properties: dict[str, Any] = {}
    skipped: list[str] = []

    for field_name, column in FIELD_TO_COLUMN.items():
        value = values.get(field_name)
        if value is None or value == [] or value == "":
            continue

        column_type = schema.get(column)
        if column_type is None:
            skipped.append(f"{column} (không có trong bảng đích)")
            continue

        if column_type in READ_ONLY_TYPES:
            skipped.append(f"{column} (kiểu {column_type} do Notion tự sinh, không ghi được)")
            continue

        builder = _BUILDERS.get(column_type)
        if builder is None:
            skipped.append(f"{column} (kiểu {column_type} chưa hỗ trợ)")
            continue

        payload = builder(value)
        if payload is not None:
            properties[column] = payload

    return properties, skipped


# --- Dựng payload theo từng kiểu property của Notion ------------------------
def _text_objects(value: Any) -> list[dict[str, Any]]:
    text = _as_text(value)[:_MAX_RICH_TEXT]
    return [{"text": {"content": text}}]


def _as_text(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def _multi_select(value: Any) -> list[dict[str, str]] | None:
    items = value if isinstance(value, list) else [value]
    # Notion cấm dấu phẩy trong tên option của multi_select.
    names = [str(item).replace(",", " ").strip()[:100] for item in items]
    options = [{"name": name} for name in names if name]
    return options or None


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _date(value: Any) -> dict[str, str] | None:
    text = str(value).strip()
    return {"start": text} if text else None


def _files(value: Any) -> list[dict[str, Any]] | None:
    """Đính link file dạng `external` — Notion không cho upload qua API kiểu này.

    Link file của Notion hết hạn sau ~1 giờ nên chỉ có tác dụng truy vết nguồn,
    không dùng để tải lại về sau.
    """
    url = _as_text(value).strip()
    if not url:
        return None
    return [{"type": "external", "name": "CV", "external": {"url": url}}]


_BUILDERS: dict[str, Callable[[Any], Any]] = {
    "title": lambda v: {"title": _text_objects(v)},
    "rich_text": lambda v: {"rich_text": _text_objects(v)},
    "select": lambda v: {"select": {"name": _as_text(v)[:100]}},
    "multi_select": lambda v: {"multi_select": options} if (options := _multi_select(v)) else None,
    "number": lambda v: {"number": number} if (number := _number(v)) is not None else None,
    "email": lambda v: {"email": _as_text(v)},
    "phone_number": lambda v: {"phone_number": _as_text(v)},
    "url": lambda v: {"url": _as_text(v)},
    "date": lambda v: {"date": date} if (date := _date(v)) else None,
    "files": lambda v: {"files": files} if (files := _files(v)) else None,
}
