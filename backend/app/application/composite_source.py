"""Gộp nhiều bảng nguồn thành một, để luồng xử lý không phải biết có mấy bảng.

Mỗi bảng Notion là một `ApplicationSource` riêng. Composite chạy chúng song song
rồi nối kết quả — use case, trang quản trị và job đều làm việc như thể chỉ có
một nguồn duy nhất.

Notion tạo `page_id` duy nhất trên toàn workspace, nên khi ghi ngược nội dung
không cần biết dòng đó thuộc bảng nào.
"""

from __future__ import annotations

import asyncio
import logging

from app.application.ports.application_source import (
    ApplicationSource,
    PendingApplication,
    PendingFilter,
)

logger = logging.getLogger(__name__)


class CompositeApplicationSource(ApplicationSource):
    def __init__(self, sources: list[ApplicationSource]) -> None:
        if not sources:
            raise ValueError("Cần ít nhất một bảng nguồn")
        self._sources = sources

    async def list_pending(
        self, limit: int | None = None, pending_filter: PendingFilter | None = None
    ) -> list[PendingApplication]:
        # KHÔNG truyền limit xuống từng bảng: mỗi bảng trả tối đa `limit` thì tổng
        # sẽ vượt. Lấy đủ rồi cắt một lần ở đây.
        results = await asyncio.gather(
            *(source.list_pending(pending_filter=pending_filter) for source in self._sources)
        )

        pending: list[PendingApplication] = [item for batch in results for item in batch]
        if len(self._sources) > 1:
            logger.info(
                "Tổng %d CV chờ từ %d bảng: %s",
                len(pending),
                len(self._sources),
                [len(batch) for batch in results],
            )

        return pending[:limit] if limit is not None else pending

    async def count_pending(self, pending_filter: PendingFilter | None = None) -> int:
        return len(await self.list_pending(pending_filter=pending_filter))
