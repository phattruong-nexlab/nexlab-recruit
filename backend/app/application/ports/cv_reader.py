"""Port: đọc file CV thành text."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.application.ports.cv_downloader import DownloadedFile


class CvReader(ABC):
    @abstractmethod
    def to_text(self, file: DownloadedFile) -> str:
        """Trả về text/Markdown của CV.

        Chuỗi rỗng hoặc quá ngắn nghĩa là PDF không có text layer (bản scan ảnh)
        — người gọi phải chuyển sang OCR, KHÔNG coi là lỗi.
        """
