"""Adapter: Gemini trên Vertex AI — một call + structured output.

Đây là nơi DUY NHẤT trong hệ thống gọi LLM. Mọi bước khác là code thuần.

Xác thực bằng Application Default Credentials, KHÔNG dùng API key:
- Trên Cloud Run: service account gắn vào service, cần role `roles/aiplatform.user`.
- Ở máy local: `gcloud auth application-default login`.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from google import genai
from google.genai import types

from app.application.dto.parse_cv import ExtractedCv, ExtractedExperience
from app.application.ports.cv_extractor import CvExtractor
from app.domain.exceptions import CvExtractionError
from app.infrastructure.llm.prompts import (
    CV_EXTRACTION_SYSTEM_PROMPT,
    CV_EXTRACTION_USER_TEMPLATE,
)
from app.infrastructure.llm.schemas import CV_RESPONSE_SCHEMA

logger = logging.getLogger(__name__)


class GeminiCvExtractor(CvExtractor):
    def __init__(
        self,
        model: str,
        project_id: str = "",
        location: str = "global",
        timeout_seconds: int = 120,
    ) -> None:
        self._model = model
        # project/location để trống thì SDK tự lấy từ ADC và biến môi trường
        # GOOGLE_CLOUD_PROJECT / GOOGLE_CLOUD_LOCATION.
        client_kwargs: dict[str, Any] = {
            "vertexai": True,
            "http_options": types.HttpOptions(timeout=timeout_seconds * 1000),
        }
        if project_id:
            client_kwargs["project"] = project_id
        if location:
            client_kwargs["location"] = location

        self._client = genai.Client(**client_kwargs)
        logger.info(
            "Gemini qua Vertex AI: model=%s project=%s location=%s",
            model,
            project_id or "(từ ADC)",
            location,
        )

    async def extract(self, cv_markdown: str) -> ExtractedCv:
        if not cv_markdown.strip():
            raise CvExtractionError("CV rỗng, không có gì để trích xuất")

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=CV_EXTRACTION_USER_TEMPLATE.format(cv_markdown=cv_markdown),
                config=types.GenerateContentConfig(
                    system_instruction=CV_EXTRACTION_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=CV_RESPONSE_SCHEMA,
                    temperature=0.0,
                ),
            )
        except Exception as exc:  # SDK ném nhiều loại lỗi mạng/quota/quyền khác nhau
            raise CvExtractionError(
                f"Vertex AI lỗi: {exc}. Kiểm tra service account có role "
                "roles/aiplatform.user và API aiplatform.googleapis.com đã bật chưa."
            ) from exc

        raw = (response.text or "").strip()
        if not raw:
            raise CvExtractionError("Gemini trả về rỗng")

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CvExtractionError(f"Gemini trả về JSON hỏng: {exc}") from exc

        if not isinstance(payload, dict):
            raise CvExtractionError(f"Gemini trả về {type(payload).__name__}, cần object")

        logger.info("Trích xuất xong từ %d ký tự Markdown", len(cv_markdown))
        return to_dto(payload)


def to_dto(payload: dict[str, Any]) -> ExtractedCv:
    """Map JSON của LLM sang DTO. Thiếu field -> None/[] chứ không bịa."""
    experiences = [
        ExtractedExperience(
            company=str(item.get("company") or "").strip(),
            position=str(item.get("position") or "").strip(),
            start_year=_as_int(item.get("start_year")),
            end_year=_as_int(item.get("end_year")),
            is_current=bool(item.get("is_current", False)),
            description=str(item.get("description") or "").strip(),
        )
        for item in (payload.get("experiences") or [])
    ]

    return ExtractedCv(
        full_name=payload.get("full_name") or None,
        university=payload.get("university") or None,
        gpa=_as_float(payload.get("gpa")),
        experiences=experiences,
        skills=_as_str_list(payload.get("skills")),
        certificates=_as_str_list(payload.get("certificates")),
        languages=_as_str_list(payload.get("languages")),
    )


def _as_int(value: Any) -> int | None:
    """Năm không rõ -> None. Không suy đoán."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
