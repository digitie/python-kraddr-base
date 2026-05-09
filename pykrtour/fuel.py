"""주유소 POI에 공통으로 쓰는 유종과 업종 코드."""

from __future__ import annotations

from typing import Final

from ._enum import StrEnum


class FuelType(StrEnum):
    """TripMate에서 사용하는 표준 유종."""

    GASOLINE = "gasoline"
    PREMIUM_GASOLINE = "premium_gasoline"
    DIESEL = "diesel"
    LPG = "lpg"
    KEROSENE = "kerosene"
    ELECTRIC = "electric"
    HYDROGEN = "hydrogen"
    UNKNOWN = "unknown"


class FuelStationType(StrEnum):
    """주유소/충전소 업종 구분."""

    GAS_STATION = "gas_station"
    LPG_STATION = "lpg_station"
    BOTH = "both"
    EV_CHARGER = "ev_charger"
    HYDROGEN_STATION = "hydrogen_station"
    UNKNOWN = "unknown"


OPINET_PRODUCT_CODE_TO_FUEL_TYPE: Final[dict[str, FuelType]] = {
    "B027": FuelType.GASOLINE,
    "B034": FuelType.PREMIUM_GASOLINE,
    "D047": FuelType.DIESEL,
    "C004": FuelType.KEROSENE,
    "K015": FuelType.LPG,
}
"""Opinet 제품 코드에서 표준 유종으로 가는 mapping."""

FUEL_TYPE_TO_OPINET_PRODUCT_CODE: Final[dict[FuelType, str]] = {
    fuel_type: code for code, fuel_type in OPINET_PRODUCT_CODE_TO_FUEL_TYPE.items()
}
"""표준 유종에서 Opinet 제품 코드로 가는 mapping."""

OPINET_STATION_TYPE: Final[dict[str, FuelStationType]] = {
    "N": FuelStationType.GAS_STATION,
    "Y": FuelStationType.LPG_STATION,
    "C": FuelStationType.BOTH,
}
"""Opinet `LPG_YN` 업종 코드 mapping."""

BUDGET_FUEL_BRAND_CODES: Final[frozenset[str]] = frozenset({"RTE", "RTX", "NHO"})
"""Opinet 상표 코드 기준 알뜰주유소 계열."""

OPINET_TO_BJD_SIDO: Final[dict[str, str]] = {
    "01": "11",
    "02": "41",
    "03": "42",
    "04": "43",
    "05": "44",
    "06": "45",
    "07": "46",
    "08": "47",
    "09": "48",
    "10": "26",
    "11": "50",
    "14": "27",
    "15": "28",
    "16": "29",
    "17": "30",
    "18": "31",
    "19": "36",
}
"""Opinet 2자리 시도 코드에서 법정동 시도 prefix로 가는 mapping."""

BJD_TO_OPINET_SIDO: Final[dict[str, str]] = {
    value: key for key, value in OPINET_TO_BJD_SIDO.items()
}
BJD_LEGACY_TO_NEW_SIDO: Final[dict[str, str]] = {"42": "51", "45": "52"}
BJD_NEW_TO_LEGACY_SIDO: Final[dict[str, str]] = {
    value: key for key, value in BJD_LEGACY_TO_NEW_SIDO.items()
}


def fuel_type_from_opinet_product(code: str) -> FuelType:
    """Opinet 제품 코드를 TripMate 표준 유종으로 변환합니다."""

    try:
        return OPINET_PRODUCT_CODE_TO_FUEL_TYPE[str(code)]
    except KeyError as exc:
        raise ValueError(f"unknown Opinet product code: {code!r}") from exc


def opinet_product_code_for_fuel_type(fuel_type: FuelType | str) -> str:
    """TripMate 표준 유종을 Opinet 제품 코드로 변환합니다."""

    normalized = FuelType(str(fuel_type))
    if normalized is FuelType.UNKNOWN:
        raise ValueError("FuelType.UNKNOWN cannot be mapped to an Opinet product code")
    try:
        return FUEL_TYPE_TO_OPINET_PRODUCT_CODE[normalized]
    except KeyError as exc:
        raise ValueError(f"fuel type cannot be mapped to Opinet: {fuel_type!r}") from exc


def fuel_station_type_from_opinet_lpg_yn(value: str | None) -> FuelStationType:
    """Opinet `LPG_YN` 값을 주유소/충전소 업종 enum으로 변환합니다."""

    if value is None:
        return FuelStationType.UNKNOWN
    return OPINET_STATION_TYPE.get(str(value).strip().upper(), FuelStationType.UNKNOWN)


def is_budget_fuel_brand(brand_code: str | None) -> bool:
    """상표 코드가 알뜰주유소 계열인지 반환합니다."""

    if brand_code is None:
        return False
    return str(brand_code).strip().upper() in BUDGET_FUEL_BRAND_CODES


def opinet_sido_to_bjd(opinet_code: str) -> str:
    """Opinet 2자리 시도 코드를 법정동 시도 prefix로 변환합니다."""

    try:
        return OPINET_TO_BJD_SIDO[str(opinet_code)]
    except KeyError as exc:
        raise ValueError(f"unknown Opinet sido code: {opinet_code!r}") from exc


def bjd_sido_to_opinet(bjd_code: str) -> str:
    """법정동 시도 prefix를 Opinet 2자리 시도 코드로 변환합니다."""

    normalized = BJD_NEW_TO_LEGACY_SIDO.get(str(bjd_code), str(bjd_code))
    try:
        return BJD_TO_OPINET_SIDO[normalized]
    except KeyError as exc:
        raise ValueError(f"unknown BJD sido code: {bjd_code!r}") from exc
