"""Lấy access token của Google từ Application Default Credentials.

Trên Cloud Run là service account gắn vào service; ở máy local là
`gcloud auth application-default login`. Không dùng key JSON.
"""

from __future__ import annotations

import asyncio
from typing import Any

import google.auth
import google.auth.transport.requests
import httpx

from app.domain.exceptions import DomainError

_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


class GoogleApiClient:
    """Gọi REST API của Google, tự làm mới token khi hết hạn."""

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self._timeout = timeout_seconds
        self._credentials: Any = None

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        token = await asyncio.to_thread(self._access_token)
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    headers={"Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()
                return dict(response.json())
        except httpx.HTTPStatusError as exc:
            raise DomainError(
                f"Google API trả {exc.response.status_code}: {exc.response.text[:200]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise DomainError(f"Không gọi được Google API: {exc}") from exc

    def _access_token(self) -> str:
        if self._credentials is None:
            self._credentials, _ = google.auth.default(scopes=[_SCOPE])
        if not self._credentials.valid:
            self._credentials.refresh(google.auth.transport.requests.Request())
        return str(self._credentials.token)
