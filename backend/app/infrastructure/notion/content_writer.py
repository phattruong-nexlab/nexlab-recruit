"""Adapter: ghi nội dung CV vào cột `Resume Content` của dòng nguồn.

Notion giới hạn 2000 ký tự cho mỗi text object, nên nội dung dài phải cắt thành
nhiều mảnh trong cùng một property — Notion nối lại khi hiển thị.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from notion_client import Client
from notion_client.errors import APIResponseError

from app.application.ports.content_writer import ResumeContentWriter
from app.domain.exceptions import CandidatePublishError

logger = logging.getLogger(__name__)

CONTENT_COLUMN = "Resume Content"

# Giới hạn của Notion: mỗi text object 2000, mỗi property tối đa 100 object.
#
# QUAN TRỌNG: Notion đếm theo đơn vị UTF-16 (như String.length của JavaScript),
# không phải theo ký tự Unicode. Emoji và ký tự ngoài BMP tính là 2 đơn vị, nên
# cắt bằng len() của Python sẽ vượt hạn mức mà không hiểu vì sao.
_CHUNK = 2000
_MAX_CHUNKS = 100
MAX_CONTENT_CHARS = _CHUNK * _MAX_CHUNKS


def utf16_len(text: str) -> int:
    """Độ dài theo cách Notion đếm."""
    return len(text.encode("utf-16-le")) // 2


class NotionResumeContentWriter(ResumeContentWriter):
    def __init__(self, api_key: str, column: str = CONTENT_COLUMN) -> None:
        self._client = Client(auth=api_key)
        self._column = column

    async def write(self, page_id: str, content: str) -> None:
        if not content.strip():
            raise CandidatePublishError("Nội dung rỗng, không ghi")

        try:
            await asyncio.to_thread(
                self._client.pages.update,
                page_id=page_id,
                properties={self._column: {"rich_text": to_rich_text(content)}},
            )
        except APIResponseError as exc:
            raise CandidatePublishError(f"Notion từ chối ghi {self._column!r}: {exc}") from exc

        logger.info("Đã ghi %d ký tự vào %s của %s", len(content), self._column, page_id)


def to_rich_text(content: str) -> list[dict[str, Any]]:
    """Cắt thành các mảnh vừa hạn mức UTF-16 của Notion, không cắt giữa emoji."""
    chunks: list[str] = []
    current: list[str] = []
    used = 0

    for char in content:
        width = utf16_len(char)
        if used + width > _CHUNK:
            chunks.append("".join(current))
            if len(chunks) >= _MAX_CHUNKS:
                logger.warning("Nội dung quá dài, cắt còn %d mảnh", _MAX_CHUNKS)
                return _wrap(chunks)
            current, used = [], 0
        current.append(char)
        used += width

    if current:
        chunks.append("".join(current))
    return _wrap(chunks)


def _wrap(chunks: list[str]) -> list[dict[str, Any]]:
    return [{"type": "text", "text": {"content": chunk}} for chunk in chunks]
