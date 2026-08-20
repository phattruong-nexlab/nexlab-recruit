"""Adapter: tìm đơn ứng tuyển cần trích nội dung CV.

Không dùng mốc thời gian để nhớ "đã xử lý tới đâu" — dấu hiệu đã xử lý là **cột
đích còn rỗng hay không**. Nhờ vậy chạy lại không làm lại việc đã xong, CV lỗi tự
được nhặt ở lượt sau, và CV mà Tally upload muộn cũng không bị sót.

`PendingFilter` chỉ để THU HẸP phạm vi một lượt chạy (HR muốn làm riêng một job,
hoặc chỉ từ một ngày trở đi), không phải cơ chế chống trùng.
"""

from __future__ import annotations

import asyncio
import logging
from collections import Counter
from typing import Any

from notion_client import Client
from notion_client.errors import APIResponseError

from app.application.ports.application_source import (
    ApplicationSource,
    PendingApplication,
    PendingFilter,
)
from app.domain.exceptions import DomainError

logger = logging.getLogger(__name__)

CV_PROPERTY = "Resume, CL"
CONTENT_PROPERTY = "Resume Content"
CREATED_PROPERTY = "Created time"
JOB_URL_PROPERTY = "Job URL"


class NotionApplicationSource(ApplicationSource):
    def __init__(self, api_key: str, data_source_id: str) -> None:
        if not data_source_id:
            raise ValueError("Thiếu NOTION_SOURCE_DATA_SOURCE_ID")
        self._client = Client(auth=api_key)
        self._data_source_id = data_source_id

    async def list_pending(
        self, limit: int | None = None, pending_filter: PendingFilter | None = None
    ) -> list[PendingApplication]:
        criteria = pending_filter or PendingFilter()
        pending: list[PendingApplication] = []

        for page in await self._query(criteria):
            file_url = _first_file_url(page)
            if not file_url:  # chưa đính CV -> bỏ qua, lượt sau CV về thì làm
                continue

            pending.append(
                PendingApplication(
                    source_page_id=page["id"],
                    candidate_name=_title(page) or "(chưa rõ tên)",
                    file_url=file_url,
                    job_url=_rich_text(page, JOB_URL_PROPERTY),
                    properties=page.get("properties", {}),
                    created_time=page.get("created_time"),
                )
            )
            if limit is not None and len(pending) >= limit:
                break

        logger.info("Còn %d CV chưa trích nội dung (%s)", len(pending), criteria.describe())
        return pending

    async def count_pending(self, pending_filter: PendingFilter | None = None) -> int:
        return len(await self.list_pending(pending_filter=pending_filter))

    async def job_breakdown(
        self, pending_filter: PendingFilter | None = None
    ) -> list[tuple[str, int]]:
        """Các job đang có đơn chờ, kèm số lượng — để HR chọn trên giao diện.

        Lấy từ chính danh sách đang chờ nên không tốn thêm lời gọi Notion nào.
        """
        pending = await self.list_pending(pending_filter=pending_filter)
        counter = Counter(item.job_url for item in pending if item.job_url)
        return counter.most_common()

    def _build_filter(self, criteria: PendingFilter) -> dict[str, Any]:
        conditions: list[dict[str, Any]] = [
            {"property": CONTENT_PROPERTY, "rich_text": {"is_empty": True}}
        ]
        if (since := criteria.since_for_notion) is not None:
            conditions.append(
                {"property": CREATED_PROPERTY, "created_time": {"on_or_after": since}}
            )
        if criteria.job_url_contains:
            conditions.append(
                {"property": JOB_URL_PROPERTY, "rich_text": {"contains": criteria.job_url_contains}}
            )
        return conditions[0] if len(conditions) == 1 else {"and": conditions}

    async def _query(self, criteria: PendingFilter) -> list[dict[str, Any]]:
        """Lọc ngay trên Notion để không phải tải cả bảng về rồi mới loại."""
        pages: list[dict[str, Any]] = []
        cursor: str | None = None
        query_filter = self._build_filter(criteria)

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


def _rich_text(page: dict[str, Any], name: str) -> str:
    prop = page.get("properties", {}).get(name) or {}
    return "".join(part.get("plain_text", "") for part in prop.get("rich_text", []))
