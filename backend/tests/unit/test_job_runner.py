"""Cloud Run Admin API từ chối POST không có body (411 Length Required)."""

from __future__ import annotations

from typing import Any

from app.infrastructure.gcp.job_runner import CloudRunJobRunner


class RecordingApi:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.calls.append({"method": method, "url": url, "json": json})
        return {"metadata": {"name": "executions/abc"}}


async def test_kich_hoat_job_gui_body_rong() -> None:
    """json={} để httpx đặt Content-Length; thiếu nó Google trả 411."""
    runner = CloudRunJobRunner("p", "r", "j")
    api = RecordingApi()
    runner._api = api  # type: ignore[assignment]

    name = await runner.start()

    assert name == "executions/abc"
    assert api.calls[0]["method"] == "POST"
    assert api.calls[0]["json"] == {}


def test_chua_cau_hinh_thi_bao_configured_false() -> None:
    assert CloudRunJobRunner("", "r", "j").configured is False
    assert CloudRunJobRunner("p", "r", "j").configured is True
