"""Bearer token tĩnh bảo vệ endpoint MCP.

Endpoint chạy public trên Cloud Run nên không có lớp này thì ai biết URL cũng gọi
được và đốt quota Gemini.
"""

from __future__ import annotations

import hmac
import logging

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)

# Health check phải mở để Cloud Run probe được.
_PUBLIC_PATHS = frozenset({"/health", "/healthz"})


class BearerTokenMiddleware:
    """So sánh token bằng compare_digest để tránh rò rỉ qua thời gian phản hồi."""

    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self._token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        if request.url.path in _PUBLIC_PATHS:
            await self.app(scope, receive, send)
            return

        if not self._is_authorized(request.headers.get("authorization")):
            logger.warning("Từ chối request thiếu/sai token tới %s", request.url.path)
            response = JSONResponse(
                {"error": "unauthorized", "detail": "Thiếu hoặc sai Bearer token."},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

    def _is_authorized(self, header: str | None) -> bool:
        if not header:
            return False
        scheme, _, value = header.partition(" ")
        if scheme.lower() != "bearer":
            return False
        return hmac.compare_digest(value.strip(), self._token)
