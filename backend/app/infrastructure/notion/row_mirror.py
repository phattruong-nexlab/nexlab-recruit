"""Adapter: tạo dòng ở bảng gương — chép cột, upload CV vào Notion.

Upload CV theo ba bước của Notion API: `create` xin chỗ, `send` đẩy bytes, rồi
đính `file_upload_id` vào cột `files` khi tạo trang. Nhờ vậy file do Notion lưu
(`type: file`) chứ không còn là link ngoài (`type: external`) — đây là điều kiện
để connector Notion của Claude mở được CV.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from notion_client import Client
from notion_client.errors import APIResponseError

from app.application.ports.application_source import PendingApplication
from app.application.ports.cv_downloader import DownloadedFile
from app.application.ports.row_mirror import RowMirror
from app.domain.exceptions import CandidatePublishError
from app.infrastructure.notion.property_copier import (
    copy_properties,
    file_upload_value,
    rich_text_value,
)

logger = logging.getLogger(__name__)

SOURCE_ID_COLUMN = "Source ID"
RESUME_COLUMN = "Resume"


class NotionRowMirror(RowMirror):
    def __init__(self, api_key: str, target_data_source_id: str) -> None:
        if not target_data_source_id:
            raise ValueError("Thiếu NOTION_MIRROR_DATA_SOURCE_ID")
        self._client = Client(auth=api_key)
        self._target_id = target_data_source_id
        self._schema: dict[str, str] | None = None
        self._lock = asyncio.Lock()

    async def mirror(self, application: PendingApplication, cv: DownloadedFile | None) -> str:
        schema = await self._get_schema()
        properties, skipped = copy_properties(application.properties, schema)

        if skipped:
            logger.warning("Bỏ qua %d cột: %s", len(skipped), skipped[:5])

        # Khoá đối chiếu — thiếu nó thì lượt sau nhân bản lại chính dòng này.
        if SOURCE_ID_COLUMN in schema:
            properties[SOURCE_ID_COLUMN] = rich_text_value(application.source_page_id)
        else:
            raise CandidatePublishError(
                f"Bảng gương thiếu cột {SOURCE_ID_COLUMN!r} — không chống trùng được."
            )

        if cv is not None and RESUME_COLUMN in schema:
            upload_id = await self._upload(cv)
            properties[RESUME_COLUMN] = file_upload_value(upload_id, cv.filename)

        try:
            page: Any = await asyncio.to_thread(
                self._client.pages.create,
                parent={"type": "data_source_id", "data_source_id": self._target_id},
                properties=properties,
            )
        except APIResponseError as exc:
            raise CandidatePublishError(f"Notion từ chối tạo dòng: {exc}") from exc

        page_id: str = page["id"]
        logger.info("Đã nhân bản %s -> %s", application.candidate_name, page_id)
        return page_id

    async def _upload(self, cv: DownloadedFile) -> str:
        """Trả về file_upload_id để đính vào cột files."""
        content_type = cv.content_type or "application/pdf"
        try:
            created: Any = await asyncio.to_thread(
                self._client.file_uploads.create,
                filename=cv.filename,
                content_type=content_type,
            )
            await asyncio.to_thread(
                self._client.file_uploads.send,
                file_upload_id=created["id"],
                file=(cv.filename, cv.content, content_type),
            )
        except APIResponseError as exc:
            raise CandidatePublishError(f"Upload CV lên Notion lỗi: {exc}") from exc

        upload_id: str = created["id"]
        logger.debug("Đã upload %s (%d bytes) -> %s", cv.filename, len(cv.content), upload_id)
        return upload_id

    async def _get_schema(self) -> dict[str, str]:
        if self._schema is not None:
            return self._schema

        async with self._lock:
            if self._schema is not None:
                return self._schema
            try:
                data_source: Any = await asyncio.to_thread(
                    self._client.data_sources.retrieve,
                    data_source_id=self._target_id,
                )
            except APIResponseError as exc:
                raise CandidatePublishError(
                    f"Không đọc được schema bảng gương {self._target_id}: {exc}. "
                    "Nhớ share bảng đó cho integration."
                ) from exc

            self._schema = {name: prop["type"] for name, prop in data_source["properties"].items()}
            logger.info("Đã nạp schema bảng gương: %d cột", len(self._schema))
            return self._schema
