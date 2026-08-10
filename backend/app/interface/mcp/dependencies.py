"""Composition root: nơi DUY NHẤT ghép adapter cụ thể vào port."""

from __future__ import annotations

import logging
from functools import lru_cache

from app.application.ports.candidate_publisher import CandidatePublisher
from app.application.use_cases.parse_cv import ParseCvUseCase
from app.infrastructure.http.file_downloader import HttpCvDownloader
from app.infrastructure.llm.gemini_cv_extractor import GeminiCvExtractor
from app.infrastructure.notion.notion_publisher import NotionCandidatePublisher
from app.infrastructure.reader.markitdown_reader import MarkItDownCvReader
from config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_parse_cv_use_case() -> ParseCvUseCase:
    """Khởi tạo một lần rồi dùng lại — markitdown và các client đều nặng."""
    settings = get_settings()

    publisher: CandidatePublisher | None = None
    if settings.notion_api_key and settings.notion_target_data_source_id:
        publisher = NotionCandidatePublisher(
            api_key=settings.notion_api_key,
            data_source_id=settings.notion_target_data_source_id,
        )
    else:
        logger.warning("Chưa cấu hình Notion đích — tool sẽ chỉ trả kết quả phân tích, không ghi.")

    return ParseCvUseCase(
        downloader=HttpCvDownloader(
            timeout_seconds=settings.download_timeout_seconds,
            max_bytes=settings.max_cv_bytes,
            allowed_hosts=settings.allowed_file_hosts,
        ),
        reader=MarkItDownCvReader(),
        extractor=GeminiCvExtractor(
            model=settings.gemini_model,
            project_id=settings.gcp_project_id,
            location=settings.vertex_location,
            timeout_seconds=settings.gemini_timeout_seconds,
        ),
        publisher=publisher,
    )
