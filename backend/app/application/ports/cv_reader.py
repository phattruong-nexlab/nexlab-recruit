"""Port: đọc file CV thành Markdown (spec bước [2])."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.application.ports.cv_downloader import DownloadedFile


class CvReader(ABC):
    """Markdown giữ được cấu trúc (heading, bullet, bảng) nên LLM tách field
    chính xác hơn so với text phẳng."""

    @abstractmethod
    def to_markdown(self, file: DownloadedFile) -> str:
        """Raises: CvParsingError khi file hỏng hoặc không có text (CV scan ảnh)."""
