"""Sao chép GIÁ TRỊ property từ dòng Notion này sang dòng Notion khác.

Notion trả property ở dạng đọc (kèm `id`, `plain_text`, `href`...) nhưng chỉ nhận
một tập con hẹp hơn khi ghi. Module này dịch giữa hai dạng đó — thuần code, không
suy đoán gì, cùng đầu vào luôn ra cùng payload.

Điều kiện: hai bảng có cột trùng tên và trùng kiểu. Cột nào lệch sẽ bị bỏ qua kèm
cảnh báo, không làm hỏng cả dòng.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Notion tự sinh, ghi vào là 400.
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

# Chép nguyên giá trị, không cần bọc thêm.
_SCALAR_TYPES = frozenset({"number", "checkbox", "email", "phone_number", "url"})


def copy_properties(
    source: dict[str, Any], target_schema: dict[str, str]
) -> tuple[dict[str, Any], list[str]]:
    """Dựng payload `properties` cho pages.create từ property của dòng nguồn.

    Args:
        source: `page["properties"]` của dòng nguồn (dạng đọc).
        target_schema: map tên cột -> kiểu của bảng đích.

    Returns:
        (properties, danh sách cột bị bỏ qua kèm lý do)
    """
    payload: dict[str, Any] = {}
    skipped: list[str] = []

    for name, prop in source.items():
        kind = prop.get("type")

        target_kind = target_schema.get(name)
        if target_kind is None:
            skipped.append(f"{name} (không có ở bảng đích)")
            continue
        if target_kind != kind:
            skipped.append(f"{name} (nguồn {kind} ≠ đích {target_kind})")
            continue
        if kind in READ_ONLY_TYPES:
            continue  # Notion tự sinh, bỏ qua im lặng — không phải lỗi

        value = _convert(prop, kind)
        if value is not None:
            payload[name] = value

    return payload, skipped


def _convert(prop: dict[str, Any], kind: str) -> dict[str, Any] | None:
    """None nghĩa là cột rỗng — bỏ hẳn khỏi payload thay vì ghi null."""
    raw = prop.get(kind)

    if kind in ("title", "rich_text"):
        items = [_text_item(part) for part in (raw or [])]
        return {kind: items} if items else None

    if kind in _SCALAR_TYPES:
        return {kind: raw} if raw is not None else None

    if kind in ("select", "status"):
        return {kind: {"name": raw["name"]}} if raw else None

    if kind == "multi_select":
        options = [{"name": option["name"]} for option in (raw or [])]
        return {kind: options} if options else None

    if kind == "date":
        if not raw or not raw.get("start"):
            return None
        date: dict[str, Any] = {"start": raw["start"]}
        if raw.get("end"):
            date["end"] = raw["end"]
        return {kind: date}

    if kind == "people":
        people = [{"object": "user", "id": person["id"]} for person in (raw or [])]
        return {kind: people} if people else None

    if kind == "relation":
        relations = [{"id": item["id"]} for item in (raw or [])]
        return {kind: relations} if relations else None

    if kind == "files":
        files = [item for item in (_file_item(f) for f in (raw or [])) if item]
        return {kind: files} if files else None

    logger.debug("Chưa hỗ trợ kiểu property %r, bỏ qua", kind)
    return None


def _text_item(part: dict[str, Any]) -> dict[str, Any]:
    """Giữ link nếu có; bỏ annotation vì không ảnh hưởng nội dung."""
    content = part.get("plain_text", "")
    text: dict[str, Any] = {"content": content[:2000]}
    if part.get("href"):
        text["link"] = {"url": part["href"]}
    return {"type": "text", "text": text}


def _file_item(item: dict[str, Any]) -> dict[str, Any] | None:
    """File do Notion lưu KHÔNG chép thẳng được — URL của nó hết hạn sau ~1 giờ.

    Chỉ chép được link `external`; muốn có bản Notion lưu thì phải tải rồi upload
    lại (xem `NotionRowMirror`).
    """
    name = item.get("name") or "file"
    if item.get("type") == "external":
        url = (item.get("external") or {}).get("url")
        return {"type": "external", "name": name, "external": {"url": url}} if url else None

    url = (item.get("file") or {}).get("url")
    if not url:
        return None
    return {"type": "external", "name": name, "external": {"url": url}}


def file_upload_value(upload_id: str, name: str) -> dict[str, Any]:
    """Payload đính file vừa upload vào một cột `files`."""
    return {"files": [{"type": "file_upload", "name": name, "file_upload": {"id": upload_id}}]}


def rich_text_value(text: str) -> dict[str, Any]:
    return {"rich_text": [{"type": "text", "text": {"content": text[:2000]}}]}
