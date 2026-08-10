"""Downloader nhận URL từ agent — phải chặn SSRF và giới hạn kích thước."""

from __future__ import annotations

import pytest

from app.domain.exceptions import CvDownloadError
from app.infrastructure.http.file_downloader import HttpCvDownloader


@pytest.mark.parametrize(
    "url",
    ["file:///etc/passwd", "ftp://x/cv.pdf", "not-a-url", "http://"],
)
async def test_tu_choi_scheme_khong_phai_http(url: str) -> None:
    with pytest.raises(CvDownloadError):
        await HttpCvDownloader().download(url)


async def test_chan_host_ngoai_danh_sach_cho_phep() -> None:
    downloader = HttpCvDownloader(allowed_hosts=["file.notion.so"])

    with pytest.raises(CvDownloadError, match="không nằm trong danh sách"):
        await downloader.download("https://169.254.169.254/latest/meta-data/")


async def test_danh_sach_rong_thi_khong_chan_host() -> None:
    """Chỉ dùng khi chạy local; lỗi phát sinh sau đó là lỗi mạng, không phải chặn host."""
    downloader = HttpCvDownloader(allowed_hosts=[], timeout_seconds=0.001)

    with pytest.raises(CvDownloadError) as exc:
        await downloader.download("https://127.0.0.1:9/cv.pdf")

    assert "không nằm trong danh sách" not in str(exc.value)
