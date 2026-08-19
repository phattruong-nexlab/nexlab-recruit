"""Use case: nhân bản đơn ứng tuyển sang bảng gương, kèm CV do Notion lưu.

Không đọc nội dung CV, không gọi LLM. Chỉ chép giá trị cột và biến file `external`
(Tally) thành file Notion tự lưu — để connector của Claude mở được.
"""

from __future__ import annotations

import asyncio
import logging

from app.application.dto.scan import ScanFailure, ScanSummary
from app.application.ports.application_source import ApplicationSource, PendingApplication
from app.application.ports.cv_downloader import CvDownloader, DownloadedFile
from app.application.ports.row_mirror import RowMirror
from app.domain.exceptions import CvDownloadError, DomainError

logger = logging.getLogger(__name__)


class MirrorApplicationsUseCase:
    def __init__(
        self,
        source: ApplicationSource,
        downloader: CvDownloader,
        mirror: RowMirror,
        concurrency: int = 4,
    ) -> None:
        self._source = source
        self._downloader = downloader
        self._mirror = mirror
        # Notion giới hạn ~3 req/s, mỗi dòng tốn ~5 lời gọi nên đừng đẩy quá cao.
        self._semaphore = asyncio.Semaphore(max(1, concurrency))

    async def count_pending(self) -> int:
        return await self._source.count_pending()

    async def execute(self, limit: int | None = None) -> ScanSummary:
        pending = await self._source.list_pending(limit=limit)
        summary = ScanSummary(total=len(pending))

        if not pending:
            logger.info("Không có dòng nào cần nhân bản.")
            return summary

        logger.info("Nhân bản %d dòng", len(pending))
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
        """None = thành công. Lỗi một dòng không làm chết cả lượt."""
        async with self._semaphore:
            cv: DownloadedFile | None = None
            try:
                if application.file_url:
                    cv = await self._downloader.download(application.file_url)
            except CvDownloadError as exc:
                # Tải CV hỏng thì vẫn chép các cột còn lại — có dữ liệu vẫn hơn không.
                logger.warning("Không tải được CV của %s: %s", application.candidate_name, exc)

            try:
                await self._mirror.mirror(application, cv)
            except DomainError as exc:
                logger.warning("Lỗi %s: %s", application.candidate_name, exc)
                return f"{type(exc).__name__}: {exc}"
            except Exception as exc:
                logger.exception("Lỗi không lường trước ở %s", application.candidate_name)
                return f"{type(exc).__name__}: {exc}"

            return None
