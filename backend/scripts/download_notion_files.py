"""Tải toàn bộ file đính kèm (CV...) của một Notion database về máy.

Notion trả link file có chữ ký và HẾT HẠN SAU ~1 GIỜ, nên phải tải ngay trong lúc
chạy chứ không lưu link lại để dùng sau.

Cách dùng:
    # 1) đặt NOTION_API_KEY trong backend/.env (xem scripts/README.md)
    # 2) xem trước có gì, chưa tải:
    uv run python -m scripts.download_notion_files --dry-run

    # 3) tải thật:
    uv run python -m scripts.download_notion_files --output-dir ./data/cv

Mặc định quét CẢ property lẫn nội dung trang (đệ quy tới 3 cấp), vì CV thường được
đính thẳng vào trong từng trang. Dùng --skip-blocks nếu chỉ cần property.

Hai chế độ nguồn:
    --database-id  quét mọi dòng của một bảng Notion (mặc định lấy NOTION_DATABASE_ID)
    --page-id      quét thẳng (các) trang cụ thể, bỏ qua bước query bảng

Cả hai đều nhận URL Notion hoặc id thô. Script đi XUYÊN QUA bảng lồng: gặp bảng con
bên trong một trang (kiểu "Job Application for ...") thì query luôn bảng đó và quét
từng dòng — tắt bằng --no-child-databases.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from notion_client import Client
from notion_client.errors import APIResponseError

from config import get_settings

logger = logging.getLogger("download_notion_files")

# Notion giới hạn ~3 request/giây; nghỉ giữa các call cho an toàn.
_RATE_LIMIT_SLEEP = 0.35

# Các loại block có thể chứa file đính kèm.
_FILE_BLOCK_TYPES = frozenset({"file", "pdf", "image", "video", "audio"})

# Độ sâu đệ quy khi quét nội dung trang (toggle / column / sub-page lồng nhau).
_DEFAULT_MAX_DEPTH = 3

_INVALID_FILENAME_CHARS = re.compile(r"[<>:\"/\\|?*\x00-\x1f]")


@dataclass(slots=True)
class NotionFile:
    """Một file đính kèm tìm thấy trên Notion."""

    page_id: str
    page_title: str
    source: str  # tên property, hoặc "block:<type>"
    file_name: str
    url: str
    is_external: bool

    @property
    def local_name(self) -> str:
        """Tên file trên đĩa: <tiêu đề trang>__<8 ký tự id>__<tên gốc>."""
        title = _sanitize(self.page_title) or "untitled"
        short_id = self.page_id.replace("-", "")[:8]
        return f"{title[:80]}__{short_id}__{_sanitize(self.file_name)}"


# ---------------------------------------------------------------------------
# Thu thập
# ---------------------------------------------------------------------------
def resolve_data_sources(client: Client, notion_id: str) -> list[tuple[str, str]]:
    """Trả về [(data_source_id, tên)] của một database.

    Từ Notion API 2025-09-03, database là "vỏ" chứa một hay nhiều data source;
    muốn query dữ liệu phải đi qua data source chứ không query database nữa.
    Hàm này cũng chấp nhận id vốn đã là data source.
    """
    try:
        database: Any = client.databases.retrieve(database_id=notion_id)
    except APIResponseError as exc:
        if exc.code != "object_not_found":
            raise
        # Có thể người dùng đưa thẳng data_source_id.
        data_source: Any = client.data_sources.retrieve(data_source_id=notion_id)
        return [(data_source["id"], _plain_text(data_source.get("title")))]

    sources = database.get("data_sources") or []
    if not sources:
        raise ValueError(f"Database {notion_id} không có data source nào.")

    return [(item["id"], item.get("name") or "") for item in sources]


def resolve_view(client: Client, view_id: str) -> tuple[str, dict[str, Any] | None]:
    """Đọc một VIEW → trả về (data_source_id của bảng gốc, bộ lọc của view).

    Đây là cách lấy đúng tập dòng mà một linked view đang hiển thị: view lưu sẵn
    `data_source_id` trỏ về bảng thật, cùng `filter` / `quick_filters`. Nhờ vậy
    lấy được "CV của đúng job này" thay vì cả bảng gồm ứng viên từ đời nào.
    """
    view: Any = client.views.retrieve(view_id=view_id)
    data_source_id: str = view["data_source_id"]

    conditions: list[dict[str, Any]] = []
    if view.get("filter"):
        conditions.append(view["filter"])
    for property_id, condition in (view.get("quick_filters") or {}).items():
        conditions.append({"property": property_id, **condition})

    logger.info(
        "View %r trên bảng %s, %d điều kiện lọc: %s",
        view.get("name") or "(không tên)",
        data_source_id,
        len(conditions),
        _describe_filters(view, conditions),
    )

    if not conditions:
        return data_source_id, None
    return data_source_id, ({"and": conditions} if len(conditions) > 1 else conditions[0])


def _describe_filters(view: dict[str, Any], conditions: list[dict[str, Any]]) -> str:
    """Đổi property_id khó đọc ("sLOi") thành tên cột để log cho người xem."""
    names = {
        item["property_id"]: item["property_name"]
        for item in (view.get("configuration") or {}).get("properties", [])
        if "property_name" in item
    }
    parts = []
    for condition in conditions:
        property_id = condition.get("property")
        rest = {k: v for k, v in condition.items() if k != "property"}
        parts.append(f"{names.get(property_id, property_id)}={rest}")
    return "; ".join(parts) or "(không lọc)"


def iter_pages(
    client: Client,
    data_source_id: str,
    limit: int | None = None,
    query_filter: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Lấy page của một data source (tự phân trang). `limit` để dừng sớm."""
    pages: list[dict[str, Any]] = []
    cursor: str | None = None
    page_size = 100 if limit is None else min(100, limit)

    while True:
        query: dict[str, Any] = {
            "data_source_id": data_source_id,
            "start_cursor": cursor,
            "page_size": page_size,
        }
        if query_filter is not None:
            query["filter"] = query_filter
        response: Any = client.data_sources.query(**query)
        pages.extend(response["results"])
        logger.info("Đã lấy %d page...", len(pages))

        if limit is not None and len(pages) >= limit:
            return pages[:limit]
        if not response.get("has_more"):
            break
        cursor = response["next_cursor"]
        time.sleep(_RATE_LIMIT_SLEEP)

    return pages


