"""POI row 정규화에 쓰는 작은 변환 helper."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from math import isfinite
from types import MappingProxyType
from typing import Any, Final

SENSITIVE_RAW_KEYS: Final[frozenset[str]] = frozenset(
    {
        "api_key",
        "apikey",
        "authkey",
        "authorization",
        "certkey",
        "key",
        "servicekey",
        "x-api-key",
    }
)
"""raw payload를 보존할 때 제거할 인증/비밀 계열 key 이름."""

_EMPTY_RAW: Final[Mapping[str, Any]] = MappingProxyType({})


def strip_or_none(value: Any) -> str | None:
    """빈 문자열, 공백, 흔한 placeholder를 `None`으로 정규화합니다."""

    if value is None:
        return None
    text = str(value).strip()
    if text in {"", "-", "--", "null", "None", "NULL"}:
        return None
    return text


def first_value(row: Mapping[str, Any], *names: str) -> Any:
    """여러 후보 key 중 처음으로 비어 있지 않은 값을 반환합니다."""

    for name in names:
        value = row.get(name)
        if strip_or_none(value) is not None:
            return value
    return None


def to_float_or_none(value: Any) -> float | None:
    """문자열 숫자를 float로 바꾸고 빈값은 `None`으로 둡니다."""

    text = strip_or_none(value)
    if text is None:
        return None
    try:
        result = float(text.replace(",", ""))
    except ValueError:
        return None
    if not isfinite(result):
        return None
    return result


def to_int_or_none(value: Any) -> int | None:
    """문자열 정수를 int로 바꾸고 빈값은 `None`으로 둡니다."""

    text = strip_or_none(value)
    if text is None:
        return None
    normalized = text.replace(",", "").replace("원", "").strip()
    try:
        return int(Decimal(normalized))
    except (InvalidOperation, ValueError):
        return None


def to_bool_or_none(value: Any) -> bool | None:
    """공공데이터에서 흔한 Y/N, O/X, 1/0, true/false 값을 bool로 정규화합니다."""

    text = strip_or_none(value)
    if text is None:
        return None
    normalized = text.casefold()
    if normalized in {"y", "yes", "true", "t", "1", "o", "open", "운영", "영업", "정상"}:
        return True
    if normalized in {"n", "no", "false", "f", "0", "x", "closed", "폐업", "취소"}:
        return False
    return None


def to_bool_yn(value: Any) -> bool | None:
    """`to_bool_or_none`의 provider 코드용 명시 alias입니다."""

    return to_bool_or_none(value)


def freeze_raw(raw: Mapping[str, Any] | None) -> Mapping[str, Any]:
    """raw payload를 읽기 전용 mapping으로 보존하고 인증 계열 key를 제거합니다."""

    if raw is None:
        return _EMPTY_RAW
    if not isinstance(raw, Mapping):
        raise TypeError("raw must be a mapping")

    frozen: dict[str, Any] = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            raise TypeError("raw keys must be strings")
        if key.strip().replace("-", "_").casefold() in SENSITIVE_RAW_KEYS:
            continue
        frozen[key] = _freeze_raw_value(value)
    return MappingProxyType(frozen)


def json_safe_raw(value: Any) -> Any:
    """MappingProxyType, tuple 등을 JSON 직렬화하기 쉬운 기본 container로 바꿉니다."""

    if isinstance(value, Mapping):
        return {str(key): json_safe_raw(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [json_safe_raw(item) for item in value]
    return value


def _freeze_raw_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return freeze_raw(value)
    if isinstance(value, tuple | list):
        return tuple(_freeze_raw_value(item) for item in value)
    return value
