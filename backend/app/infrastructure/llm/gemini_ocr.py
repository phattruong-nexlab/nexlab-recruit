"""Adapter: đọc text từ CV scan bằng Gemini trên Vertex AI.

Chỉ chạy khi markitdown không moi được text — tức PDF là ảnh scan. Gemini nhận
thẳng bytes PDF, không cần tách trang hay chuyển sang ảnh trước.

Xác thực bằng Application Default Credentials, KHÔNG dùng API key.
"""

from __future__ import annotations

import logging
from typing import Any

from google import genai
from google.genai import types

from app.application.ports.cv_downloader import DownloadedFile
from app.application.ports.cv_ocr import CvOcr
from app.domain.exceptions import CvParsingError

logger = logging.getLogger(__name__)

_PROMPT = """\
Đây là một CV dạng ảnh scan. Hãy đọc và chép lại TOÀN BỘ nội dung chữ trong file
thành Markdown.

- Giữ nguyên thứ tự và cấu trúc: tiêu đề mục, gạch đầu dòng, bảng.
- Chép đúng nguyên văn, KHÔNG tóm tắt, KHÔNG diễn giải, KHÔNG thêm nhận xét.
- Giữ nguyên ngôn ngữ gốc (tiếng Việt hoặc tiếng Anh).
- Chỗ nào mờ không đọc được thì ghi [không đọc được].
- Chỉ trả về nội dung CV, không thêm lời dẫn.
"""


class GeminiCvOcr(CvOcr):
    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        project_id: str = "",
        location: str = "global",
        timeout_seconds: int = 180,
    ) -> None:
        self._model = model
        client_kwargs: dict[str, Any] = {
            "vertexai": True,
            "http_options": types.HttpOptions(timeout=timeout_seconds * 1000),
        }
        if project_id:
            client_kwargs["project"] = project_id
        if location:
            client_kwargs["location"] = location

        self._client = genai.Client(**client_kwargs)
        logger.info("OCR qua Vertex AI: model=%s project=%s", model, project_id or "(từ ADC)")

    async def to_text(self, file: DownloadedFile) -> str:
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=[
                    types.Part.from_bytes(
                        data=file.content,
                        mime_type=file.content_type or "application/pdf",
                    ),
                    _PROMPT,
                ],
                config=types.GenerateContentConfig(temperature=0.0),
            )
        except Exception as exc:  # SDK ném nhiều loại lỗi mạng/quota/quyền
            raise CvParsingError(
                f"Vertex AI không đọc được {file.filename!r}: {exc}. Kiểm tra service "
                "account có roles/aiplatform.user và API aiplatform đã bật chưa."
            ) from exc

        text = (response.text or "").strip()
        if not text:
            raise CvParsingError(f"Vertex AI trả về rỗng cho {file.filename!r}")

        logger.info("OCR %s -> %d ký tự", file.filename, len(text))
        return text