def fetch_page(client: Client, page_id: str) -> dict[str, Any]:
    """Lấy một page rời (không thuộc database nào cần query).

    Dùng cho chế độ --page-id: đi thẳng vào page rồi duyệt block con, giống cách
    một knowledge-base crawler hoạt động — không cần biết database/data source.
    """
    page: dict[str, Any] = client.pages.retrieve(page_id=page_id)
    logger.info("Page: %s (%s)", page_title(page) or "(không tiêu đề)", page_id)
    return page


def files_from_properties(page: dict[str, Any]) -> list[NotionFile]:
    """Quét các property kiểu `files` — chỗ CV thường được đính kèm."""
    page_id: str = page["id"]
    title = page_title(page)
    found: list[NotionFile] = []

    for prop_name, prop in page.get("properties", {}).items():
        if prop.get("type") != "files":
            continue

        for item in prop.get("files") or []:
            parsed = _parse_file_item(item)
            if parsed is None:
                continue
            url, is_external = parsed
            found.append(
                NotionFile(
                    page_id=page_id,
                    page_title=title,
                    source=prop_name,
                    file_name=item.get("name") or _name_from_url(url),
                    url=url,
                    is_external=is_external,
                )
            )

    return found


def files_from_blocks(
    client: Client,
    page: dict[str, Any],
    max_depth: int = _DEFAULT_MAX_DEPTH,
    on_child_database: Callable[[str], None] | None = None,
) -> list[NotionFile]:
    """Quét file nằm trong NỘI DUNG trang (không phải property).

    Duyệt đệ quy: CV hay bị đặt trong toggle, column, callout hoặc sub-page chứ
    không phải lúc nào cũng ở cấp ngoài cùng.

    `on_child_database` được gọi khi gặp một bảng lồng trong trang. Hàm này chỉ
    quét block; muốn đi tiếp vào bảng con thì dùng `Crawler` bên dưới.
    """
    return _walk_blocks(
        client,
        block_id=page["id"],
        page_id=page["id"],
        page_title_text=page_title(page),
        depth=0,
        max_depth=max_depth,
        on_child_database=on_child_database,
    )


