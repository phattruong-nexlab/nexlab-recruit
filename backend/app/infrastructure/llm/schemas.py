"""JSON schema ép Gemini trả structured output."""

from __future__ import annotations

from typing import Any

CV_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "full_name": {"type": "string", "nullable": True},
        "university": {"type": "string", "nullable": True},
        "gpa": {"type": "number", "nullable": True},
        "skills": {"type": "array", "items": {"type": "string"}},
        "certificates": {"type": "array", "items": {"type": "string"}},
        "languages": {"type": "array", "items": {"type": "string"}},
        "experiences": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"},
                    "position": {"type": "string"},
                    "start_year": {"type": "integer", "nullable": True},
                    "end_year": {"type": "integer", "nullable": True},
                    "is_current": {"type": "boolean"},
                    "description": {"type": "string"},
                },
                "required": ["company", "position", "is_current", "description"],
            },
        },
    },
    "required": ["skills", "certificates", "languages", "experiences"],
}
