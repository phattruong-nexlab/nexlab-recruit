"""Port: đọc danh sách đơn ứng tuyển cần xử lý từ bảng nguồn."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class PendingApplication:
    """Một đơn ứng tuyển đã có CV nhưng chưa được quét."""

    source_page_id: str
    candidate_name: str
    file_url: str
    job_url: str | None = None
    email: str | None = None
    phone: str | None = None
    created_time: str | None = None


class ApplicationSource(ABC):
    @abstractmethod
    async def list_pending(self, limit: int | None = None) -> list[PendingApplication]:
        """Đơn có CV, trừ đi những đơn đã có mặt ở bảng đích.

        Là phép TRỪ TẬP HỢP chứ không phải mốc thời gian: chạy lại bao nhiêu lần
        cũng ra đúng, đơn lỗi hôm trước tự được nhặt lại, CV về muộn cũng không sót.
        """

    @abstractmethod
    async def count_pending(self) -> int:
        """Đếm nhanh để hiển thị, không tải toàn bộ chi tiết."""
