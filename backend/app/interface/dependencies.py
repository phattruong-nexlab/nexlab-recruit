"""Composition root: nơi DUY NHẤT ghép adapter cụ thể vào port."""

from __future__ import annotations

import logging
from functools import lru_cache

from app.application.use_cases.mirror_applications import MirrorApplicationsUseCase
from app.infrastructure.http.file_downloader import HttpCvDownloader
from app.infrastructure.notion.application_source import NotionApplicationSource
from app.infrastructure.notion.row_mirror import NotionRowMirror
from config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_mirror_use_case() -> MirrorApplicationsUseCase:
    """Dùng chung cho Cloud Run Job (theo lịch) và nút bấm ở trang quản trị."""
    settings = get_settings()

    return MirrorApplicationsUseCase(
        source=NotionApplicationSource(
            api_key=settings.notion_api_key,
            source_data_source_id=settings.notion_source_data_source_id,
            target_data_source_id=settings.notion_mirror_data_source_id,
        ),
        downloader=HttpCvDownloader(
            timeout_seconds=settings.download_timeout_seconds,
            max_bytes=settings.max_cv_bytes,
            allowed_hosts=settings.allowed_file_hosts,
        ),
        mirror=NotionRowMirror(
            api_key=settings.notion_api_key,
            target_data_source_id=settings.notion_mirror_data_source_id,
        ),
        concurrency=settings.scan_concurrency,
    )
