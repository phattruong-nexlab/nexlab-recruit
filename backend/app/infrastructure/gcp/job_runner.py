"""Adapter: kích hoạt và theo dõi Cloud Run Job qua Admin API v2.

Xác thực bằng chính ADC của service (service account gắn vào Cloud Run), không
cần key. Service cần quyền `run.jobs.run` và `run.executions.get`.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import google.auth
import google.auth.transport.requests
import httpx

from app.domain.exceptions import DomainError

logger = logging.getLogger(__name__)

_API = "https://run.googleapis.com/v2"
_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


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
        self._credentials: Any = None

    @property
    def configured(self) -> bool:
        return bool(self._project and self._region and self._job)

    async def start(self) -> str:
        """Kích hoạt job, trả về tên execution để theo dõi."""
        url = f"{_API}/projects/{self._project}/locations/{self._region}/jobs/{self._job}:run"
        payload = await self._request("POST", url)
        # Long-running operation: tên execution nằm trong metadata.
        name = (payload.get("metadata") or {}).get("name") or payload.get("name", "")
        logger.info("Đã kích hoạt job %s -> %s", self._job, name)
        return str(name)

    async def status(self, execution_name: str) -> ExecutionStatus:
        payload = await self._request("GET", f"{_API}/{execution_name}")
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

    async def _request(self, method: str, url: str) -> dict[str, Any]:
        token = await asyncio.to_thread(self._access_token)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method, url, headers={"Authorization": f"Bearer {token}"}
                )
                response.raise_for_status()
                return dict(response.json())
        except httpx.HTTPStatusError as exc:
            raise DomainError(
                f"Cloud Run API trả {exc.response.status_code}: {exc.response.text[:200]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise DomainError(f"Không gọi được Cloud Run API: {exc}") from exc

    def _access_token(self) -> str:
        if self._credentials is None:
            self._credentials, _ = google.auth.default(scopes=[_SCOPE])
        if not self._credentials.valid:
            self._credentials.refresh(google.auth.transport.requests.Request())
        return str(self._credentials.token)
