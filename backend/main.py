"""Entrypoint: MCP server chạy trên Streamable HTTP.

Chạy local:  uv run python main.py
Trên Cloud Run:  uvicorn main:app --host 0.0.0.0 --port $PORT

Endpoint:
    POST /mcp     giao thức MCP (cần header Authorization: Bearer <MCP_AUTH_TOKEN>)
    GET  /health  health check cho Cloud Run probe (không cần token)
"""

from __future__ import annotations

import logging

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from app.interface.mcp.auth import BearerTokenMiddleware
from app.interface.mcp.server import create_mcp_server
from config import get_settings

logger = logging.getLogger(__name__)


def create_app() -> Starlette:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    mcp_server = create_mcp_server(name=settings.app_name)

    # stateless_http=True: mỗi request tự chứa đủ ngữ cảnh, không giữ session giữa
    # các lần gọi — hợp Cloud Run vì instance có thể bị thu hồi bất cứ lúc nào.
    mcp_app = mcp_server.streamable_http_app(
        streamable_http_path="/",
        stateless_http=True,
        json_response=True,
        host="0.0.0.0",
    )

    async def health(_: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "environment": settings.environment})

    app = Starlette(
        routes=[
            Route("/health", health, methods=["GET"]),
            Mount(settings.mcp_path, app=mcp_app),
        ],
        lifespan=mcp_app.router.lifespan_context,
    )

    if settings.auth_enabled:
        app.add_middleware(BearerTokenMiddleware, token=settings.mcp_auth_token)
    else:
        logger.warning(
            "MCP_AUTH_TOKEN trống — endpoint đang MỞ. Chỉ chấp nhận được khi chạy local."
        )

    logger.info("MCP server %s sẵn sàng tại %s", settings.app_name, settings.mcp_path)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
