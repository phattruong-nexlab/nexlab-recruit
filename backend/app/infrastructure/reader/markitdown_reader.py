"""Adapter: markitdown — file CV sang Markdown.

Giữ được heading / bullet / bảng nên text đọc ra có cấu trúc, dễ dùng lại về sau.
markitdown nhận nhiều định dạng (PDF, DOCX, PPTX, HTML...), không chỉ PDF.

PDF dạng ảnh scan sẽ ra chuỗi gần rỗng — đó KHÔNG phải lỗi, người gọi chuyển
sang OCR.
"""

from __future__ import annotations

import io
import logging

from markitdown import MarkItDown, StreamInfo

from app.application.ports.cv_downloader import DownloadedFile
from app.application.ports.cv_reader import CvReader

logger = logging.getLogger(__name__)


class MarkItDownCvReader(CvReader):
    def __init__(self, max_chars: int = 200_000) -> None:
        # enable_plugins=False: chỉ dùng converter có sẵn, không nạp plugin ngoài.
        self._converter = MarkItDown(enable_plugins=False)
        self._max_chars = max_chars

    def to_text(self, file: DownloadedFile) -> str:
        extension = None
        if "." in file.filename:
            extension = f".{file.filename.rsplit('.', 1)[-1].lower()}"

        stream_info = StreamInfo(
            extension=extension,
            mimetype=file.content_type,
            filename=file.filename,
        )

        try:
            result = self._converter.convert(io.BytesIO(file.content), stream_info=stream_info)
        except Exception as exc:  # markitdown ném nhiều loại lỗi tuỳ converter
            logger.warning("markitdown không đọc được %s: %s", file.filename, exc)
            return ""

        text = (result.text_content or "").strip()
        if len(text) > self._max_chars:
            logger.warning("CV dài %d ký tự, cắt còn %d", len(text), self._max_chars)
            text = text[: self._max_chars]
        return text
