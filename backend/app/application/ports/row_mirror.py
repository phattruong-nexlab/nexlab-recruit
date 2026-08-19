"""Port: nhân bản một dòng đơn ứng tuyển sang bảng gương."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.application.ports.application_source import PendingApplication
from app.application.ports.cv_downloader import DownloadedFile


class RowMirror(ABC):
    @abstractmethod
    async def mirror(self, application: PendingApplication, cv: DownloadedFile | None) -> str:
        """Tạo dòng mới ở bảng gương, trả về page id.

        `cv` là file đã tải về; None nghĩa là dòng nguồn chưa đính CV — vẫn chép
        các cột còn lại, lượt sau CV về thì sẽ chép lại.

        Raises:
            CandidatePublishError: không ghi được.
        """
