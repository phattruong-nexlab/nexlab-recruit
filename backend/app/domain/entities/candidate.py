"""Aggregate root: ứng viên sau khi trích xuất từ CV.

Gộp hai nguồn dữ liệu:
- Do agent gửi kèm (chính xác, không suy đoán): email, phone, job_url, created_time
- Do LLM đọc từ CV: university, gpa, experiences, skills, certificates, languages
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.entities.experience import Experience
from app.domain.value_objects.skill_set import SkillSet


@dataclass(slots=True)
class Candidate:
    full_name: str | None = None
    applied_job: str | None = None
    university: str | None = None
    gpa: float | None = None
    experiences: list[Experience] = field(default_factory=list)
    skills: SkillSet = field(default_factory=SkillSet)
    certificates: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)

    # Thông tin agent gửi kèm — không do LLM suy ra.
    email: str | None = None
    phone: str | None = None
    job_url: str | None = None
    applied_at: str | None = None
    source_file_url: str | None = None

    def reindex_experiences(self) -> None:
        """Đánh lại order_index theo đúng thứ tự xuất hiện trong CV."""
        for index, experience in enumerate(self.experiences):
            experience.order_index = index

    @property
    def total_experience_years(self) -> int:
        """Tổng số năm tính được; job thiếu năm bị bỏ qua (không đoán)."""
        return sum(
            duration
            for exp in self.experiences
            if (duration := exp.period.duration_years) is not None
        )

    def experiences_as_text(self) -> str:
        """Gộp nhiều job thành một khối text cho ô rich_text của Notion."""
        lines: list[str] = []
        for exp in self.experiences:
            lines.append(f"• {exp.as_line()}")
            if exp.description:
                lines.append(f"  {exp.description}")
        return "\n".join(lines)
