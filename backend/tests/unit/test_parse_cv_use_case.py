"""Use case là điều phối duy nhất của service — test kỹ các bất biến."""

from __future__ import annotations

from app.application.dto.parse_cv import ExtractedCv, ParseCvCommand
from app.application.use_cases.parse_cv import ParseCvUseCase
from tests.conftest import FakeDownloader, FakeExtractor, FakePublisher, FakeReader

_COMMAND = ParseCvCommand(
    file_url="https://file.notion.so/cv.pdf",
    job_url="https://nexlab.tech/jobs/senior-data-engineer",
    email="a@example.com",
    phone="+84900000000",
    created_time="2026-08-06T10:00:00.000Z",
)


def _use_case(extracted: ExtractedCv, publisher: FakePublisher | None) -> ParseCvUseCase:
    return ParseCvUseCase(
        downloader=FakeDownloader(),
        reader=FakeReader(),
        extractor=FakeExtractor(extracted),
        publisher=publisher,
    )


async def test_tra_ve_day_du_bay_nhom_thong_tin(extracted_cv: ExtractedCv) -> None:
    result = await _use_case(extracted_cv, FakePublisher()).execute(_COMMAND)

    assert result.full_name == "Trần Khánh Hoà"
    assert result.applied_job == "Senior Data Engineer"  # suy từ Job URL, không phải LLM
    assert result.university == "Đại học Bách Khoa"
    assert result.gpa == 3.6
    assert result.skills == ["Python", "SQL"]  # trùng và rỗng đã bị loại
    assert result.certificates == ["AWS Certified"]
    assert result.languages == ["Tiếng Việt", "English"]
    assert len(result.experiences) == 3


async def test_ghi_notion_thanh_cong_thi_tra_page_id(extracted_cv: ExtractedCv) -> None:
    publisher = FakePublisher(page_id="page-abc")

    result = await _use_case(extracted_cv, publisher).execute(_COMMAND)

    assert result.published is True
    assert result.notion_page_id == "page-abc"
    # Thông tin agent gửi kèm phải đi thẳng vào Notion, không qua LLM.
    written = publisher.published[0]
    assert written.email == "a@example.com"
    assert written.phone == "+84900000000"
    assert written.source_file_url == _COMMAND.file_url


async def test_notion_loi_van_tra_ket_qua_phan_tich(extracted_cv: ExtractedCv) -> None:
    """Đọc CV tốn một lần gọi LLM — không được vứt đi chỉ vì ghi Notion hỏng."""
    result = await _use_case(extracted_cv, FakePublisher(should_fail=True)).execute(_COMMAND)

    assert result.published is False
    assert result.publish_error is not None
    assert result.university == "Đại học Bách Khoa"
    assert result.skills == ["Python", "SQL"]


async def test_khong_cau_hinh_notion_thi_chi_phan_tich(extracted_cv: ExtractedCv) -> None:
    result = await _use_case(extracted_cv, None).execute(_COMMAND)

    assert result.published is False
    assert result.publish_error is None
    assert result.full_name == "Trần Khánh Hoà"


async def test_experience_thieu_ten_cong_ty_bi_loai_khoi_notion(
    extracted_cv: ExtractedCv,
) -> None:
    publisher = FakePublisher()

    await _use_case(extracted_cv, publisher).execute(_COMMAND)

    written = publisher.published[0]
    assert [e.company for e in written.experiences] == ["Wow Entertainment", "Nexlab"]
    assert written.total_experience_years == 4  # job đang làm thiếu end_year -> không tính


async def test_job_url_rong_thi_applied_job_la_none(extracted_cv: ExtractedCv) -> None:
    command = ParseCvCommand(file_url="https://file.notion.so/cv.pdf")

    result = await _use_case(extracted_cv, None).execute(command)

    assert result.applied_job is None
