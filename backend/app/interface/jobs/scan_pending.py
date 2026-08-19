"""Entrypoint cho Cloud Run Job: quét mọi đơn ứng tuyển chưa xử lý.

    python -m app.interface.jobs.scan_pending [--limit N]

Job chạy tới khi xong rồi tắt — không có endpoint HTTP, không cần token, và
`file_url` lấy thẳng từ Notion nên không có bề mặt SSRF như đường MCP.

Exit code: 0 = xong sạch, 1 = có ít nhất một CV lỗi (Cloud Run Job sẽ retry).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from app.interface.dependencies import get_scan_pending_use_case
from config import get_settings

logger = logging.getLogger("scan_pending")


async def run(limit: int | None) -> int:
    summary = await get_scan_pending_use_case().execute(limit=limit)

    logger.info(
        "KẾT QUẢ: %d/%d thành công, %d lỗi",
        summary.succeeded,
        summary.total,
        summary.failed,
    )
    for failure in summary.failures:
        logger.error("  %s: %s", failure.candidate_name, failure.reason)

    return 0 if summary.all_ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Quét CV chưa xử lý và ghi vào Notion.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Chỉ xử lý N đơn đầu — dùng để thử trước khi chạy cả lượt",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(levelname)s %(message)s")

    return asyncio.run(run(args.limit))


if __name__ == "__main__":
    sys.exit(main())
