"""Use case: đọc nội dung CV rồi ghi vào cột `Resume Content` của chính dòng đó.

Không trích xuất field, không suy luận — chỉ lấy nguyên văn text để về sau người
hoặc AI đọc được mà không cần mở PDF.
"""

from __future__ import annotations

import asyncio
import logging

from app.application.dto.scan import ScanFailure, ScanSummary
from app.application.ports.application_source import (
    ApplicationSource,
    PendingApplication,
    PendingFilter,
)
from app.application.ports.content_writer import ResumeContentWriter
from app.application.ports.cv_downloader import CvDownloader
from app.application.ports.cv_ocr import CvOcr
from app.application.ports.cv_reader import CvReader
from app.domain.exceptions import DomainError

logger = logging.getLogger(__name__)

# Ít hơn ngần này ký tự thì coi như PDF không có text layer (bản scan ảnh).
MIN_TEXT_CHARS = 200


class ExtractResumeContentUseCase:
    def __init__(
        self,
        source: ApplicationSource,
        downloader: CvDownloader,
        reader: CvReader,
        writer: ResumeContentWriter,
        ocr: CvOcr | None = None,
        concurrency: int = 4,
    ) -> None:
        self._source = source
        self._downloader = downloader
        self._reader = reader
        self._writer = writer
        self._ocr = ocr
        self._semaphore = asyncio.Semaphore(max(1, concurrency))

    async def count_pending(self, pending_filter: PendingFilter | None = None) -> int:
        return await self._source.count_pending(pending_filter=pending_filter)

    async def list_pending(
        self, pending_filter: PendingFilter | None = None
    ) -> list[PendingApplication]:
        """Cho trang quản trị hiển thị số lượng và danh sách job đang chờ."""
        return await self._source.list_pending(pending_filter=pending_filter)

    async def execute(
        self, limit: int | None = None, pending_filter: PendingFilter | None = None
    ) -> ScanSummary:
        pending = await self._source.list_pending(limit=limit, pending_filter=pending_filter)
        summary = ScanSummary(total=len(pending))

        if not pending:
            logger.info("Không có đơn nào cần trích nội dung.")
            return summary

        logger.info("Trích nội dung %d CV", len(pending))
        results = await asyncio.gather(*(self._process(item) for item in pending))

        for application, failure in zip(pending, results, strict=True):
            if failure is None:
                summary.succeeded += 1
            else:
                summary.failed += 1
                summary.failures.append(
                    ScanFailure(
                        source_page_id=application.source_page_id,
                        candidate_name=application.candidate_name,
                        reason=failure,
                    )
                )

        logger.info("Xong: %d thành công, %d lỗi", summary.succeeded, summary.failed)
        return summary

    async def _process(self, application: PendingApplication) -> str | None:
        """None = thành công. Lỗi một CV không làm chết cả lượt."""
        if not application.file_url:
            return "Chưa đính CV"

        async with self._semaphore:
            try:
                file = await self._downloader.download(application.file_url)

                # Thư viện trước, OCR sau — OCR tốn tiền nên chỉ dùng khi cần.
                text = self._reader.to_text(file)
                if len(text) < MIN_TEXT_CHARS:
                    if self._ocr is None:
                        return f"PDF không có text ({len(text)} ký tự) và chưa bật OCR"
                    logger.info(
                        "%s: chỉ đọc được %d ký tự, chuyển sang OCR",
                        application.candidate_name,
                        len(text),
                    )
                    text = await self._ocr.to_text(file)

                await self._writer.write(application.source_page_id, text)
            except DomainError as exc:
                logger.warning("Lỗi %s: %s", application.candidate_name, exc)
                return f"{type(exc).__name__}: {exc}"
            except Exception as exc:
                logger.exception("Lỗi không lường trước ở %s", application.candidate_name)
                return f"{type(exc).__name__}: {exc}"

            return None
