"""Adapter: tìm đơn ứng tuyển chưa được quét, bằng cách đối chiếu hai bảng Notion.

Không dùng mốc thời gian ("đã xử lý tới lúc X") vì mốc lệch trong ba tình huống:
Tally tạo dòng trước rồi mới upload CV, một CV lỗi giữa chừng, hoặc ứng viên sửa
CV sau khi nộp. Phép trừ tập hợp không có mốc nào để lệch.

Khoá đối chiếu là `page_id` của dòng nguồn — email không dùng được vì trong 3849
đơn thật chỉ có 3192 email khác nhau, và ngay cả cặp (email, job) vẫn còn trùng.
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
SOURCE_ID_COLUMN = "Source ID"


class NotionApplicationSource(ApplicationSource):
    def __init__(
        self,
        api_key: str,
        source_data_source_id: str,
        target_data_source_id: str,
    ) -> None:
        if not source_data_source_id:
            raise ValueError("Thiếu NOTION_SOURCE_DATA_SOURCE_ID")
        self._client = Client(auth=api_key)
        self._source_id = source_data_source_id
        self._target_id = target_data_source_id

    async def list_pending(self, limit: int | None = None) -> list[PendingApplication]:
        done = await self._processed_source_ids()
        pending: list[PendingApplication] = []

        for page in await self._query_all(self._source_id):
            if page["id"] in done:
                continue
            application = _to_pending(page)
            if application is None:  # chưa đính CV -> để lượt sau
                continue
            pending.append(application)
            if limit is not None and len(pending) >= limit:
                break

        logger.info("Còn %d đơn chưa quét (đã quét: %d)", len(pending), len(done))
        return pending

    async def count_pending(self) -> int:
        return len(await self.list_pending())

    async def _processed_source_ids(self) -> set[str]:
        """Tập `Source ID` đã có ở bảng đích."""
        if not self._target_id:
            return set()

        done: set[str] = set()
        for page in await self._query_all(self._target_id):
            value = _rich_text(page, SOURCE_ID_COLUMN)
            if value:
                done.add(value)
        return done

    async def _query_all(self, data_source_id: str) -> list[dict[str, Any]]:
        """Lấy hết dòng của một bảng (tự phân trang). Chạy trong thread vì SDK sync."""
        pages: list[dict[str, Any]] = []
        cursor: str | None = None

        while True:
            try:
                response: Any = await asyncio.to_thread(
                    self._client.data_sources.query,
                    data_source_id=data_source_id,
                    start_cursor=cursor,
                    page_size=100,
                )
            except APIResponseError as exc:
                raise DomainError(f"Không đọc được bảng {data_source_id}: {exc}") from exc

            pages.extend(response["results"])
            if not response.get("has_more"):
                return pages
            cursor = response["next_cursor"]


def _to_pending(page: dict[str, Any]) -> PendingApplication | None:
    """None nghĩa là dòng chưa có CV — chưa xử lý được, không phải lỗi."""
    file_url = _first_file_url(page)
    if not file_url:
        return None

    return PendingApplication(
        source_page_id=page["id"],
        candidate_name=_title(page) or "(chưa rõ tên)",
        file_url=file_url,
        job_url=_rich_text(page, "Job URL") or None,
        email=(page["properties"].get("Email") or {}).get("email"),
        phone=(page["properties"].get("Phone") or {}).get("phone_number"),
        created_time=page.get("created_time"),
    )


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
