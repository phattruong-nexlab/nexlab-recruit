"""Fake adapter cho các port — test không chạm mạng, không gọi LLM."""

from __future__ import annotations

import pytest

from app.application.dto.parse_cv import ExtractedCv, ExtractedExperience
from app.application.ports.candidate_publisher import CandidatePublisher
from app.application.ports.cv_downloader import CvDownloader, DownloadedFile
from app.application.ports.cv_extractor import CvExtractor
from app.application.ports.cv_reader import CvReader
from app.domain.entities.candidate import Candidate
from app.domain.exceptions import CandidatePublishError


class FakeDownloader(CvDownloader):
    def __init__(self, filename: str = "cv.pdf") -> None:
        self.filename = filename
        self.calls: list[str] = []

    async def download(self, url: str) -> DownloadedFile:
        self.calls.append(url)
        return DownloadedFile(content=b"%PDF-fake", filename=self.filename)


class FakeReader(CvReader):
    def __init__(self, markdown: str = "# CV\n\nNội dung") -> None:
        self.markdown = markdown

    def to_markdown(self, file: DownloadedFile) -> str:
        return self.markdown


class FakeExtractor(CvExtractor):
    def __init__(self, result: ExtractedCv) -> None:
        self.result = result
        self.seen_markdown: str | None = None

    async def extract(self, cv_markdown: str) -> ExtractedCv:
        self.seen_markdown = cv_markdown
        return self.result


class FakePublisher(CandidatePublisher):
    def __init__(self, page_id: str = "page-1", should_fail: bool = False) -> None:
        self.page_id = page_id
        self.should_fail = should_fail
        self.published: list[Candidate] = []

    async def publish(self, candidate: Candidate) -> str:
        if self.should_fail:
            raise CandidatePublishError("Notion tạm thời không phản hồi")
        self.published.append(candidate)
        return self.page_id


@pytest.fixture
def extracted_cv() -> ExtractedCv:
    return ExtractedCv(
        full_name="Trần Khánh Hoà",
        university="Đại học Bách Khoa",
        gpa=3.6,
        skills=["Python", "python", "SQL", "  "],
        certificates=["AWS Certified", "AWS Certified"],
        languages=["Tiếng Việt", "English"],
        experiences=[
            ExtractedExperience(
                company="Wow Entertainment",
                position="Data Engineer",
                start_year=2020,
                end_year=2024,
                description="Xây dựng pipeline",
            ),
            ExtractedExperience(
                company="Nexlab",
                position="Senior DE",
                start_year=2025,
                is_current=True,
                description="Airflow, Clickhouse",
            ),
            ExtractedExperience(company="   ", description="thiếu tên công ty"),
        ],
    )
