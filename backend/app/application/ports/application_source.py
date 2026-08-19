"""Port: đọc danh sách đơn ứng tuyển cần xử lý từ bảng nguồn."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PendingApplication:
    """Một đơn ứng tuyển chưa có mặt ở bảng gương."""

    source_page_id: str
    candidate_name: str
    file_url: str | None
    """Link CV ở cột "Resume, CL"; None nếu ứng viên chưa đính file."""

    properties: dict[str, Any] = field(default_factory=dict)
    """Nguyên `page["properties"]` của dòng nguồn, để chép sang bảng gương."""

    created_time: str | None = None


class ApplicationSource(ABC):
    @abstractmethod
    async def list_pending(self, limit: int | None = None) -> list[PendingApplication]:
        """Đơn ở bảng nguồn, trừ đi những đơn đã có mặt ở bảng gương.

        Là phép TRỪ TẬP HỢP chứ không phải mốc thời gian: chạy lại bao nhiêu lần
        cũng ra đúng, đơn lỗi hôm trước tự được nhặt lại, CV về muộn cũng không sót.
        """

    @abstractmethod
    async def count_pending(self) -> int:
        """Đếm nhanh để hiển thị, không tải toàn bộ chi tiết."""
