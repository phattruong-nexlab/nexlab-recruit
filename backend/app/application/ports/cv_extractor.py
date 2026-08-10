"""Port: trích xuất field có cấu trúc từ Markdown của CV (spec bước [3])."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.application.dto.parse_cv import ExtractedCv


class CvExtractor(ABC):
    """Một LLM call + structured output. Đây là nơi DUY NHẤT trong hệ thống gọi LLM."""

    @abstractmethod
    async def extract(self, cv_markdown: str) -> ExtractedCv:
        """Raises: CvExtractionError khi LLM trả về cấu trúc không hợp lệ."""
