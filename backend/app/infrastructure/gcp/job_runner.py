"""Adapter: kích hoạt và theo dõi Cloud Run Job qua Admin API v2.

Xác thực bằng chính ADC của service (service account gắn vào Cloud Run), không
cần key. Service cần quyền `run.jobs.run` và `run.executions.get`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.infrastructure.gcp.credentials import GoogleApiClient

logger = logging.getLogger(__name__)

_API = "https://run.googleapis.com/v2"


@dataclass(slots=True)
class ExecutionStatus:
    name: str
    running: bool
    succeeded: int
    failed: int
    finished: bool

    @property
    def label(self) -> str:
        if self.running:
            return "Đang chạy"
        if not self.finished:
            return "Đang khởi động"
        return "Xong" if self.failed == 0 else "Có lỗi"


class CloudRunJobRunner:
    def __init__(self, project_id: str, region: str, job_name: str) -> None:
        self._project = project_id
        self._region = region
        self._job = job_name
        self._api = GoogleApiClient()

    @property
    def configured(self) -> bool:
        return bool(self._project and self._region and self._job)

    async def start(self, args: list[str] | None = None) -> str:
        """Kích hoạt job, trả về tên execution để theo dõi.

        `args` ghi đè tham số dòng lệnh của container cho riêng lần chạy này —
        nhờ vậy HR chọn ngày và job trên web mà không phải sửa cấu hình job.
        """
        url = f"{_API}/projects/{self._project}/locations/{self._region}/jobs/{self._job}:run"

        # Body rỗng là bắt buộc: POST không có body thì httpx bỏ Content-Length,
        # và Google trả 411 Length Required.
        body: dict[str, Any] = {}
        if args:
            body = {"overrides": {"containerOverrides": [{"args": args}]}}

        payload = await self._api.request("POST", url, json=body)
        # Long-running operation: tên execution nằm trong metadata.
        name = (payload.get("metadata") or {}).get("name") or payload.get("name", "")
        logger.info("Đã kích hoạt job %s -> %s", self._job, name)
        return str(name)

    async def status(self, execution_name: str) -> ExecutionStatus:
        payload = await self._api.request("GET", f"{_API}/{execution_name}")
        conditions = payload.get("conditions") or []
        completed = any(
            c.get("type") == "Completed" and c.get("state") == "CONDITION_SUCCEEDED"
            for c in conditions
        )
        return ExecutionStatus(
            name=execution_name,
            running=int(payload.get("runningCount", 0)) > 0,
            succeeded=int(payload.get("succeededCount", 0)),
            failed=int(payload.get("failedCount", 0)),
            finished=completed or bool(payload.get("completionTime")),
        )
