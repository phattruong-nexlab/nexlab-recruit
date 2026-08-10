"""Port: tải file CV từ URL agent gửi sang (spec bước [1])."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class DownloadedFile:
    content: bytes
    filename: str
    content_type: str | None = None


class CvDownloader(ABC):
    @abstractmethod
    async def download(self, url: str) -> DownloadedFile:
        """Raises: CvDownloadError khi URL sai, hết hạn, quá lớn hoặc host lạ."""
