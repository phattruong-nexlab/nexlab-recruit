"""Entrypoint cho Cloud Run Job: trích nội dung CV vào cột Resume Content.

    python -m app.interface.jobs.extract_content [--limit N]

Job chạy tới khi xong rồi tắt — không có endpoint HTTP, không cần token, và
`file_url` lấy thẳng từ Notion nên không có bề mặt SSRF như đường MCP.

Exit code: 0 = xong sạch, 1 = có ít nhất một CV lỗi (Cloud Run Job sẽ retry).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timedelta

from app.application.ports.application_source import VN_TZ, PendingFilter
from app.interface.dependencies import get_extract_use_case
from config import get_settings

logger = logging.getLogger("extract_content")


async def run(limit: int | None, pending_filter: PendingFilter) -> int:
    summary = await get_extract_use_case().execute(limit=limit, pending_filter=pending_filter)

    logger.info(
        "KẾT QUẢ: %d/%d thành công, %d lỗi",
        summary.succeeded,
        summary.total,
        summary.failed,
    )
    for failure in summary.failures:
        logger.error("  %s: %s", failure.candidate_name, failure.reason)

    return 0 if summary.all_ok else 1


def _force_utf8_console() -> None:
    """Console Windows mặc định cp1252, in tiếng Việt sẽ UnicodeEncodeError."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    _force_utf8_console()

    parser = argparse.ArgumentParser(description="Đọc CV rồi ghi text vào cột Resume Content.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Chỉ xử lý N CV đầu — dùng để thử trước khi chạy cả lượt",
    )
    parser.add_argument(
        "--since",
        default=None,
        metavar="YYYY-MM-DD",
        help="Chỉ xử lý đơn nộp từ ngày này trở đi",
    )
    parser.add_argument(
        "--since-days",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Cửa sổ trượt: chỉ xử lý đơn trong N ngày gần nhất. Dùng cho lượt chạy "
            "tự động — đủ rộng để bù khi lỡ vài đêm, nhưng không đụng tồn đọng cũ."
        ),
    )
    parser.add_argument(
        "--job",
        default=None,
        metavar="SLUG",
        help="Chỉ xử lý đơn có Job URL chứa chuỗi này, ví dụ junior-frontend",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(levelname)s %(message)s")

    since = args.since
    if since is None and args.since_days is not None:
        # Tính tại thời điểm chạy, không phải lúc cấu hình — nhờ vậy cửa sổ luôn trượt.
        # Đếm ngày theo GIỜ VIỆT NAM để khớp với cách HR hiểu "N ngày gần nhất".
        since = (datetime.now(VN_TZ) - timedelta(days=args.since_days)).date().isoformat()
        logger.info("Cửa sổ %d ngày gần nhất -> từ %s", args.since_days, since)

    pending_filter = PendingFilter(since=since, job_url_contains=args.job)
    logger.info("Phạm vi: %s", pending_filter.describe())
    return asyncio.run(run(args.limit, pending_filter))


if __name__ == "__main__":
    sys.exit(main())
