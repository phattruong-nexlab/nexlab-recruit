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

# Giới hạn của Notion: mỗi text object 2000 ký tự, mỗi property tối đa 100 object.
_CHUNK = 2000
_MAX_CHUNKS = 100
MAX_CONTENT_CHARS = _CHUNK * _MAX_CHUNKS


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
    """Cắt thành các mảnh 2000 ký tự. Quá dài thì cắt bớt phần đuôi."""
    text = content
    if len(text) > MAX_CONTENT_CHARS:
        logger.warning("Nội dung %d ký tự, cắt còn %d", len(text), MAX_CONTENT_CHARS)
        text = text[:MAX_CONTENT_CHARS]

    return [
        {"type": "text", "text": {"content": text[i : i + _CHUNK]}}
        for i in range(0, len(text), _CHUNK)
    ]
