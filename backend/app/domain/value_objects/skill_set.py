"""Value object: tập kỹ năng đã chuẩn hoá (bỏ trùng, giữ thứ tự xuất hiện)."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SkillSet:
    values: tuple[str, ...] = ()

    @classmethod
    def from_raw(cls, raw: Iterable[str] | None) -> SkillSet:
        """Trim, bỏ rỗng, bỏ trùng (không phân biệt hoa/thường), giữ nguyên thứ tự."""
        if raw is None:
            return cls()

        seen: set[str] = set()
        cleaned: list[str] = []
        for item in raw:
            skill = (item or "").strip()
            if not skill:
                continue
            key = skill.casefold()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(skill)
        return cls(tuple(cleaned))

    def __iter__(self) -> Iterator[str]:
        return iter(self.values)

    def __len__(self) -> int:
        return len(self.values)

    def as_list(self) -> list[str]:
        return list(self.values)
