"""Port: đọc danh sách đơn ứng tuyển cần trích nội dung CV."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import timedelta, timezone
from typing import Any

# Việt Nam không có giờ mùa hè nên offset cố định +07:00 là chính xác tuyệt đối,
# và tránh phụ thuộc gói tzdata (Windows không có sẵn cơ sở dữ liệu múi giờ IANA).
VN_TZ = timezone(timedelta(hours=7))
VN_OFFSET = "+07:00"


@dataclass(slots=True)
class PendingFilter:
    """Thu hẹp phạm vi một lượt chạy. Cả hai để trống = làm tất cả những gì còn thiếu."""

    since: str | None = None
    """Chỉ lấy đơn nộp từ ngày này trở đi, dạng YYYY-MM-DD — hiểu theo GIỜ VIỆT NAM."""

    job_url_contains: str | None = None
    """Chỉ lấy đơn có Job URL chứa chuỗi này, ví dụ 'junior-frontend'."""

    @property
    def is_empty(self) -> bool:
        return not self.since and not self.job_url_contains

    @property
    def since_for_notion(self) -> str | None:
        """Mốc thời gian gửi cho Notion, kèm offset giờ Việt Nam.

        Notion lưu `Created time` theo UTC. Gửi chuỗi ngày trần thì Notion hiểu là
        00:00 UTC — tức 07:00 sáng giờ VN — nên đơn nộp trong khoảng 00:00–07:00
        sáng hôm đó bị bỏ sót. Gắn offset để mốc đúng nửa đêm giờ VN.
        """
        if not self.since:
            return None
        # Người dùng có thể tự nhập mốc đầy đủ; khi đó tôn trọng nguyên văn.
        if "T" in self.since:
            return self.since
        return f"{self.since}T00:00:00{VN_OFFSET}"

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
