"""Trích nội dung CV: OCR chỉ chạy khi cần, một CV hỏng không làm chết cả lượt."""

from __future__ import annotations

from app.application.ports.application_source import PendingApplication
from app.application.use_cases.extract_resume_content import (
    MIN_TEXT_CHARS,
    ExtractResumeContentUseCase,
)
from tests.conftest import (
    FakeDownloader,
    FakeOcr,
    FakeReader,
    FakeSource,
    FakeWriter,
    make_application,
)


def _use_case(
    items: list[PendingApplication],
    reader: FakeReader | None = None,
    writer: FakeWriter | None = None,
    ocr: FakeOcr | None = None,
    downloader: FakeDownloader | None = None,
) -> ExtractResumeContentUseCase:
    return ExtractResumeContentUseCase(
        source=FakeSource(items),
        downloader=downloader or FakeDownloader(),
        reader=reader or FakeReader(),
        writer=writer or FakeWriter(),
        ocr=ocr,
        concurrency=3,
    )


async def test_ghi_text_vao_dung_dong_nguon(applications: list[PendingApplication]) -> None:
    writer = FakeWriter()

    summary = await _use_case(applications, writer=writer).execute()

    assert summary.succeeded == 5
    assert set(writer.written) == {f"src-{i}" for i in range(5)}


async def test_pdf_co_text_thi_khong_goi_ocr(applications: list[PendingApplication]) -> None:
    """OCR tốn tiền — chỉ được dùng khi thư viện bó tay."""
    ocr = FakeOcr()

    await _use_case(applications, ocr=ocr).execute()

    assert ocr.calls == []


async def test_pdf_scan_thi_chuyen_sang_ocr() -> None:
    """markitdown trả gần rỗng ⇒ PDF là ảnh scan ⇒ dùng model đọc."""
    reader = FakeReader(text="x" * (MIN_TEXT_CHARS - 1))
    ocr = FakeOcr(text="nội dung đọc bằng OCR")
    writer = FakeWriter()

    summary = await _use_case([make_application(1)], reader, writer, ocr).execute()

    assert summary.succeeded == 1
    assert ocr.calls == ["cv.pdf"]
    assert writer.written["src-1"] == "nội dung đọc bằng OCR"


async def test_pdf_scan_ma_tat_ocr_thi_bao_loi_ro_rang() -> None:
    reader = FakeReader(text="")

    summary = await _use_case([make_application(1)], reader, ocr=None).execute()

    assert summary.failed == 1
    assert "chưa bật OCR" in summary.failures[0].reason


async def test_tai_cv_loi_thi_dem_la_that_bai(
    applications: list[PendingApplication],
) -> None:
    summary = await _use_case(applications, downloader=FakeDownloader(should_fail=True)).execute()

    assert summary.failed == 5
    assert "CvDownloadError" in summary.failures[0].reason


async def test_ghi_notion_loi_thi_dem_la_that_bai(
    applications: list[PendingApplication],
) -> None:
    summary = await _use_case(applications, writer=FakeWriter(should_fail=True)).execute()

    assert summary.failed == 5
    assert summary.succeeded == 0


async def test_chua_dinh_cv_thi_bo_qua_co_ly_do() -> None:
    summary = await _use_case([make_application(1, with_cv=False)]).execute()

    assert summary.failed == 1
    assert summary.failures[0].reason == "Chưa đính CV"


async def test_limit_chi_lam_n_cv_dau(applications: list[PendingApplication]) -> None:
    writer = FakeWriter()

    summary = await _use_case(applications, writer=writer).execute(limit=2)

    assert summary.total == 2
    assert len(writer.written) == 2
