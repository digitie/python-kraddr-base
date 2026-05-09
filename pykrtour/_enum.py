"""Python 3.10 호환 문자열 enum 기반 클래스."""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """Python 3.10에서 `enum.StrEnum`을 대신하는 최소 호환 클래스."""

    def __str__(self) -> str:
        return str(self.value)