def _walk_blocks(
    client: Client,
    block_id: str,
    page_id: str,
    page_title_text: str,
    depth: int,
    max_depth: int,
    on_child_database: Callable[[str], None] | None = None,
) -> list[NotionFile]:
    found: list[NotionFile] = []
    cursor: str | None = None

    while True:
        response: Any = client.blocks.children.list(
            block_id=block_id, start_cursor=cursor, page_size=100
        )

        for block in response["results"]:
            block_type = block.get("type")

            if block_type in _FILE_BLOCK_TYPES:
                parsed = _parse_file_item(block[block_type])
                if parsed is not None:
                    url, is_external = parsed
                    found.append(
                        NotionFile(
                            page_id=page_id,
                            page_title=page_title_text,
                            source=f"block:{block_type}",
                            file_name=block[block_type].get("name") or _name_from_url(url),
                            url=url,
                            is_external=is_external,
                        )
                    )
                continue

            # child_database (bảng lồng trong trang, ví dụ "Job Application for X")
            # KHÔNG duyệt được như block thường — phải query nó như một database.
            if block_type == "child_database":
                if on_child_database is not None:
                    on_child_database(block["id"])
                else:
                    logger.debug("Bỏ qua child_database %s", block["id"])
                continue

            if block.get("has_children") and depth < max_depth:
                time.sleep(_RATE_LIMIT_SLEEP)
                found.extend(
                    _walk_blocks(
                        client,
                        block_id=block["id"],
                        page_id=page_id,
                        page_title_text=page_title_text,
                        depth=depth + 1,
                        max_depth=max_depth,
                        on_child_database=on_child_database,
                    )
                )

        if not response.get("has_more"):
            break
        cursor = response["next_cursor"]
        time.sleep(_RATE_LIMIT_SLEEP)

    return found


class Crawler:
    """Đi hết cây Notion: database → từng dòng → nội dung dòng → BẢNG LỒNG bên trong.

    Cấu trúc thực tế ở nexlab: `Job Post` là một bảng, mỗi dòng là một tin tuyển
    dụng, và BÊN TRONG mỗi tin lại có bảng `Job Application for ...` mà mỗi dòng
    là một ứng viên — CV nằm ở tầng đó. Không đi xuyên qua bảng lồng thì không
    thấy CV nào.

    Chống lặp vô hạn bằng tập id đã thăm (Notion cho phép nhúng chéo lẫn nhau).
    """

    def __init__(
        self,
        client: Client,
        *,
        max_depth: int = _DEFAULT_MAX_DEPTH,
        scan_blocks: bool = True,
        follow_child_databases: bool = True,
        max_pages: int | None = None,
    ) -> None:
        self._client = client
        self._max_depth = max_depth
        self._scan_blocks = scan_blocks
        self._follow_child_databases = follow_child_databases
        self._max_pages = max_pages
        self._visited_pages: set[str] = set()
        self._visited_databases: set[str] = set()
        self.files: list[NotionFile] = []
        self.inaccessible_databases: list[str] = []

    def crawl_database(self, database_id: str) -> None:
        if database_id in self._visited_databases:
            return
        self._visited_databases.add(database_id)

        for data_source_id, name in resolve_data_sources(self._client, database_id):
            logger.info("Bảng: %s (%s)", name or "(không tên)", data_source_id)
            for page in iter_pages(self._client, data_source_id, limit=self._max_pages):
                if self._reached_limit():
                    logger.info("Đã đủ %d trang (--limit), dừng.", self._max_pages)
                    return
                self.crawl_page(page)

    def _crawl_nested_database(self, database_id: str) -> None:
        """Như crawl_database nhưng KHÔNG làm hỏng cả lượt chạy khi một bảng lồng lỗi.

        Notion trả `data_sources: []` khi integration nhìn thấy vỏ database nhưng
        không có quyền đọc dữ liệu bên trong. Quyền ở bảng CHA không tự lan xuống
        data source của bảng lồng — phải nối integration ở cấp TRANG cha chung.
        Bỏ qua riêng bảng đó và đi tiếp, ghi lại để báo cuối lượt.
        """
        try:
            self.crawl_database(database_id)
        except ValueError:
            self.inaccessible_databases.append(database_id)
            logger.warning(
                "Bảng lồng %s: thấy vỏ nhưng không đọc được dữ liệu (data_sources rỗng) "
                "— thiếu quyền. Bỏ qua, đi tiếp.",
                database_id,
            )
        except APIResponseError as exc:
            if exc.code != "object_not_found":
                raise
            self.inaccessible_databases.append(database_id)
            logger.warning("Bảng lồng %s chưa được share cho integration. Bỏ qua.", database_id)

    def crawl_view(self, view_id: str) -> None:
        """Crawl đúng tập dòng mà một view đang hiển thị (đã áp bộ lọc của view)."""
        data_source_id, query_filter = resolve_view(self._client, view_id)
        for page in iter_pages(
            self._client, data_source_id, limit=self._max_pages, query_filter=query_filter
        ):
            if self._reached_limit():
                logger.info("Đã đủ %d trang (--limit), dừng.", self._max_pages)
                return
            self.crawl_page(page)

    def _reached_limit(self) -> bool:
        return self._max_pages is not None and len(self._visited_pages) >= self._max_pages

    def crawl_page(self, page: dict[str, Any]) -> None:
        page_id: str = page["id"]
        if page_id in self._visited_pages or self._reached_limit():
            return
        self._visited_pages.add(page_id)

        self.files.extend(files_from_properties(page))

        if not self._scan_blocks:
            return

        logger.info("Quét nội dung: %s", page_title(page)[:60] or "(không tiêu đề)")
        self.files.extend(
            files_from_blocks(
                self._client,
                page,
                max_depth=self._max_depth,
                on_child_database=self._on_child_database,
            )
        )
        time.sleep(_RATE_LIMIT_SLEEP)

    def _on_child_database(self, database_id: str) -> None:
        if not self._follow_child_databases:
            logger.info("Bỏ qua bảng lồng %s (--no-child-databases)", database_id)
            return
        logger.info("Đi vào bảng lồng %s", database_id)
        self._crawl_nested_database(database_id)


