"""Port: đọc danh sách đơn ứng tuyển cần trích nội dung CV."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PendingFilter:
    """Thu hẹp phạm vi một lượt chạy. Cả hai để trống = làm tất cả những gì còn thiếu."""

    since: str | None = None
    """Chỉ lấy đơn nộp từ ngày này trở đi, dạng YYYY-MM-DD."""

    job_url_contains: str | None = None
    """Chỉ lấy đơn có Job URL chứa chuỗi này, ví dụ 'junior-frontend'."""

    @property
    def is_empty(self) -> bool:
        return not self.since and not self.job_url_contains

    def describe(self) -> str:
        parts = []
        if self.since:
            parts.append(f"từ {self.since}")
        if self.job_url_contains:
            parts.append(f"job chứa {self.job_url_contains!r}")
        return ", ".join(parts) or "tất cả"


@dataclass(slots=True)
class PendingApplication:
    """Một đơn ứng tuyển có CV nhưng chưa có nội dung đã trích."""

    source_page_id: str
    candidate_name: str
    file_url: str | None
    """Link CV ở cột "Resume, CL"; None nếu ứng viên chưa đính file."""

    job_url: str = ""
    properties: dict[str, Any] = field(default_factory=dict)
    """Nguyên `page["properties"]` của dòng nguồn."""

    created_time: str | None = None


class ApplicationSource(ABC):
    @abstractmethod
    async def list_pending(
        self, limit: int | None = None, pending_filter: PendingFilter | None = None
    ) -> list[PendingApplication]:
        """Đơn có CV mà cột đích còn rỗng, thu hẹp thêm theo `pending_filter`.

        Cột đích rỗng hay không CHÍNH LÀ dấu hiệu đã xử lý — nên chạy lại bao
        nhiêu lần cũng không làm lại việc đã xong, kể cả khi bộ lọc trùng nhau.
        """

    @abstractmethod
    async def count_pending(self, pending_filter: PendingFilter | None = None) -> int:
        """Đếm để hiển thị, không xử lý gì."""
