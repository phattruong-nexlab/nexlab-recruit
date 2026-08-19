"""Fake adapter cho các port — test không chạm mạng."""

from __future__ import annotations

from typing import Any

import pytest

from app.application.ports.application_source import ApplicationSource, PendingApplication
from app.application.ports.content_writer import ResumeContentWriter
from app.application.ports.cv_downloader import CvDownloader, DownloadedFile
from app.application.ports.cv_ocr import CvOcr
from app.application.ports.cv_reader import CvReader
from app.domain.exceptions import CandidatePublishError, CvDownloadError


class FakeDownloader(CvDownloader):
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.calls: list[str] = []

    async def download(self, url: str) -> DownloadedFile:
        self.calls.append(url)
        if self.should_fail:
            raise CvDownloadError("Link hỏng")
        return DownloadedFile(
            content=b"%PDF-fake", filename="cv.pdf", content_type="application/pdf"
        )


class FakeSource(ApplicationSource):
    def __init__(self, items: list[PendingApplication]) -> None:
        self.items = items

    async def list_pending(self, limit: int | None = None) -> list[PendingApplication]:
        return self.items[:limit] if limit else self.items

    async def count_pending(self) -> int:
        return len(self.items)


class FakeReader(CvReader):
    """`text` ngắn = giả lập PDF scan không có text layer."""

    def __init__(self, text: str = "x" * 500) -> None:
        self.text = text

    def to_text(self, file: DownloadedFile) -> str:
        return self.text


class FakeOcr(CvOcr):
    def __init__(self, text: str = "nội dung OCR " * 40) -> None:
        self.text = text
        self.calls: list[str] = []

    async def to_text(self, file: DownloadedFile) -> str:
        self.calls.append(file.filename)
        return self.text


class FakeWriter(ResumeContentWriter):
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.written: dict[str, str] = {}

    async def write(self, page_id: str, content: str) -> None:
        if self.should_fail:
            raise CandidatePublishError("Notion không phản hồi")
        self.written[page_id] = content


def make_application(index: int, with_cv: bool = True) -> PendingApplication:
    properties: dict[str, Any] = {
        "Candidate Name": {"type": "title", "title": [{"plain_text": f"Ứng viên {index}"}]},
        "Email": {"type": "email", "email": f"a{index}@example.com"},
    }
    return PendingApplication(
        source_page_id=f"src-{index}",
        candidate_name=f"Ứng viên {index}",
        file_url=f"https://storage.tally.so/cv-{index}.pdf" if with_cv else None,
        properties=properties,
        created_time="2026-08-10T00:00:00.000Z",
    )


@pytest.fixture
def applications() -> list[PendingApplication]:
    return [make_application(i) for i in range(5)]
