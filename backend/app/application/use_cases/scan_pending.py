"""Use case: quét toàn bộ đơn ứng tuyển chưa xử lý.

Dùng chung cho cả hai đường kích hoạt: Cloud Scheduler chạy theo lịch, và HR bấm
nút trên trang quản trị. Cả hai đều gọi đúng hàm này.
"""

from __future__ import annotations

import asyncio
import logging

from app.application.dto.parse_cv import ParseCvCommand
from app.application.dto.scan import ScanFailure, ScanSummary
from app.application.ports.application_source import ApplicationSource, PendingApplication
from app.application.use_cases.parse_cv import ParseCvUseCase
from app.domain.exceptions import DomainError

logger = logging.getLogger(__name__)


class ScanPendingUseCase:
    def __init__(
        self,
        source: ApplicationSource,
        parse_cv: ParseCvUseCase,
        concurrency: int = 4,
    ) -> None:
        self._source = source
        self._parse_cv = parse_cv
        # Vertex AI và Notion đều có rate limit; chạy song song vừa phải là đủ nhanh.
        self._semaphore = asyncio.Semaphore(max(1, concurrency))

    async def count_pending(self) -> int:
        """Cho trang quản trị hiển thị, không xử lý gì."""
        return await self._source.count_pending()

    async def execute(self, limit: int | None = None) -> ScanSummary:
        pending = await self._source.list_pending(limit=limit)
        summary = ScanSummary(total=len(pending))

        if not pending:
            logger.info("Không có đơn nào cần xử lý.")
            return summary

        logger.info("Bắt đầu xử lý %d đơn (song song %d)", len(pending), self._semaphore._value)
        results = await asyncio.gather(
            *(self._process(item) for item in pending),
            return_exceptions=False,
        )

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

        logger.info(
            "Xong: %d thành công, %d lỗi trên tổng %d",
            summary.succeeded,
            summary.failed,
            summary.total,
        )
        return summary

    async def _process(self, application: PendingApplication) -> str | None:
        """Trả về None nếu thành công, chuỗi lý do nếu lỗi.

        Một CV hỏng KHÔNG được làm chết cả lượt — lượt sau sẽ tự nhặt lại nó vì
        nó vẫn chưa có mặt ở bảng đích.
        """
        async with self._semaphore:
            try:
                result = await self._parse_cv.execute(
                    ParseCvCommand(
                        file_url=application.file_url,
                        job_url=application.job_url,
                        email=application.email,
                        phone=application.phone,
                        created_time=application.created_time,
                        source_page_id=application.source_page_id,
                    )
                )
            except DomainError as exc:
                logger.warning("Lỗi %s: %s", application.candidate_name, exc)
                return f"{type(exc).__name__}: {exc}"
            except Exception as exc:  # lỗi ngoài dự kiến cũng không được làm chết lượt
                logger.exception("Lỗi không lường trước ở %s", application.candidate_name)
                return f"{type(exc).__name__}: {exc}"

            if not result.published:
                return result.publish_error or "Ghi Notion thất bại"
            return None
