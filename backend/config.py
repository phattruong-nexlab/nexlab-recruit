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

    # --- MCP ---
    mcp_path: str = "/mcp"
    mcp_auth_token: str = ""
    """Bearer token tĩnh mà agent phải gửi kèm. Rỗng = tắt kiểm tra (chỉ dùng local)."""

    # --- Gemini qua Vertex AI ---
    # Không dùng API key: xác thực bằng Application Default Credentials.
    # Trên Cloud Run là service account gắn vào service; ở máy local là
    # `gcloud auth application-default login`.
    gcp_project_id: str = ""
    """Để trống thì SDK tự lấy từ ADC / GOOGLE_CLOUD_PROJECT."""

    vertex_location: str = "global"
    gemini_model: str = "gemini-2.5-flash"
    gemini_timeout_seconds: int = 120

    # --- Notion ---
    notion_api_key: str = ""
    notion_target_data_source_id: str = ""
    """Data source (bảng) đích để ghi kết quả trích xuất."""

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

    @property
    def auth_enabled(self) -> bool:
        return bool(self.mcp_auth_token)


@lru_cache
def get_settings() -> Settings:
    """Settings dùng chung toàn app; cache để chỉ parse .env một lần."""
    return Settings()
