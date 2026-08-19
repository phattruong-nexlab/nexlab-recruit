"""DTO vào/ra của tool MCP `parse_cv`."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ParseCvCommand:
    """Đúng những gì agent Notion lấy được từ đơn ứng tuyển mới."""

    file_url: str
    job_url: str | None = None
    email: str | None = None
    phone: str | None = None
    created_time: str | None = None
    source_page_id: str | None = None
    """page_id của dòng nguồn — khoá để đối chiếu đã xử lý hay chưa."""


@dataclass(slots=True)
class ExtractedExperience:
    company: str
    position: str = ""
    start_year: int | None = None
    end_year: int | None = None
    is_current: bool = False
    description: str = ""


@dataclass(slots=True)
class ExtractedCv:
    """Khớp đúng JSON schema ép Gemini trả về."""

    full_name: str | None = None
    university: str | None = None
    gpa: float | None = None
    experiences: list[ExtractedExperience] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    certificates: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ParseCvResult:
    """Kết quả trả về cho agent.

    `published=False` nghĩa là đã phân tích xong nhưng ghi Notion lỗi — agent có
    thể gọi lại, hoặc tự ghi bằng dữ liệu trong `candidate`.
    """

    full_name: str | None
    applied_job: str | None
    university: str | None
    gpa: float | None
    experiences: list[ExtractedExperience]
    skills: list[str]
    certificates: list[str]
    languages: list[str]
    total_experience_years: int
    notion_page_id: str | None = None
    published: bool = False
    publish_error: str | None = None
