"""Entity: một kinh nghiệm làm việc của ứng viên."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.value_objects.employment_period import EmploymentPeriod


@dataclass(slots=True)
class Experience:
    company: str
    position: str = ""
    period: EmploymentPeriod = field(default_factory=EmploymentPeriod)
    description: str = ""
    order_index: int = 0

    @property
    def start_year(self) -> int | None:
        return self.period.start_year

    @property
    def end_year(self) -> int | None:
        return self.period.end_year

    @property
    def is_current(self) -> bool:
        return self.period.is_current

    def as_line(self) -> str:
        """Một dòng tóm tắt để ghi vào ô text của Notion."""
        start = self.start_year or "?"
        end = "hiện tại" if self.is_current else (self.end_year or "?")
        head = f"{self.position} — {self.company}" if self.position else self.company
        return f"{head} ({start} – {end})"
