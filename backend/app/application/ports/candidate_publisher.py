"""Port: ghi ứng viên đã trích xuất lên Notion (spec bước [4])."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.candidate import Candidate


class CandidatePublisher(ABC):
    @abstractmethod
    async def publish(self, candidate: Candidate) -> str:
        """Tạo dòng mới trong bảng đích, trả về page id.

        Raises:
            CandidatePublishError: use case bắt lỗi này và vẫn trả kết quả phân
            tích cho agent, không để mất công đọc CV.
        """
