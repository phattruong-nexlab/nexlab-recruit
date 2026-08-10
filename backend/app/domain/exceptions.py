"""Exception của tầng domain — không phụ thuộc MCP, HTTP hay SDK nào."""

from __future__ import annotations


class DomainError(Exception):
    """Gốc của mọi lỗi nghiệp vụ."""


class InvalidEmploymentPeriodError(DomainError):
    """Khoảng thời gian làm việc không hợp lệ (năm âm, kết thúc trước bắt đầu...)."""


class CvDownloadError(DomainError):
    """Không tải được file CV từ URL agent gửi sang."""


class CvParsingError(DomainError):
    """Không đọc được nội dung text từ file CV."""


class CvExtractionError(DomainError):
    """LLM không trả về cấu trúc hợp lệ."""


class CandidatePublishError(DomainError):
    """Không ghi được ứng viên lên Notion."""
