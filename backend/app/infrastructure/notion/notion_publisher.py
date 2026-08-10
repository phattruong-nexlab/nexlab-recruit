"""Adapter: ghi ứng viên đã trích xuất thành một dòng mới trong bảng Notion đích."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from notion_client import Client
from notion_client.errors import APIResponseError

from app.application.ports.candidate_publisher import CandidatePublisher
from app.domain.entities.candidate import Candidate
from app.domain.exceptions import CandidatePublishError
from app.infrastructure.notion.property_mapping import build_properties

logger = logging.getLogger(__name__)


class NotionCandidatePublisher(CandidatePublisher):
    """Schema bảng đích được đọc một lần rồi cache — mapping dựng theo đúng kiểu cột."""

    def __init__(self, api_key: str, data_source_id: str) -> None:
        if not api_key:
            raise ValueError("Thiếu NOTION_API_KEY")
        if not data_source_id:
            raise ValueError("Thiếu NOTION_TARGET_DATA_SOURCE_ID")

        self._client = Client(auth=api_key)
        self._data_source_id = data_source_id
        self._schema: dict[str, str] | None = None
        self._lock = asyncio.Lock()

    async def publish(self, candidate: Candidate) -> str:
        schema = await self._get_schema()
        properties, skipped = build_properties(candidate, schema)

        if skipped:
            logger.warning("Bỏ qua %d cột không khớp bảng đích: %s", len(skipped), skipped)
        if not properties:
            raise CandidatePublishError(
                "Không dựng được property nào khớp bảng đích — kiểm tra FIELD_TO_COLUMN."
            )

        try:
            page: Any = await asyncio.to_thread(
                self._client.pages.create,
                parent={"type": "data_source_id", "data_source_id": self._data_source_id},
                properties=properties,
            )
        except APIResponseError as exc:
            raise CandidatePublishError(f"Notion từ chối ghi: {exc}") from exc

        page_id: str = page["id"]
        logger.info("Đã tạo dòng Notion %s cho %s", page_id, candidate.full_name)
        return page_id

    async def _get_schema(self) -> dict[str, str]:
        """map tên cột -> kiểu. Đọc một lần, dùng lại cho các lần ghi sau."""
        if self._schema is not None:
            return self._schema

        async with self._lock:
            if self._schema is not None:  # request khác đã nạp xong trong lúc chờ
                return self._schema
            try:
                data_source: Any = await asyncio.to_thread(
                    self._client.data_sources.retrieve,
                    data_source_id=self._data_source_id,
                )
            except APIResponseError as exc:
                raise CandidatePublishError(
                    f"Không đọc được schema bảng đích {self._data_source_id}: {exc}. "
                    "Nhớ share bảng đó cho integration."
                ) from exc

            self._schema = {name: prop["type"] for name, prop in data_source["properties"].items()}
            logger.info("Đã nạp schema bảng đích: %d cột", len(self._schema))
            return self._schema
