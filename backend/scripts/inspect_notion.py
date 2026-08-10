"""Xem integration nhìn thấy gì trên Notion — chạy trước khi tải file.

Dùng để trả lời: database nào chứa CV, property nào là 'Files & media'.

    # liệt kê mọi database integration được share
    uv run python -m scripts.inspect_notion

    # xem schema + vài dòng mẫu của một database
    uv run python -m scripts.inspect_notion --database-id <URL hoặc id>
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Any

from notion_client import Client
from notion_client.errors import APIResponseError

from config import get_settings
from scripts.download_notion_files import (
    _plain_text,
    force_utf8_console,
    normalize_notion_id,
    page_title,
    resolve_data_sources,
)

logger = logging.getLogger("inspect_notion")


def list_databases(client: Client) -> None:
    """Search API chỉ trả về thứ đã được share cho integration.

    API 2025-09-03 bỏ giá trị "database"; giờ chỉ nhận "page" hoặc "data_source".
    """
    response: Any = client.search(
        filter={"property": "object", "value": "data_source", "in_trash": False},
        page_size=100,
    )
    results = response["results"]

    if not results:
        logger.warning(
            "Integration chưa được share database nào. Mở database trên Notion "
            "→ ••• → Connections → thêm integration."
        )
        return

    logger.info("Integration nhìn thấy %d bảng (data source):", len(results))
    for data_source in results:
        parent = data_source.get("parent") or {}
        logger.info(
            "  %s  (database %s)  %s",
            data_source["id"],
            parent.get("database_id", "?"),
            _plain_text(data_source.get("title")) or "(không tiêu đề)",
        )


def describe_database(client: Client, notion_id: str, sample_size: int) -> None:
    """In schema của từng data source trong database, đánh dấu property chứa file."""
    for data_source_id, name in resolve_data_sources(client, notion_id):
        data_source: Any = client.data_sources.retrieve(data_source_id=data_source_id)
        logger.info(
            "Data source: %s (%s)",
            name or _plain_text(data_source.get("title")) or "(không tên)",
            data_source_id,
        )

        file_props: list[str] = []
        logger.info("Properties:")
        for prop_name, prop in data_source["properties"].items():
            prop_type = prop["type"]
            marker = "  <-- chứa file" if prop_type == "files" else ""
            logger.info("  %-30s %s%s", prop_name, prop_type, marker)
            if prop_type == "files":
                file_props.append(prop_name)

        if not file_props:
            logger.warning(
                "Data source này KHÔNG có property kiểu 'files'. CV có thể ở database khác, "
                "hoặc nằm trong nội dung trang (dùng --include-blocks khi tải)."
            )

        if sample_size <= 0:
            continue

        response: Any = client.data_sources.query(
            data_source_id=data_source_id, page_size=sample_size
        )
        logger.info("%d dòng mẫu:", len(response["results"]))
        for page in response["results"]:
            attached = [
                f"{prop}={len(page['properties'][prop].get('files') or [])} file"
                for prop in file_props
            ]
            logger.info("  %-45s %s", page_title(page)[:45], ", ".join(attached) or "-")


def main(argv: list[str] | None = None) -> int:
    force_utf8_console()

    parser = argparse.ArgumentParser(description="Kiểm tra quyền truy cập và schema Notion.")
    parser.add_argument("--database-id", default=None, help="Database id hoặc URL Notion")
    parser.add_argument("--sample-size", type=int, default=3)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    settings = get_settings()
    if not settings.notion_api_key:
        logger.error("Thiếu NOTION_API_KEY trong backend/.env")
        return 1

    client = Client(auth=settings.notion_api_key)
    target = args.database_id

    try:
        if target:
            describe_database(client, normalize_notion_id(target), args.sample_size)
        else:
            list_databases(client)
    except ValueError as exc:
        logger.error("%s", exc)
        return 1
    except APIResponseError as exc:
        logger.error("Notion từ chối: %s", exc)
        if exc.code == "object_not_found":
            logger.error(
                "Id đúng nhưng integration chưa được share. Mở database trên Notion "
                "→ ••• → Connections → thêm integration của bạn."
            )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
