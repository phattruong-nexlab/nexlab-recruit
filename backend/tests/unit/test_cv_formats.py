"""Nhiều ứng viên nộp CV dạng .docx — phải đọc được bằng thư viện, không sang OCR."""

from __future__ import annotations

import io
import zipfile

import pytest

from app.application.ports.cv_downloader import DownloadedFile
from app.domain.exceptions import CvParsingError
from app.infrastructure.llm.gemini_ocr import GeminiCvOcr
from app.infrastructure.reader.markitdown_reader import MarkItDownCvReader

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml"
 ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1"
 Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
 Target="word/document.xml"/>
</Relationships>"""

_DOCUMENT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body>
</w:document>"""


def _make_docx(text: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _RELS)
        archive.writestr("word/document.xml", _DOCUMENT.format(text=text))
    return buffer.getvalue()


def test_markitdown_doc_duoc_docx() -> None:
    file = DownloadedFile(
        content=_make_docx("Nguyen Van A - Business Analyst"),
        filename="Resume-Nguyen-Van-A.docx",
        content_type=DOCX_MIME,
    )

    assert "Business Analyst" in MarkItDownCvReader().to_text(file)


async def test_ocr_tu_choi_file_khong_phai_pdf_hay_anh() -> None:
    """Gemini trả 400 cho docx; báo lỗi rõ ràng thay vì gọi API rồi hỏng."""
    ocr = GeminiCvOcr.__new__(GeminiCvOcr)  # không tạo client Vertex AI thật
    file = DownloadedFile(content=b"", filename="cv.docx", content_type=DOCX_MIME)

    with pytest.raises(CvParsingError, match="chỉ hỗ trợ PDF hoặc ảnh"):
        await ocr.to_text(file)
