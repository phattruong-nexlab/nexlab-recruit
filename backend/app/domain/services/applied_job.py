"""Domain service: suy ra tên vị trí ứng tuyển từ Job URL.

Thuần chuỗi, KHÔNG dùng LLM — Job URL do agent gửi sang là nguồn chính xác nhất,
không cần đoán từ nội dung CV.

    https://nexlab.tech/jobs/senior-data-engineer  ->  "Senior Data Engineer"
"""

from __future__ import annotations

from urllib.parse import urlparse

# Từ viết tắt cần giữ nguyên dạng in hoa khi dựng lại tên vị trí.
_ACRONYMS = frozenset({"ai", "ba", "qa", "qc", "hr", "pm", "ui", "ux", "his", "it", "devops"})


def from_job_url(job_url: str | None) -> str | None:
    """Lấy slug cuối của URL rồi đổi thành tên đọc được. Không parse được → None."""
    if not job_url:
        return None

    path = urlparse(job_url.strip()).path if "//" in job_url else job_url.strip()
    slug = path.rstrip("/").split("/")[-1]
    if not slug:
        return None

    words = [word for word in slug.replace("_", "-").split("-") if word]
    if not words:
        return None

    return " ".join(
        word.upper() if word.lower() in _ACRONYMS else word.capitalize() for word in words
    )
