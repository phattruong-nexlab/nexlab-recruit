"""Port: ghi nội dung CV đã trích vào lại dòng nguồn trên Notion."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ResumeContentWriter(ABC):
    @abstractmethod
    async def write(self, page_id: str, content: str) -> None:
        """Ghi vào cột `Resume Content` của đúng dòng đó.

        Raises:
            CandidatePublishError: không ghi được.
        """
