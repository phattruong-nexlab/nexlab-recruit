"""Port: đọc text từ CV dạng ảnh scan bằng model đa phương thức."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.application.ports.cv_downloader import DownloadedFile


class CvOcr(ABC):
    """Chỉ dùng khi thư viện trích text thất bại — mỗi lần gọi là một lần tốn tiền."""

    @abstractmethod
    async def to_text(self, file: DownloadedFile) -> str:
        """Raises: CvParsingError nếu model không đọc được."""
