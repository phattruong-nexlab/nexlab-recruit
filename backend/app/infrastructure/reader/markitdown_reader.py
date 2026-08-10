"""Adapter: markitdown — file CV sang Markdown.

Markdown giữ được heading / bullet / bảng, nên LLM tách field chính xác hơn text
phẳng. markitdown nhận nhiều định dạng (PDF, DOCX, PPTX, HTML...), không chỉ PDF.
"""

from __future__ import annotations

import io
import logging

from markitdown import MarkItDown, StreamInfo

from app.application.ports.cv_downloader import DownloadedFile
from app.application.ports.cv_reader import CvReader
from app.domain.exceptions import CvParsingError

logger = logging.getLogger(__name__)

# Ít hơn ngần này ký tự thì gần như chắc chắn là CV scan ảnh (cần OCR — ngoài phạm vi).
_MIN_MEANINGFUL_CHARS = 50


class MarkItDownCvReader(CvReader):
    def __init__(self, max_chars: int = 100_000) -> None:
        # enable_plugins=False: chỉ dùng converter có sẵn, không nạp plugin ngoài.
        self._converter = MarkItDown(enable_plugins=False)
        self._max_chars = max_chars

    def to_markdown(self, file: DownloadedFile) -> str:
        extension = f".{file.filename.rsplit('.', 1)[-1].lower()}" if "." in file.filename else None
        stream_info = StreamInfo(
            extension=extension,
            mimetype=file.content_type,
            filename=file.filename,
        )

        try:
            result = self._converter.convert(io.BytesIO(file.content), stream_info=stream_info)
        except Exception as exc:  # markitdown ném nhiều loại lỗi tuỳ converter
            raise CvParsingError(f"Không đọc được file {file.filename!r}: {exc}") from exc

        markdown = (result.text_content or "").strip()
        if len(markdown) < _MIN_MEANINGFUL_CHARS:
            raise CvParsingError(
                f"File {file.filename!r} gần như không có text "
                "(có thể là CV scan ảnh — cần OCR, ngoài phạm vi hiện tại)."
            )

        if len(markdown) > self._max_chars:
            logger.warning("CV dài %d ký tự, cắt còn %d", len(markdown), self._max_chars)
            markdown = markdown[: self._max_chars]

        return markdown
