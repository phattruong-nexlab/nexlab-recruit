"""Entrypoint: web service phục vụ trang quản trị cho HR.

Chạy local:      uv run python main.py
Trên Cloud Run:  uvicorn main:app --host 0.0.0.0 --port $PORT

Đường dẫn:
    GET  /admin   trang HR bấm nút quét CV (đăng nhập bằng ADMIN_PASSWORD)
    GET  /health  health check cho Cloud Run probe

Việc nặng KHÔNG chạy ở đây: nút bấm chỉ kích hoạt Cloud Run Job rồi hỏi tiến độ.
"""

from __future__ import annotations

import logging

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.routing import Route

from app.interface.web.admin import admin_routes
from config import get_settings

logger = logging.getLogger(__name__)


def create_app() -> Starlette:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    async def health(_: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "environment": settings.environment})

    async def root(_: Request) -> Response:
        return RedirectResponse("/admin", status_code=303)

    app = Starlette(
        routes=[
            Route("/", root, methods=["GET"]),
            Route("/health", health, methods=["GET"]),
            *admin_routes(),
        ]
    )

    if not settings.admin_password:
        logger.warning(
            "ADMIN_PASSWORD trống — trang quản trị đang MỞ. Chỉ chấp nhận được khi chạy local."
        )

    logger.info("Service %s sẵn sàng", settings.app_name)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