def page_title(page: dict[str, Any]) -> str:
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            return _plain_text(prop.get("title"))
    return ""


def _plain_text(rich_text: Any) -> str:
    if not rich_text:
        return ""
    return "".join(part.get("plain_text", "") for part in rich_text)


# ---------------------------------------------------------------------------
# Tải về
# ---------------------------------------------------------------------------
def deduplicate(files: list[NotionFile]) -> list[NotionFile]:
    """Bỏ bản trùng: cùng một file hay bị đính CẢ ở property lẫn trong nội dung trang.

    Khoá so sánh là đường dẫn URL đã bỏ query string, vì phần chữ ký của link
    Notion khác nhau giữa hai lần trả về dù trỏ cùng một file.
    """
    seen: set[tuple[str, str]] = set()
    unique: list[NotionFile] = []

    for item in files:
        key = (item.page_id, urlparse(item.url).path)
        if key in seen:
            logger.debug("Bỏ bản trùng: %s (%s)", item.file_name, item.source)
            continue
        seen.add(key)
        unique.append(item)

    if len(unique) < len(files):
        logger.info("Bỏ %d bản trùng.", len(files) - len(unique))

    return unique


def _unique_path(output_dir: Path, name: str, taken: set[str]) -> Path:
    """Hai file KHÁC nhau cùng tên trong một trang thì thêm hậu tố -2, -3..."""
    if name not in taken:
        taken.add(name)
        return output_dir / name

    stem, suffix = Path(name).stem, Path(name).suffix
    counter = 2
    while f"{stem}-{counter}{suffix}" in taken:
        counter += 1

    unique_name = f"{stem}-{counter}{suffix}"
    taken.add(unique_name)
    return output_dir / unique_name


