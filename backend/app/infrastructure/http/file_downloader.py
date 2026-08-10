"""Adapter: tải file CV qua HTTP.

Link file của Notion có chữ ký và hết hạn ~1 giờ nên phải tải ngay trong lúc xử lý.
"""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import ParseResult, unquote, urlparse

import httpx

from app.application.ports.cv_downloader import CvDownloader, DownloadedFile
from app.domain.exceptions import CvDownloadError

logger = logging.getLogger(__name__)


class HttpCvDownloader(CvDownloader):
    def __init__(
        self,
        timeout_seconds: float = 60.0,
        max_bytes: int = 20 * 1024 * 1024,
        allowed_hosts: list[str] | None = None,
    ) -> None:
        self._timeout = timeout_seconds
        self._max_bytes = max_bytes
        # Rỗng = cho phép mọi host (chỉ nên dùng khi chạy local).
        self._allowed_hosts = {host.lower() for host in (allowed_hosts or [])}

    async def download(self, url: str) -> DownloadedFile:
        parsed = self._validate(url)

        try:
            async with (
                httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client,
                client.stream("GET", url) as response,
            ):
                response.raise_for_status()
                content = await self._read_capped(response)
                content_type = response.headers.get("content-type")
        except httpx.HTTPStatusError as exc:
            raise CvDownloadError(
                f"Không tải được CV ({exc.response.status_code}). "
                "Link Notion hết hạn sau ~1 giờ, thử lấy link mới."
            ) from exc
        except httpx.HTTPError as exc:
            raise CvDownloadError(f"Lỗi mạng khi tải CV: {exc}") from exc

        filename = unquote(Path(parsed.path).name) or "cv.pdf"
        logger.info("Đã tải CV %s (%d bytes)", filename, len(content))
        return DownloadedFile(content=content, filename=filename, content_type=content_type)

    def _validate(self, url: str) -> ParseResult:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise CvDownloadError(f"URL phải là http/https, nhận được: {parsed.scheme!r}")
        if not parsed.netloc:
            raise CvDownloadError(f"URL không hợp lệ: {url!r}")

        # Chặn SSRF: chỉ cho tải từ host của Notion.
        if (
            self._allowed_hosts
            and parsed.hostname
            and (parsed.hostname.lower() not in self._allowed_hosts)
        ):
            raise CvDownloadError(f"Host {parsed.hostname!r} không nằm trong danh sách cho phép.")
        return parsed

    async def _read_capped(self, response: httpx.Response) -> bytes:
        """Đọc theo chunk và dừng ngay khi vượt ngưỡng, không nạp hết vào RAM."""
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes(chunk_size=65536):
            total += len(chunk)
            if total > self._max_bytes:
                raise CvDownloadError(f"File CV vượt quá {self._max_bytes} bytes.")
            chunks.append(chunk)

        if total == 0:
            raise CvDownloadError("File CV rỗng.")
        return b"".join(chunks)
