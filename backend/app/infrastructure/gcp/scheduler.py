"""Adapter: đọc và đổi giờ chạy tự động của Cloud Scheduler.

HR chọn giờ trên trang quản trị, không phải gõ cron — module này dịch qua lại
giữa "02:00" và biểu thức cron `0 2 * * *`.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.domain.exceptions import DomainError
from app.infrastructure.gcp.credentials import GoogleApiClient

logger = logging.getLogger(__name__)

_API = "https://cloudscheduler.googleapis.com/v1"

# Chỉ nhận cron dạng "phút giờ * * *" — đủ cho "chạy mỗi ngày lúc HH:MM".
_DAILY_CRON = re.compile(r"^(\d{1,2})\s+(\d{1,2})\s+\*\s+\*\s+\*$")


@dataclass(slots=True)
class Schedule:
    cron: str
    timezone: str
    enabled: bool

    @property
    def time_of_day(self) -> str | None:
        """ "0 2 * * *" -> "02:00". None nếu cron phức tạp hơn dạng hằng ngày."""
        match = _DAILY_CRON.match(self.cron.strip())
        if match is None:
            return None
        minute, hour = int(match.group(1)), int(match.group(2))
        return f"{hour:02d}:{minute:02d}"


def to_daily_cron(time_of_day: str) -> str:
    """ "02:00" -> "0 2 * * *". Raises DomainError nếu giờ không hợp lệ."""
    parts = time_of_day.strip().split(":")
    if len(parts) != 2:
        raise DomainError(f"Giờ phải dạng HH:MM, nhận được {time_of_day!r}")

    try:
        hour, minute = int(parts[0]), int(parts[1])
    except ValueError as exc:
        raise DomainError(f"Giờ phải là số, nhận được {time_of_day!r}") from exc

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise DomainError(f"Giờ ngoài khoảng hợp lệ: {time_of_day!r}")

    return f"{minute} {hour} * * *"


class CloudSchedulerClient:
    def __init__(self, project_id: str, region: str, job_name: str) -> None:
        self._project = project_id
        self._region = region
        self._job = job_name
        self._api = GoogleApiClient()

    @property
    def configured(self) -> bool:
        return bool(self._project and self._region and self._job)

    @property
    def _url(self) -> str:
        return f"{_API}/projects/{self._project}/locations/{self._region}/jobs/{self._job}"

    async def get(self) -> Schedule:
        payload = await self._api.request("GET", self._url)
        return Schedule(
            cron=str(payload.get("schedule", "")),
            timezone=str(payload.get("timeZone", "")),
            enabled=payload.get("state") == "ENABLED",
        )

    async def set_time_of_day(self, time_of_day: str) -> Schedule:
        """Đổi giờ chạy hằng ngày. Giữ nguyên múi giờ đang cấu hình."""
        cron = to_daily_cron(time_of_day)
        payload = await self._api.request(
            "PATCH",
            self._url,
            params={"updateMask": "schedule"},
            json={"schedule": cron},
        )
        logger.info("Đã đổi lịch chạy sang %s (%s)", time_of_day, cron)
        return Schedule(
            cron=str(payload.get("schedule", cron)),
            timezone=str(payload.get("timeZone", "")),
            enabled=payload.get("state") == "ENABLED",
        )