def download(files: list[NotionFile], output_dir: Path, overwrite: bool) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []
    taken: set[str] = set()

    with httpx.Client(timeout=60.0, follow_redirects=True) as http:
        for index, item in enumerate(files, start=1):
            target = _unique_path(output_dir, item.local_name, taken)
            record: dict[str, Any] = asdict(item) | {"local_path": str(target)}

            if target.exists() and not overwrite:
                logger.info("[%d/%d] Bỏ qua (đã có): %s", index, len(files), target.name)
                manifest.append(record | {"status": "skipped"})
                continue

            try:
                with http.stream("GET", item.url) as response:
                    response.raise_for_status()
                    with target.open("wb") as fp:
                        for chunk in response.iter_bytes(chunk_size=65536):
                            fp.write(chunk)
            except httpx.HTTPError as exc:
                logger.error("[%d/%d] LỖI %s: %s", index, len(files), item.file_name, exc)
                target.unlink(missing_ok=True)
                manifest.append(record | {"status": "failed", "error": str(exc)})
                continue

            size = target.stat().st_size
            logger.info("[%d/%d] Đã tải %s (%.1f KB)", index, len(files), target.name, size / 1024)
            manifest.append(record | {"status": "downloaded", "bytes": size})

    return manifest


def write_manifest(output_dir: Path, database_id: str, manifest: list[dict[str, Any]]) -> Path:
    """Ghi lại file nào đến từ page nào — để bước extract sau này truy ngược được."""
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "database_id": database_id,
                "downloaded_at": datetime.now(UTC).isoformat(),
                "files": manifest,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return manifest_path


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _parse_file_item(item: dict[str, Any]) -> tuple[str, bool] | None:
    """Trả về (url, is_external). Link `file` do Notion host sẽ hết hạn sau ~1h."""
    if item.get("type") == "external":
        url = (item.get("external") or {}).get("url")
        return (url, True) if url else None

    url = (item.get("file") or {}).get("url")
    return (url, False) if url else None


