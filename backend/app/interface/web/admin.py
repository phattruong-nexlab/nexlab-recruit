"""Trang quản trị cho HR: xem còn bao nhiêu CV chưa xử lý và bấm chạy.

Cố ý render HTML thẳng từ server, không dựng thêm ứng dụng frontend — cả trang
chỉ có một nút bấm và một dòng trạng thái.

Xác thực bằng mật khẩu dùng chung (ADMIN_PASSWORD), lưu trong cookie có ký.
HR không cần tài khoản riêng; đường vào là một link đặt sẵn trong Notion.
"""

from __future__ import annotations

import hmac
import logging
from typing import Any

from itsdangerous import BadSignature, URLSafeSerializer
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Route

from app.domain.exceptions import DomainError
from app.infrastructure.gcp.job_runner import CloudRunJobRunner
from app.infrastructure.gcp.scheduler import CloudSchedulerClient
from app.interface.dependencies import get_mirror_use_case
from app.interface.web.templates import render_login, render_page
from config import get_settings

logger = logging.getLogger(__name__)

_COOKIE = "nexlab_admin"


def _serializer() -> URLSafeSerializer:
    settings = get_settings()
    # Dùng chính mật khẩu làm khoá ký: đổi mật khẩu là mọi phiên cũ hết hiệu lực.
    return URLSafeSerializer(settings.admin_password or "insecure-dev-key", salt="admin")


def _is_signed_in(request: Request) -> bool:
    settings = get_settings()
    if not settings.admin_password:
        return True  # chưa đặt mật khẩu (chạy local) thì không chặn

    cookie = request.cookies.get(_COOKIE)
    if not cookie:
        return False
    try:
        return bool(_serializer().loads(cookie) == "ok")
    except BadSignature:
        return False


async def login_page(request: Request) -> Response:
    if _is_signed_in(request):
        return RedirectResponse("/admin", status_code=303)
    return HTMLResponse(render_login())


async def login_submit(request: Request) -> Response:
    form = await request.form()
    password = str(form.get("password") or "")
    settings = get_settings()

    if not hmac.compare_digest(password, settings.admin_password):
        logger.warning("Đăng nhập trang quản trị thất bại")
        return HTMLResponse(render_login(error="Mật khẩu không đúng."), status_code=401)

    response = RedirectResponse("/admin", status_code=303)
    response.set_cookie(
        _COOKIE,
        _serializer().dumps("ok"),
        httponly=True,
        secure=settings.environment != "local",
        samesite="lax",
        max_age=8 * 60 * 60,
    )
    return response


async def dashboard(request: Request) -> Response:
    if not _is_signed_in(request):
        return RedirectResponse("/admin/login", status_code=303)
    return HTMLResponse(render_page())


async def pending_count(request: Request) -> Response:
    if not _is_signed_in(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    try:
        pending = await get_mirror_use_case().count_pending()
    except DomainError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    return JSONResponse({"pending": pending})


async def start_run(request: Request) -> Response:
    if not _is_signed_in(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    runner = _runner()
    if not runner.configured:
        return JSONResponse(
            {"error": "Chưa cấu hình CLOUD_RUN_JOB_NAME / GCP_PROJECT_ID / GCP_REGION."},
            status_code=503,
        )

    try:
        execution = await runner.start()
    except DomainError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    return JSONResponse({"execution": execution})


async def run_status(request: Request) -> Response:
    if not _is_signed_in(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    execution = request.query_params.get("execution", "")
    if not execution:
        return JSONResponse({"error": "thiếu tham số execution"}, status_code=400)

    try:
        status = await _runner().status(execution)
    except DomainError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)

    return JSONResponse(
        {
            "label": status.label,
            "running": status.running,
            "finished": status.finished,
            "succeeded": status.succeeded,
            "failed": status.failed,
        }
    )


async def get_schedule(request: Request) -> Response:
    if not _is_signed_in(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    scheduler = _scheduler()
    if not scheduler.configured:
        return JSONResponse({"configured": False})

    try:
        schedule = await scheduler.get()
    except DomainError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)

    return JSONResponse(
        {
            "configured": True,
            "time": schedule.time_of_day,
            "cron": schedule.cron,
            "timezone": schedule.timezone,
            "enabled": schedule.enabled,
        }
    )


async def set_schedule(request: Request) -> Response:
    """HR chọn giờ dạng HH:MM; cron do server dựng, HR không phải biết cú pháp."""
    if not _is_signed_in(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    scheduler = _scheduler()
    if not scheduler.configured:
        return JSONResponse({"error": "Chưa cấu hình CLOUD_SCHEDULER_JOB_NAME."}, status_code=503)

    body = await request.json()
    time_of_day = str(body.get("time", ""))

    try:
        schedule = await scheduler.set_time_of_day(time_of_day)
    except DomainError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

    return JSONResponse({"time": schedule.time_of_day, "cron": schedule.cron})


def _scheduler() -> CloudSchedulerClient:
    settings = get_settings()
    return CloudSchedulerClient(
        project_id=settings.gcp_project_id,
        region=settings.gcp_region,
        job_name=settings.cloud_scheduler_job_name,
    )


def _runner() -> CloudRunJobRunner:
    settings = get_settings()
    return CloudRunJobRunner(
        project_id=settings.gcp_project_id,
        region=settings.gcp_region,
        job_name=settings.cloud_run_job_name,
    )


def admin_routes() -> list[Any]:
    return [
        Route("/admin", dashboard, methods=["GET"]),
        Route("/admin/login", login_page, methods=["GET"]),
        Route("/admin/login", login_submit, methods=["POST"]),
        Route("/admin/pending", pending_count, methods=["GET"]),
        Route("/admin/run", start_run, methods=["POST"]),
        Route("/admin/status", run_status, methods=["GET"]),
        Route("/admin/schedule", get_schedule, methods=["GET"]),
        Route("/admin/schedule", set_schedule, methods=["POST"]),
    ]
