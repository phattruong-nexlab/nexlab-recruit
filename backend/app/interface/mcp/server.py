"""MCP server: expose tool `parse_cv` cho agent Notion gọi.

Tầng này chỉ dịch giữa MCP và use case — không chứa nghiệp vụ, không gọi SDK.
"""

from __future__ import annotations

import logging
from dataclasses import asdict

from mcp.server import MCPServer
from pydantic import BaseModel, Field

from app.application.dto.parse_cv import ParseCvCommand
from app.domain.exceptions import DomainError
from app.interface.mcp.dependencies import get_parse_cv_use_case

logger = logging.getLogger(__name__)

_INSTRUCTIONS = """\
Dịch vụ phân tích CV của Nexlab.

Gọi `parse_cv` với link file CV lấy từ cột "Resume, CL" của đơn ứng tuyển, kèm
Job URL, Email, Phone và Created time nếu có. Tool trả về thông tin đã trích xuất
và tự ghi một dòng mới vào bảng Notion đích.
"""


class ExperienceOut(BaseModel):
    company: str = Field(description="Tên công ty")
    position: str = Field(default="", description="Chức danh")
    start_year: int | None = Field(default=None, description="Năm bắt đầu, null nếu không rõ")
    end_year: int | None = Field(default=None, description="Năm kết thúc, null nếu đang làm")
    is_current: bool = Field(default=False, description="Đang làm việc tại đây")
    description: str = Field(default="", description="Mô tả công việc")


class ParseCvOut(BaseModel):
    """Kết quả phân tích CV."""

    full_name: str | None = Field(default=None, description="Họ tên ứng viên")
    applied_job: str | None = Field(default=None, description="Vị trí ứng tuyển, suy từ Job URL")
    university: str | None = Field(default=None, description="Trường đại học")
    gpa: float | None = Field(default=None, description="Điểm trung bình")
    experiences: list[ExperienceOut] = Field(default_factory=list, description="Kinh nghiệm")
    skills: list[str] = Field(default_factory=list, description="Kỹ năng")
    certificates: list[str] = Field(default_factory=list, description="Chứng chỉ")
    languages: list[str] = Field(default_factory=list, description="Ngôn ngữ giao tiếp")
    total_experience_years: int = Field(default=0, description="Tổng số năm kinh nghiệm")
    notion_page_id: str | None = Field(default=None, description="Id dòng vừa tạo trên Notion")
    published: bool = Field(default=False, description="Đã ghi được vào Notion hay chưa")
    publish_error: str | None = Field(default=None, description="Lý do ghi Notion thất bại")


def create_mcp_server(name: str = "nexlab-scan-cv", version: str = "0.1.0") -> MCPServer:
    server: MCPServer = MCPServer(
        name=name,
        title="Nexlab Scan CV",
        version=version,
        instructions=_INSTRUCTIONS,
    )

    @server.tool(  # type: ignore[untyped-decorator]
        name="parse_cv",
        title="Phân tích CV ứng viên",
        description=(
            "Tải CV từ file_url, đọc nội dung và trích xuất thông tin ứng viên "
            "(trường đại học, GPA, kinh nghiệm, kỹ năng, chứng chỉ, ngôn ngữ), "
            "rồi ghi một dòng mới vào bảng Notion đích."
        ),
    )
    async def parse_cv(
        file_url: str,
        job_url: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        created_time: str | None = None,
    ) -> ParseCvOut:
        """Phân tích CV của một đơn ứng tuyển.

        Args:
            file_url: Link file CV (cột "Resume, CL"). Link Notion hết hạn sau ~1 giờ.
            job_url: Link tin tuyển dụng (cột "Job URL") — dùng để suy ra vị trí ứng tuyển.
            email: Email ứng viên đã khai trong đơn.
            phone: Số điện thoại ứng viên đã khai trong đơn.
            created_time: Thời điểm nộp đơn, dạng ISO 8601.
        """
        logger.info("parse_cv: %s (job=%s)", file_url[:80], job_url)

        use_case = get_parse_cv_use_case()
        try:
            result = await use_case.execute(
                ParseCvCommand(
                    file_url=file_url,
                    job_url=job_url,
                    email=email,
                    phone=phone,
                    created_time=created_time,
                )
            )
        except DomainError as exc:
            # Trả lỗi có nghĩa để agent biết nên thử lại hay bỏ qua.
            logger.warning("parse_cv thất bại: %s: %s", type(exc).__name__, exc)
            raise ValueError(f"{type(exc).__name__}: {exc}") from exc

        return ParseCvOut(
            full_name=result.full_name,
            applied_job=result.applied_job,
            university=result.university,
            gpa=result.gpa,
            experiences=[ExperienceOut(**asdict(item)) for item in result.experiences],
            skills=result.skills,
            certificates=result.certificates,
            languages=result.languages,
            total_experience_years=result.total_experience_years,
            notion_page_id=result.notion_page_id,
            published=result.published,
            publish_error=result.publish_error,
        )

    return server