def force_utf8_console() -> None:
    """Console Windows mặc định là cp1252, in tiếng Việt sẽ UnicodeEncodeError."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def _sanitize(value: str) -> str:
    cleaned = _INVALID_FILENAME_CHARS.sub("_", value).strip(" .")
    return re.sub(r"\s+", " ", cleaned)


def _name_from_url(url: str) -> str:
    return Path(urlparse(url).path).name or "file"


def extract_view_id(raw: str) -> str:
    """Lấy view id: ưu tiên query `v=` trong URL, nếu không thì coi raw là id thô."""
    candidate = raw.strip()
    if candidate.startswith("http"):
        view = parse_qs(urlparse(candidate).query).get("v")
        if not view:
            raise ValueError(f"URL không có tham số ?v= (id của view): {raw}")
        candidate = view[0]
    return normalize_notion_id(candidate)


def normalize_notion_id(raw: str) -> str:
    """Chấp nhận URL Notion hoặc id thô (database hay page), có/không dấu gạch."""
    candidate = raw.strip()

    if candidate.startswith("http"):
        parsed = urlparse(candidate)

        # URL "peek" (mở trang chồng lên bảng) đặt id TRANG ở query `p=`, còn path
        # vẫn là bảng nền. Ưu tiên `p=` vì đó mới là thứ người dùng đang xem.
        peek = parse_qs(parsed.query).get("p")
        segment = peek[0] if peek else parsed.path.rstrip("/").split("/")[-1]

        match = re.search(r"[0-9a-fA-F]{32}", segment.replace("-", ""))
        if match is None:
            raise ValueError(f"Không tìm thấy id Notion trong URL: {raw}")
        candidate = match.group(0)

    hex_only = candidate.replace("-", "")
    if len(hex_only) != 32:
        raise ValueError(f"Id Notion không hợp lệ: {raw!r}")

    return f"{hex_only[:8]}-{hex_only[8:12]}-{hex_only[12:16]}-{hex_only[16:20]}-{hex_only[20:]}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    force_utf8_console()

    parser = argparse.ArgumentParser(description="Tải file đính kèm từ Notion database về local.")
    parser.add_argument(
        "--database-id",
        default=None,
        help="Database id hoặc URL Notion (quét toàn bảng)",
    )
    parser.add_argument(
        "--page-id",
        action="append",
        default=None,
        metavar="ID_HOẶC_URL",
        help=(
            "Quét thẳng (các) page cụ thể, bỏ qua bước query database. "
            "Lặp lại cờ này cho nhiều page. Không dùng chung với --database-id."
        ),
    )
    parser.add_argument(
        "--view-id",
        default=None,
        metavar="ID_HOẶC_URL",
        help=(
            "Lấy đúng các dòng mà một VIEW đang hiển thị (áp bộ lọc của view đó). "
            "Dán nguyên URL có ?v=... là được — hợp để lấy CV của riêng một job."
        ),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("./data/notion-files"))
    parser.add_argument(
        "--skip-blocks",
        action="store_true",
        help="Chỉ quét property, bỏ qua nội dung trang (nhanh hơn nhiều)",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=_DEFAULT_MAX_DEPTH,
        help="Độ sâu đệ quy khi quét nội dung trang (mặc định %(default)s)",
    )
    parser.add_argument(
        "--no-child-databases",
        action="store_true",
        help=(
            "Không đi vào bảng lồng bên trong trang. Mặc định CÓ đi vào — ứng viên "
            "thường nằm ở bảng con kiểu 'Job Application for ...'."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Chỉ xử lý N trang đầu — dùng để thử trước trên bảng lớn",
    )
    parser.add_argument("--dry-run", action="store_true", help="Chỉ liệt kê, không tải")
    parser.add_argument("--overwrite", action="store_true", help="Tải đè file đã có")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    settings = get_settings()
    if not settings.notion_api_key:
        logger.error(
            "Thiếu NOTION_API_KEY. Tạo internal integration tại "
            "https://www.notion.so/my-integrations rồi thêm vào backend/.env"
        )
        return 1

    chosen = [bool(args.page_id), bool(args.database_id), bool(args.view_id)]
    if sum(chosen) > 1:
        logger.error("Chỉ chọn MỘT trong: --page-id, --database-id, --view-id.")
        return 1

    client = Client(auth=settings.notion_api_key)
    crawler = Crawler(
        client,
        max_depth=args.max_depth,
        scan_blocks=not args.skip_blocks,
        follow_child_databases=not args.no_child_databases,
        max_pages=args.limit,
    )

    try:
        if args.view_id:
            source_id = extract_view_id(args.view_id)
            crawler.crawl_view(source_id)
        elif args.page_id:
            # Chế độ page: pages.retrieve rồi duyệt block, không query bảng nào.
            source_id = ",".join(args.page_id)
            for raw in args.page_id:
                crawler.crawl_page(fetch_page(client, normalize_notion_id(raw)))
        else:
            raw_id = args.database_id
            if not raw_id:
                logger.error("Chưa có id: truyền --view-id, --database-id hoặc --page-id.")
                return 1
            source_id = normalize_notion_id(raw_id)
            crawler.crawl_database(source_id)
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

    return _download_result(crawler, source_id, args)


def _download_result(crawler: Crawler, source_id: str, args: argparse.Namespace) -> int:
    files = deduplicate(crawler.files)
    logger.info("Tìm thấy %d file đính kèm.", len(files))

    if crawler.inaccessible_databases:
        logger.warning(
            "%d bảng lồng KHÔNG đọc được — dữ liệu trong đó (có thể gồm CV) đã bị bỏ sót. "
            "Quyền nối ở bảng cha không lan xuống bảng lồng bên trong từng trang. "
            "Cách xử lý: nối integration ở cấp TRANG CHA CHUNG (ví dụ 'HR/ADMIN HUB') "
            "thay vì chỉ ở bảng job post.",
            len(crawler.inaccessible_databases),
        )

    if not files:
        logger.warning(
            "Không có file nào. Thử tăng --max-depth nếu CV nằm sâu trong trang. "
            "Dùng --verbose để xem script đã đi vào những bảng lồng nào."
        )
        return 0

    if args.dry_run:
        for item in files:
            logger.info("  [%s] %s -> %s", item.source, item.page_title, item.local_name)
        return 0

    manifest = download(files, args.output_dir, overwrite=args.overwrite)
    manifest_path = write_manifest(args.output_dir, source_id, manifest)

    downloaded = sum(1 for item in manifest if item["status"] == "downloaded")
    failed = sum(1 for item in manifest if item["status"] == "failed")
    logger.info(
        "Xong: %d tải mới, %d bỏ qua, %d lỗi. Manifest: %s",
        downloaded,
        len(manifest) - downloaded - failed,
        failed,
        manifest_path,
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
