"""Cấu hình tập trung cho MCP server.

Mọi biến môi trường chỉ được đọc tại đây (qua pydantic-settings), không dùng
os.environ rải rác trong code. Xem `.env.example` để biết các biến cần khai báo.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    app_name: str = "nexlab-scan-cv"
    environment: Literal["local", "dev", "prod"] = "local"
    log_level: str = "INFO"

    gcp_project_id: str = ""
    gcp_region: str = "asia-southeast1"

    # --- OCR cho CV dạng ảnh scan (Gemini qua Vertex AI, không dùng API key) ---
    ocr_enabled: bool = True
    gemini_model: str = "gemini-2.5-flash"
    vertex_location: str = "global"
    ocr_timeout_seconds: int = 180

    # --- Notion ---
    notion_api_key: str = ""
    notion_source_data_source_id: str = ""
    """Data source NGUỒN — bảng đơn ứng tuyển do Tally đổ vào."""

    # Chỉ còn MỘT bảng: đọc CV và ghi text đều trên bảng nguồn.

    scan_concurrency: int = 4
    """Số dòng nhân bản song song. Notion ~3 req/s, mỗi dòng tốn ~5 lời gọi."""

    # --- Trang quản trị cho HR ---
    cloud_run_job_name: str = ""
    """Tên Cloud Run Job mà nút bấm sẽ kích hoạt."""

    cloud_scheduler_job_name: str = ""
    """Tên Cloud Scheduler job — để HR đổi giờ chạy tự động từ trang quản trị."""

    admin_password: str = ""
    """Mật khẩu dùng chung. Rỗng = KHÔNG chặn (chỉ chấp nhận được khi chạy local)."""

    # --- Tải file CV ---
    download_timeout_seconds: float = 60.0
    max_cv_bytes: int = 20 * 1024 * 1024
    allowed_file_hosts: list[str] = Field(
        default_factory=lambda: [
            # Form Tally upload thẳng lên đây; CV trong Notion là link `external`
            # trỏ về host này chứ không phải file do Notion lưu.
            "storage.tally.so",
            # File thật sự do Notion lưu (khi ai đó kéo thả trực tiếp vào bảng).
            "prod-files-secure.s3.us-west-2.amazonaws.com",
            "s3.us-west-2.amazonaws.com",
            "file.notion.so",
            "www.notion.so",
        ]
    )
    """Chặn SSRF: `file_url` do agent gửi vào nên phải giới hạn host tải được.

    Rỗng = cho phép mọi host (chỉ nên dùng khi chạy local).
    """


@lru_cache
def get_settings() -> Settings:
    """Settings dùng chung toàn app; cache để chỉ parse .env một lần."""
    return Settings()
