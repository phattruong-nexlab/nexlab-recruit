"""Use case: tải CV → Markdown → LLM trích xuất → ghi Notion.

Điều phối duy nhất của service. Không chứa chi tiết SDK nào.
"""

from __future__ import annotations

import logging

from app.application.dto.parse_cv import (
    ExtractedCv,
    ParseCvCommand,
    ParseCvResult,
)
from app.application.ports.candidate_publisher import CandidatePublisher
from app.application.ports.cv_downloader import CvDownloader
from app.application.ports.cv_extractor import CvExtractor
from app.application.ports.cv_reader import CvReader
from app.domain.entities.candidate import Candidate
from app.domain.entities.experience import Experience
from app.domain.exceptions import CandidatePublishError
from app.domain.services import applied_job, candidate_normalizer
from app.domain.value_objects.employment_period import EmploymentPeriod
from app.domain.value_objects.skill_set import SkillSet

logger = logging.getLogger(__name__)


class ParseCvUseCase:
    def __init__(
        self,
        downloader: CvDownloader,
        reader: CvReader,
        extractor: CvExtractor,
        publisher: CandidatePublisher | None = None,
    ) -> None:
        self._downloader = downloader
        self._reader = reader
        self._extractor = extractor
        self._publisher = publisher

    async def execute(self, command: ParseCvCommand) -> ParseCvResult:
        # [1] Tải file — link Notion có chữ ký, hết hạn ~1h nên phải tải ngay.
        file = await self._downloader.download(command.file_url)

        # [2] File -> Markdown (giữ heading/bullet/bảng cho LLM dễ tách field)
        markdown = self._reader.to_markdown(file)

        # [3] Một lần gọi LLM duy nhất
        extracted = await self._extractor.extract(markdown)

        # [4] Map sang domain + chuẩn hoá (thuần code, không LLM)
        candidate = _to_candidate(extracted, command)
        candidate = candidate_normalizer.normalize(candidate)

        # [5] Ghi Notion — lỗi ở đây KHÔNG làm mất kết quả phân tích
        notion_page_id: str | None = None
        publish_error: str | None = None
        if self._publisher is not None:
            try:
                notion_page_id = await self._publisher.publish(candidate)
            except CandidatePublishError as exc:
                publish_error = str(exc)
                logger.warning(
                    "Ghi Notion thất bại cho %s: %s — vẫn trả kết quả cho agent",
                    candidate.full_name or command.file_url,
                    exc,
                )

        return ParseCvResult(
            full_name=candidate.full_name,
            applied_job=candidate.applied_job,
            university=candidate.university,
            gpa=candidate.gpa,
            experiences=extracted.experiences,
            skills=candidate.skills.as_list(),
            certificates=candidate.certificates,
            languages=candidate.languages,
            total_experience_years=candidate.total_experience_years,
            notion_page_id=notion_page_id,
            published=notion_page_id is not None,
            publish_error=publish_error,
        )


def _to_candidate(extracted: ExtractedCv, command: ParseCvCommand) -> Candidate:
    experiences = [
        Experience(
            company=item.company,
            position=item.position,
            period=EmploymentPeriod(
                start_year=item.start_year,
                end_year=None if item.is_current else item.end_year,
                is_current=item.is_current,
            ),
            description=item.description,
            order_index=index,
        )
        for index, item in enumerate(extracted.experiences)
    ]

    return Candidate(
        full_name=extracted.full_name,
        # Vị trí ứng tuyển lấy từ Job URL agent gửi sang, không để LLM đoán.
        applied_job=applied_job.from_job_url(command.job_url),
        university=extracted.university,
        gpa=extracted.gpa,
        experiences=experiences,
        skills=SkillSet.from_raw(extracted.skills),
        certificates=list(extracted.certificates),
        languages=list(extracted.languages),
        email=command.email,
        phone=command.phone,
        job_url=command.job_url,
        applied_at=command.created_time,
        source_file_url=command.file_url,
    )
