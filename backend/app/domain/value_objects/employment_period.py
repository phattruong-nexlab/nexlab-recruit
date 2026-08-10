"""Value object: khoảng thời gian làm việc tại một công ty."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.exceptions import InvalidEmploymentPeriodError

MIN_YEAR = 1950
MAX_YEAR = 2100


@dataclass(frozen=True, slots=True)
class EmploymentPeriod:
    """start_year/end_year có thể None khi CV ghi mơ hồ — không đoán bừa.

    `is_current=True` nghĩa là đang làm việc, khi đó `end_year` phải là None.
    """

    start_year: int | None = None
    end_year: int | None = None
    is_current: bool = False

    def __post_init__(self) -> None:
        for label, year in (("start_year", self.start_year), ("end_year", self.end_year)):
            if year is not None and not MIN_YEAR <= year <= MAX_YEAR:
                raise InvalidEmploymentPeriodError(
                    f"{label}={year} nằm ngoài khoảng [{MIN_YEAR}, {MAX_YEAR}]"
                )

        if self.is_current and self.end_year is not None:
            raise InvalidEmploymentPeriodError("Đang làm việc thì end_year phải là None")

        if (
            self.start_year is not None
            and self.end_year is not None
            and self.end_year < self.start_year
        ):
            raise InvalidEmploymentPeriodError(
                f"end_year={self.end_year} nhỏ hơn start_year={self.start_year}"
            )

    @property
    def duration_years(self) -> int | None:
        """Số năm làm việc; None khi thiếu dữ liệu để tính."""
        if self.start_year is None or self.end_year is None:
            return None
        return self.end_year - self.start_year
