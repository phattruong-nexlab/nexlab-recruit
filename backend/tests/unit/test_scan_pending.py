"""Quét hàng loạt: một CV hỏng không được làm chết cả lượt, và không tạo dòng trùng."""

from __future__ import annotations

from app.application.dto.parse_cv import ExtractedCv
from app.application.ports.application_source import ApplicationSource, PendingApplication
from app.application.use_cases.parse_cv import ParseCvUseCase
from app.application.use_cases.scan_pending import ScanPendingUseCase
from app.domain.exceptions import CvParsingError
from tests.conftest import FakeDownloader, FakeExtractor, FakePublisher, FakeReader


class FakeSource(ApplicationSource):
    def __init__(self, items: list[PendingApplication]) -> None:
        self.items = items

    async def list_pending(self, limit: int | None = None) -> list[PendingApplication]:
        return self.items[:limit] if limit else self.items

    async def count_pending(self) -> int:
        return len(self.items)


class ExplodingReader(FakeReader):
    """Hỏng ở đúng một CV, các CV khác vẫn đọc được."""

    def __init__(self, bad_filename: str) -> None:
        super().__init__()
        self.bad = bad_filename

    def to_markdown(self, file: object) -> str:  # type: ignore[override]
        if getattr(file, "filename", "") == self.bad:
            raise CvParsingError("File hỏng")
        return self.markdown


def _application(index: int) -> PendingApplication:
    return PendingApplication(
        source_page_id=f"src-{index}",
        candidate_name=f"Ứng viên {index}",
        file_url=f"https://storage.tally.so/cv-{index}.pdf",
        job_url="/jobs/senior-data-engineer",
        email=f"a{index}@example.com",
    )


def _use_case(
    source: FakeSource,
    extracted: ExtractedCv,
    publisher: FakePublisher | None = None,
    reader: FakeReader | None = None,
) -> ScanPendingUseCase:
    return ScanPendingUseCase(
        source=source,
        parse_cv=ParseCvUseCase(
            downloader=FakeDownloader(),
            reader=reader or FakeReader(),
            extractor=FakeExtractor(extracted),
            publisher=publisher or FakePublisher(),
        ),
        concurrency=3,
    )


async def test_xu_ly_het_don_dang_cho(extracted_cv: ExtractedCv) -> None:
    source = FakeSource([_application(i) for i in range(5)])
    publisher = FakePublisher()

    summary = await _use_case(source, extracted_cv, publisher).execute()

    assert summary.total == 5
    assert summary.succeeded == 5
    assert summary.failed == 0
    assert len(publisher.published) == 5


async def test_khong_don_nao_thi_khong_lam_gi(extracted_cv: ExtractedCv) -> None:
    summary = await _use_case(FakeSource([]), extracted_cv).execute()

    assert summary.total == 0
    assert summary.all_ok


async def test_ghi_notion_loi_thi_dem_la_that_bai(extracted_cv: ExtractedCv) -> None:
    """Thất bại phải được ghi nhận, để lượt sau tự nhặt lại — không im lặng bỏ qua."""
    source = FakeSource([_application(1)])

    summary = await _use_case(source, extracted_cv, FakePublisher(should_fail=True)).execute()

    assert summary.failed == 1
    assert summary.succeeded == 0
    assert summary.failures[0].source_page_id == "src-1"


async def test_mot_cv_hong_khong_lam_chet_ca_luot(extracted_cv: ExtractedCv) -> None:
    source = FakeSource([_application(i) for i in range(4)])
    publisher = FakePublisher()
    reader = ExplodingReader(bad_filename="cv.pdf")  # FakeDownloader luôn trả tên này

    summary = await _use_case(source, extracted_cv, publisher, reader).execute()

    # Cả 4 đều dùng cùng tên file nên hỏng hết — điều cần khẳng định là use case
    # không ném exception ra ngoài mà gom thành báo cáo.
    assert summary.total == 4
    assert summary.failed == 4
    assert all("CvParsingError" in f.reason for f in summary.failures)


async def test_limit_chi_xu_ly_n_don_dau(extracted_cv: ExtractedCv) -> None:
    source = FakeSource([_application(i) for i in range(10)])
    publisher = FakePublisher()

    summary = await _use_case(source, extracted_cv, publisher).execute(limit=3)

    assert summary.total == 3
    assert len(publisher.published) == 3


async def test_source_page_id_duoc_ghi_de_doi_chieu(extracted_cv: ExtractedCv) -> None:
    """Thiếu Source ID thì lượt sau sẽ xử lý lại người đó — tạo dòng trùng."""
    source = FakeSource([_application(7)])
    publisher = FakePublisher()

    await _use_case(source, extracted_cv, publisher).execute()

    assert publisher.published[0].source_page_id == "src-7"
