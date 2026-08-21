"""Composition root: nơi DUY NHẤT ghép adapter cụ thể vào port."""

from __future__ import annotations

import logging
from functools import lru_cache

from app.application.composite_source import CompositeApplicationSource
from app.application.ports.application_source import ApplicationSource
from app.application.ports.cv_ocr import CvOcr
from app.application.use_cases.extract_resume_content import ExtractResumeContentUseCase
from app.infrastructure.http.file_downloader import HttpCvDownloader
from app.infrastructure.llm.gemini_ocr import GeminiCvOcr
from app.infrastructure.notion.application_source import NotionApplicationSource
from app.infrastructure.notion.content_writer import NotionResumeContentWriter
from app.infrastructure.reader.markitdown_reader import MarkItDownCvReader
from config import Settings, get_settings

logger = logging.getLogger(__name__)


def _build_source(settings: Settings) -> ApplicationSource:
    """Một adapter cho mỗi bảng nguồn, gộp lại thành một."""
    ids = settings.source_data_source_ids
    if not ids:
        raise ValueError("Thiếu NOTION_SOURCE_DATA_SOURCE_IDS")

    sources: list[ApplicationSource] = [
        NotionApplicationSource(api_key=settings.notion_api_key, data_source_id=ds) for ds in ids
    ]
    logger.info("Đọc từ %d bảng nguồn", len(sources))
    return CompositeApplicationSource(sources)


@lru_cache
def get_extract_use_case() -> ExtractResumeContentUseCase:
    """Dùng chung cho Cloud Run Job (theo lịch) và nút bấm ở trang quản trị."""
    settings = get_settings()

    ocr: CvOcr | None = None
    if settings.ocr_enabled:
        ocr = GeminiCvOcr(
            model=settings.gemini_model,
            project_id=settings.gcp_project_id,
            location=settings.vertex_location,
            timeout_seconds=settings.ocr_timeout_seconds,
        )
    else:
        logger.warning("OCR đang tắt — CV dạng scan ảnh sẽ bị báo lỗi thay vì đọc được.")

    return ExtractResumeContentUseCase(
        source=_build_source(settings),
        downloader=HttpCvDownloader(
            timeout_seconds=settings.download_timeout_seconds,
            max_bytes=settings.max_cv_bytes,
            allowed_hosts=settings.allowed_file_hosts,
        ),
        reader=MarkItDownCvReader(),
        writer=NotionResumeContentWriter(api_key=settings.notion_api_key),
        ocr=ocr,
        concurrency=settings.scan_concurrency,
    )
