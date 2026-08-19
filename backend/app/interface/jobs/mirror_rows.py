"""Entrypoint cho Cloud Run Job: nhân bản đơn ứng tuyển sang bảng gương.

    python -m app.interface.jobs.mirror_rows [--limit N]

Job chạy tới khi xong rồi tắt — không có endpoint HTTP, không cần token, và
`file_url` lấy thẳng từ Notion nên không có bề mặt SSRF như đường MCP.

Exit code: 0 = xong sạch, 1 = có ít nhất một CV lỗi (Cloud Run Job sẽ retry).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from app.interface.dependencies import get_mirror_use_case
from config import get_settings

logger = logging.getLogger("mirror_rows")


async def run(limit: int | None) -> int:
    summary = await get_mirror_use_case().execute(limit=limit)

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
    parser = argparse.ArgumentParser(description="Nhân bản đơn ứng tuyển sang bảng gương Notion.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Chỉ nhân bản N dòng đầu — dùng để thử trước khi chạy cả lượt",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(levelname)s %(message)s")

    return asyncio.run(run(args.limit))


if __name__ == "__main__":
    sys.exit(main())
