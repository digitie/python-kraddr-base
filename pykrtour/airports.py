"""한국 공항 POI 코드와 번들 메타데이터."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from types import MappingProxyType

from ._enum import StrEnum
from .coordinates import Wgs84Point, coerce_wgs84_point, haversine_distance_m


class AirportProvider(StrEnum):
    """한국 공항 API provider 구분."""

    KAC = "kac"
    IIAC = "iiac"


class KoreanAirportCode(StrEnum):
    """TripMate에서 우선 지원하는 한국 IATA 공항 코드."""

    ICN = "ICN"
    GMP = "GMP"
    PUS = "PUS"
    CJU = "CJU"
    TAE = "TAE"
    CJJ = "CJJ"
    KWJ = "KWJ"
    RSU = "RSU"
    USN = "USN"
    MWX = "MWX"
    YNY = "YNY"
    KUV = "KUV"
    HIN = "HIN"
    WJU = "WJU"
    KPO = "KPO"
    MPK = "MPK"


class AirportType(StrEnum):
    """공항 규모/운영 상태."""

    LARGE = "large_airport"
    MEDIUM = "medium_airport"
    SMALL = "small_airport"
    CLOSED = "closed"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class AirportInfo:
    """한국 공항 POI 메타데이터."""

    code: str
    provider: AirportProvider
    name_english: str
    name_korean: str
    icao_code: str | None
    municipality: str
    coordinate: Wgs84Point | None
    elevation_ft: int | None
    airport_type: AirportType
    active: bool = True
    source: str = "OurAirports airports.csv and historic Korean airport references"


def _airport(
    code: KoreanAirportCode,
    provider: AirportProvider,
    name_english: str,
    *,
    name_korean: str,
    icao_code: str | None,
    municipality: str,
    latitude: float | None,
    longitude: float | None,
    elevation_ft: int | None,
    airport_type: AirportType,
    active: bool = True,
    source: str = "OurAirports airports.csv, last checked 2026-05-06",
) -> AirportInfo:
    coordinate = None
    if latitude is not None and longitude is not None:
        coordinate = Wgs84Point(longitude, latitude)
    return AirportInfo(
        code=code.value,
        provider=provider,
        name_english=name_english,
        name_korean=name_korean,
        icao_code=icao_code,
        municipality=municipality,
        coordinate=coordinate,
        elevation_ft=elevation_ft,
        airport_type=airport_type,
        active=active,
        source=source,
    )


AIRPORTS: MappingProxyType[str, AirportInfo] = MappingProxyType(
    {
        "ICN": _airport(
            KoreanAirportCode.ICN,
            AirportProvider.IIAC,
            "Incheon International Airport",
            name_korean="인천국제공항",
            icao_code="RKSI",
            municipality="Seoul/Incheon",
            latitude=37.469101,
            longitude=126.450996,
            elevation_ft=23,
            airport_type=AirportType.LARGE,
        ),
        "GMP": _airport(
            KoreanAirportCode.GMP,
            AirportProvider.KAC,
            "Gimpo International Airport",
            name_korean="김포국제공항",
            icao_code="RKSS",
            municipality="Seoul",
            latitude=37.5583,
            longitude=126.791,
            elevation_ft=59,
            airport_type=AirportType.LARGE,
        ),
        "PUS": _airport(
            KoreanAirportCode.PUS,
            AirportProvider.KAC,
            "Gimhae International Airport",
            name_korean="김해국제공항",
            icao_code="RKPK",
            municipality="Busan",
            latitude=35.179501,
            longitude=128.938004,
            elevation_ft=6,
            airport_type=AirportType.LARGE,
        ),
        "CJU": _airport(
            KoreanAirportCode.CJU,
            AirportProvider.KAC,
            "Jeju International Airport",
            name_korean="제주국제공항",
            icao_code="RKPC",
            municipality="Jeju City",
            latitude=33.512058,
            longitude=126.492548,
            elevation_ft=118,
            airport_type=AirportType.LARGE,
        ),
        "TAE": _airport(
            KoreanAirportCode.TAE,
            AirportProvider.KAC,
            "Daegu International Airport",
            name_korean="대구국제공항",
            icao_code="RKTN",
            municipality="Daegu",
            latitude=35.894394,
            longitude=128.656989,
            elevation_ft=116,
            airport_type=AirportType.LARGE,
        ),
        "CJJ": _airport(
            KoreanAirportCode.CJJ,
            AirportProvider.KAC,
            "Cheongju International Airport",
            name_korean="청주국제공항",
            icao_code="RKTU",
            municipality="Cheongju",
            latitude=36.71556,
            longitude=127.500289,
            elevation_ft=191,
            airport_type=AirportType.LARGE,
        ),
        "KWJ": _airport(
            KoreanAirportCode.KWJ,
            AirportProvider.KAC,
            "Gwangju Airport",
            name_korean="광주공항",
            icao_code="RKJJ",
            municipality="Gwangju",
            latitude=35.123173,
            longitude=126.805444,
            elevation_ft=39,
            airport_type=AirportType.MEDIUM,
        ),
        "RSU": _airport(
            KoreanAirportCode.RSU,
            AirportProvider.KAC,
            "Yeosu Airport",
            name_korean="여수공항",
            icao_code="RKJY",
            municipality="Yeosu",
            latitude=34.84230041503906,
            longitude=127.61699676513672,
            elevation_ft=53,
            airport_type=AirportType.MEDIUM,
        ),
        "USN": _airport(
            KoreanAirportCode.USN,
            AirportProvider.KAC,
            "Ulsan Airport",
            name_korean="울산공항",
            icao_code="RKPU",
            municipality="Ulsan",
            latitude=35.59349823,
            longitude=129.352005005,
            elevation_ft=45,
            airport_type=AirportType.MEDIUM,
        ),
        "MWX": _airport(
            KoreanAirportCode.MWX,
            AirportProvider.KAC,
            "Muan International Airport",
            name_korean="무안국제공항",
            icao_code="RKJB",
            municipality="Muan",
            latitude=34.991406,
            longitude=126.382814,
            elevation_ft=35,
            airport_type=AirportType.LARGE,
        ),
        "YNY": _airport(
            KoreanAirportCode.YNY,
            AirportProvider.KAC,
            "Yangyang International Airport",
            name_korean="양양국제공항",
            icao_code="RKNY",
            municipality="Yangyang",
            latitude=38.060481,
            longitude=128.669822,
            elevation_ft=241,
            airport_type=AirportType.LARGE,
        ),
        "KUV": _airport(
            KoreanAirportCode.KUV,
            AirportProvider.KAC,
            "Gunsan Airport",
            name_korean="군산공항",
            icao_code="RKJK",
            municipality="Gunsan",
            latitude=35.903801,
            longitude=126.615997,
            elevation_ft=29,
            airport_type=AirportType.MEDIUM,
        ),
        "HIN": _airport(
            KoreanAirportCode.HIN,
            AirportProvider.KAC,
            "Sacheon Airport",
            name_korean="사천공항",
            icao_code="RKPS",
            municipality="Sacheon",
            latitude=35.088591,
            longitude=128.071747,
            elevation_ft=25,
            airport_type=AirportType.MEDIUM,
        ),
        "WJU": _airport(
            KoreanAirportCode.WJU,
            AirportProvider.KAC,
            "Wonju Airport",
            name_korean="원주공항",
            icao_code="RKNW",
            municipality="Wonju",
            latitude=37.437113,
            longitude=127.960051,
            elevation_ft=329,
            airport_type=AirportType.MEDIUM,
        ),
        "KPO": _airport(
            KoreanAirportCode.KPO,
            AirportProvider.KAC,
            "Pohang Gyeongju Airport",
            name_korean="포항경주공항",
            icao_code="RKTH",
            municipality="Pohang",
            latitude=35.987955,
            longitude=129.420383,
            elevation_ft=70,
            airport_type=AirportType.MEDIUM,
        ),
        "MPK": _airport(
            KoreanAirportCode.MPK,
            AirportProvider.KAC,
            "Mokpo Airport",
            name_korean="목포공항",
            icao_code="RKJM",
            municipality="Mokpo",
            latitude=34.76,
            longitude=126.38027777,
            elevation_ft=None,
            airport_type=AirportType.CLOSED,
            active=False,
            source="Historic airport coordinate reference, last checked 2026-05-06",
        ),
    }
)

SUPPORTED_AIRPORT_CODES = frozenset(AIRPORTS)
KAC_AIRPORTS = frozenset(
    code for code, airport in AIRPORTS.items() if airport.provider is AirportProvider.KAC
)
IIAC_AIRPORTS = frozenset(
    code for code, airport in AIRPORTS.items() if airport.provider is AirportProvider.IIAC
)


def normalize_airport_code(value: str | KoreanAirportCode) -> str:
    """IATA 공항 코드를 대문자 3자리 문자열로 정규화합니다."""

    code = str(value.value if isinstance(value, KoreanAirportCode) else value).strip().upper()
    if len(code) != 3 or not code.isalpha():
        raise ValueError(f"airport code must be a 3-letter IATA code: {value!r}")
    return code


def get_airport(airport_code: str | KoreanAirportCode) -> AirportInfo:
    """지원 공항 코드의 번들 메타데이터를 반환합니다."""

    code = normalize_airport_code(airport_code)
    try:
        return AIRPORTS[code]
    except KeyError as exc:
        raise KeyError(f"unsupported Korean airport code: {airport_code!r}") from exc


def get_airport_or_none(airport_code: str | KoreanAirportCode | None) -> AirportInfo | None:
    """공항 코드가 없거나 지원하지 않으면 `None`을 반환합니다."""

    if airport_code is None:
        return None
    try:
        return get_airport(airport_code)
    except (KeyError, ValueError):
        return None


def iter_airports(
    *,
    provider: AirportProvider | str | None = None,
    active: bool | None = None,
) -> Iterator[AirportInfo]:
    """공급자와 활성 상태로 필터링한 번들 공항을 순회합니다."""

    provider_value = AirportProvider(str(provider).lower()) if provider is not None else None
    airports = sorted(AIRPORTS.values(), key=lambda airport: airport.code)
    for airport in airports:
        if provider_value is not None and airport.provider is not provider_value:
            continue
        if active is not None and airport.active is not active:
            continue
        yield airport


def list_airports(
    *,
    provider: AirportProvider | str | None = None,
    active: bool | None = None,
) -> tuple[AirportInfo, ...]:
    """공급자와 활성 상태로 필터링한 번들 공항 목록을 반환합니다."""

    return tuple(iter_airports(provider=provider, active=active))


def nearest_airport(
    coordinate: Wgs84Point | tuple[float, float] | None = None,
    *,
    lon: float | None = None,
    lat: float | None = None,
    provider: AirportProvider | str | None = None,
    active: bool | None = True,
) -> AirportInfo | None:
    """WGS84 위치 기준 가장 가까운 번들 공항을 반환합니다.

    `coordinate` tuple은 `Wgs84Point`와 같은 `(lon, lat)` 순서입니다.
    """

    origin = coerce_wgs84_point(coordinate, lon=lon, lat=lat)
    candidates = [
        airport
        for airport in iter_airports(provider=provider, active=active)
        if airport.coordinate is not None
    ]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda airport: haversine_distance_m(origin, airport.coordinate),  # type: ignore[arg-type]
    )
