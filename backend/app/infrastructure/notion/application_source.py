"""Adapter: tìm đơn ứng tuyển cần trích nội dung CV.

Không dùng mốc thời gian ("đã xử lý tới lúc X") vì mốc lệch trong ba tình huống:
Tally tạo dòng trước rồi mới upload CV, một CV lỗi giữa chừng, hoặc ứng viên sửa
CV sau khi nộp.

Điều kiện đơn giản hơn hẳn phiên bản trước: **có CV và cột `Resume Content` còn
rỗng**. Chính cột đích là dấu hiệu đã xử lý — không cần cột khoá riêng, không cần
đọc bảng thứ hai.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from notion_client import Client
from notion_client.errors import APIResponseError

from app.application.ports.application_source import ApplicationSource, PendingApplication
from app.domain.exceptions import DomainError

logger = logging.getLogger(__name__)

CV_PROPERTY = "Resume, CL"
CONTENT_PROPERTY = "Resume Content"


class NotionApplicationSource(ApplicationSource):
    def __init__(self, api_key: str, data_source_id: str) -> None:
        if not data_source_id:
            raise ValueError("Thiếu NOTION_SOURCE_DATA_SOURCE_ID")
        self._client = Client(auth=api_key)
        self._data_source_id = data_source_id

    async def list_pending(self, limit: int | None = None) -> list[PendingApplication]:
        pending: list[PendingApplication] = []

        for page in await self._query_pending():
            file_url = _first_file_url(page)
            if not file_url:  # chưa đính CV -> bỏ qua, lượt sau CV về thì làm
                continue

            pending.append(
                PendingApplication(
                    source_page_id=page["id"],
                    candidate_name=_title(page) or "(chưa rõ tên)",
                    file_url=file_url,
                    properties=page.get("properties", {}),
                    created_time=page.get("created_time"),
                )
            )
            if limit is not None and len(pending) >= limit:
                break

        logger.info("Còn %d CV chưa trích nội dung", len(pending))
        return pending

    async def count_pending(self) -> int:
        return len(await self.list_pending())

    async def _query_pending(self) -> list[dict[str, Any]]:
        """Lọc ngay trên Notion để không phải tải về rồi mới loại.

        Notion không lọc được "cột files không rỗng", nên chỉ lọc theo
        `Resume Content` và kiểm tra CV ở phía client.
        """
        pages: list[dict[str, Any]] = []
        cursor: str | None = None
        query_filter = {"property": CONTENT_PROPERTY, "rich_text": {"is_empty": True}}

        while True:
            try:
                response: Any = await asyncio.to_thread(
                    self._client.data_sources.query,
                    data_source_id=self._data_source_id,
                    filter=query_filter,
                    start_cursor=cursor,
                    page_size=100,
                )
            except APIResponseError as exc:
                raise DomainError(f"Không đọc được bảng {self._data_source_id}: {exc}") from exc

            pages.extend(response["results"])
            if not response.get("has_more"):
                return pages
            cursor = response["next_cursor"]


def _first_file_url(page: dict[str, Any]) -> str | None:
    """CV có thể là file Notion lưu, hoặc link external (Tally) — nhận cả hai."""
    prop = page["properties"].get(CV_PROPERTY) or {}
    for item in prop.get("files") or []:
        source = item.get("external") if item.get("type") == "external" else item.get("file")
        url = (source or {}).get("url")
        if url:
            return str(url)
    return None


def _title(page: dict[str, Any]) -> str:
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            return "".join(part.get("plain_text", "") for part in prop.get("title", []))
    return ""
