"""DTO cho lượt quét hàng loạt."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ScanFailure:
    source_page_id: str
    candidate_name: str
    reason: str


@dataclass(slots=True)
class ScanSummary:
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    failures: list[ScanFailure] = field(default_factory=list)

    @property
    def all_ok(self) -> bool:
        return self.failed == 0
