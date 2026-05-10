"""TripMate POI에서 공유하는 좌표 값 객체와 변환 helper."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal, TypeAlias

from ._convert import first_value, strip_or_none, to_float_or_none
from ._enum import StrEnum

CoordinateKind: TypeAlias = Literal["latitude", "longitude"]

WGS84_CRS = "EPSG:4326"
KATEC_PROJ = (
    "+proj=tmerc +lat_0=38 +lon_0=128 +k=0.9999 +x_0=400000 +y_0=600000 "
    "+ellps=bessel +units=m "
    "+towgs84=-115.80,474.99,674.11,1.16,-2.31,-1.63,6.43 +no_defs"
)
KATEC_CRS = KATEC_PROJ
EPSG5174_CRS = "EPSG:5174"
AIRKOREA_TM_CRS = "EPSG:2097"
KMA_DFS_CRS = "KMA_DFS"

KMA_DFS_NX = 149
KMA_DFS_NY = 253

_KMA_RE = 6371.00877
_KMA_GRID = 5.0
_KMA_SLAT1 = 30.0
_KMA_SLAT2 = 60.0
_KMA_OLON = 126.0
_KMA_OLAT = 38.0
_KMA_XO = 43
_KMA_YO = 136

_HEMISPHERE_SIGNS = {"N": 1, "E": 1, "S": -1, "W": -1}
_HEMISPHERE_WORDS = {"NORTH": "N", "EAST": "E", "SOUTH": "S", "WEST": "W"}
_HEMISPHERE_LETTER_RE = re.compile(r"(?<![A-Z])([NSEW])(?![A-Z])")
_NUMBER_RE = re.compile(r"[+-]?\d+(?:\.\d+)?")


class CoordinateReferenceSystem(StrEnum):
    """TripMate POI layer가 명시적으로 다루는 좌표계."""

    WGS84 = WGS84_CRS
    KATEC = KATEC_CRS
    AIRKOREA_TM = AIRKOREA_TM_CRS
    KMA_DFS = KMA_DFS_CRS
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class Wgs84Point:
    """WGS84 경도/위도 좌표.

    축 순서는 항상 `(lon, lat)`입니다. GeoJSON, PostGIS WKT, 대부분의 GIS 저장
    경계에서 쓰기 좋은 순서입니다.
    """

    lon: float
    lat: float

    def __post_init__(self) -> None:
        lon = _finite_float(self.lon, "lon")
        lat = _finite_float(self.lat, "lat")
        validate_lonlat(lon, lat)
        object.__setattr__(self, "lon", lon)
        object.__setattr__(self, "lat", lat)

    @property
    def crs(self) -> CoordinateReferenceSystem:
        return CoordinateReferenceSystem.WGS84

    @property
    def longitude(self) -> float:
        return self.lon

    @property
    def latitude(self) -> float:
        return self.lat

    @property
    def lonlat(self) -> tuple[float, float]:
        return self.lon, self.lat

    @property
    def latlon(self) -> tuple[float, float]:
        return self.lat, self.lon

    def as_tuple(self) -> tuple[float, float]:
        """`(lon, lat)` 순서로 반환합니다."""

        return self.lonlat

    def as_lon_lat(self) -> tuple[float, float]:
        """`(lon, lat)` 순서 명시 alias입니다."""

        return self.lonlat

    def as_lat_lon(self) -> tuple[float, float]:
        """UI 라이브러리에서 자주 쓰는 `(lat, lon)` 순서로 반환합니다."""

        return self.latlon

    def as_geojson_position(self) -> tuple[float, float]:
        """GeoJSON Position 규칙에 맞춰 `(lon, lat)` 순서로 반환합니다."""

        return self.lonlat

    def to_wkt(self) -> str:
        """PostGIS 등에 사용할 WKT Point 문자열을 반환합니다."""

        return f"POINT({self.lon} {self.lat})"

    def to_latlon(self) -> LatLon:
        """`LatLon(lat, lon)` 값 객체로 변환합니다."""

        return LatLon(self.lat, self.lon)

    def distance_to_m(self, other: Wgs84Point | LatLon) -> float:
        """다른 WGS84 좌표까지의 대권 거리를 미터 단위로 반환합니다."""

        target = other.to_wgs84_point() if isinstance(other, LatLon) else other
        return haversine_distance_m(self, target)


@dataclass(frozen=True, slots=True)
class LatLon:
    """WGS84 위도/경도 좌표.

    축 순서는 `(lat, lon)`입니다. 사람이 읽는 UI, 기상청/대기 API처럼 위도를 먼저
    받는 경계에서 사용합니다.
    """

    lat: float
    lon: float

    def __post_init__(self) -> None:
        lat = _finite_float(self.lat, "lat")
        lon = _finite_float(self.lon, "lon")
        validate_latlon(lat, lon)
        object.__setattr__(self, "lat", lat)
        object.__setattr__(self, "lon", lon)

    @property
    def crs(self) -> CoordinateReferenceSystem:
        return CoordinateReferenceSystem.WGS84

    @property
    def latitude(self) -> float:
        return self.lat

    @property
    def longitude(self) -> float:
        return self.lon

    @property
    def latlon(self) -> tuple[float, float]:
        return self.lat, self.lon

    @property
    def lonlat(self) -> tuple[float, float]:
        return self.lon, self.lat

    def as_tuple(self) -> tuple[float, float]:
        """`(lat, lon)` 순서로 반환합니다."""

        return self.latlon

    def to_wgs84_point(self) -> Wgs84Point:
        """`Wgs84Point(lon, lat)` 값 객체로 변환합니다."""

        return Wgs84Point(self.lon, self.lat)

    def to_kma_grid(self) -> KmaGridPoint:
        """기상청 DFS 격자 좌표로 변환합니다."""

        return wgs84_to_kma_grid(self.lat, self.lon)


@dataclass(frozen=True, slots=True)
class ProjectedPoint:
    """평면 좌표계의 `(x, y)` 좌표."""

    x: float
    y: float
    crs: str = CoordinateReferenceSystem.UNKNOWN.value

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", _finite_float(self.x, "x"))
        object.__setattr__(self, "y", _finite_float(self.y, "y"))
        object.__setattr__(self, "crs", str(self.crs))

    def as_tuple(self) -> tuple[float, float]:
        return self.x, self.y

    def as_x_y(self) -> tuple[float, float]:
        return self.as_tuple()


@dataclass(frozen=True, slots=True)
class KatecPoint:
    """KATEC `(x, y)` 좌표."""

    x: float
    y: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", _finite_float(self.x, "x"))
        object.__setattr__(self, "y", _finite_float(self.y, "y"))

    @property
    def crs(self) -> CoordinateReferenceSystem:
        return CoordinateReferenceSystem.KATEC

    @property
    def katec_x(self) -> float:
        return self.x

    @property
    def katec_y(self) -> float:
        return self.y

    def as_tuple(self) -> tuple[float, float]:
        return self.x, self.y

    def as_x_y(self) -> tuple[float, float]:
        return self.as_tuple()

    def to_wgs84(self) -> Wgs84Point:
        return katec_to_wgs84(self.x, self.y)


@dataclass(frozen=True, slots=True)
class AirKoreaTmPoint:
    """AirKorea 근접 측정소 API에서 쓰는 TM `(tm_x, tm_y)` 좌표."""

    tm_x: float
    tm_y: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "tm_x", _finite_float(self.tm_x, "tm_x"))
        object.__setattr__(self, "tm_y", _finite_float(self.tm_y, "tm_y"))

    @property
    def crs(self) -> CoordinateReferenceSystem:
        return CoordinateReferenceSystem.AIRKOREA_TM

    @property
    def x(self) -> float:
        return self.tm_x

    @property
    def y(self) -> float:
        return self.tm_y

    def as_tuple(self) -> tuple[float, float]:
        return self.tm_x, self.tm_y

    def to_wgs84(self) -> Wgs84Point:
        return airkorea_tm_to_wgs84(self.tm_x, self.tm_y)


@dataclass(frozen=True, slots=True)
class KmaGridPoint:
    """기상청 DFS `(nx, ny)` 격자 좌표."""

    nx: int
    ny: int

    def __post_init__(self) -> None:
        nx = int(self.nx)
        ny = int(self.ny)
        validate_kma_grid(nx, ny)
        object.__setattr__(self, "nx", nx)
        object.__setattr__(self, "ny", ny)

    @property
    def crs(self) -> CoordinateReferenceSystem:
        return CoordinateReferenceSystem.KMA_DFS

    def as_tuple(self) -> tuple[int, int]:
        return self.nx, self.ny

    def to_latlon(self) -> LatLon:
        lat, lon = kma_grid_to_latlon(self.nx, self.ny)
        return LatLon(lat, lon)

    def to_wgs84_point(self) -> Wgs84Point:
        return self.to_latlon().to_wgs84_point()


def validate_latlon(lat: float, lon: float) -> None:
    """`(lat, lon)` 순서의 WGS84 좌표 범위를 검증합니다."""

    if not -90.0 <= lat <= 90.0:
        raise ValueError("lat must be between -90 and 90")
    if not -180.0 <= lon <= 180.0:
        raise ValueError("lon must be between -180 and 180")


def validate_lonlat(lon: float, lat: float) -> None:
    """`(lon, lat)` 순서의 WGS84 좌표 범위를 검증합니다."""

    validate_latlon(lat, lon)


def validate_kma_grid(nx: int, ny: int) -> None:
    """공식 기상청 DFS 격자 범위를 검증합니다."""

    if not 1 <= nx <= KMA_DFS_NX:
        raise ValueError(f"nx must be between 1 and {KMA_DFS_NX}")
    if not 1 <= ny <= KMA_DFS_NY:
        raise ValueError(f"ny must be between 1 and {KMA_DFS_NY}")


def coerce_latlon(
    value: LatLon | Wgs84Point | tuple[float, float] | Mapping[str, Any] | None = None,
    *,
    lat: float | None = None,
    lon: float | None = None,
) -> LatLon:
    """지원하는 WGS84 입력을 `(lat, lon)` 순서의 `LatLon`으로 정규화합니다."""

    if value is not None and (lat is not None or lon is not None):
        raise ValueError("Provide either coordinate value or lat/lon keywords, not both")
    if isinstance(value, LatLon):
        return value
    if isinstance(value, Wgs84Point):
        return value.to_latlon()
    if isinstance(value, tuple):
        if len(value) != 2:
            raise ValueError("coordinate tuple must be (lat, lon)")
        return LatLon(float(value[0]), float(value[1]))
    if isinstance(value, Mapping):
        point = coordinate_from_mapping(value)
        if point is None:
            raise ValueError("mapping must contain lat/lon or latitude/longitude")
        return point.to_latlon()
    if lat is None or lon is None:
        raise ValueError("Both lat and lon are required")
    return LatLon(lat, lon)


def coerce_wgs84_point(
    value: Wgs84Point | LatLon | tuple[float, float] | Mapping[str, Any] | None = None,
    *,
    lon: float | None = None,
    lat: float | None = None,
) -> Wgs84Point:
    """지원하는 WGS84 입력을 `(lon, lat)` 순서의 `Wgs84Point`로 정규화합니다."""

    if value is not None and (lat is not None or lon is not None):
        raise ValueError("Provide either coordinate value or lon/lat keywords, not both")
    if isinstance(value, Wgs84Point):
        return value
    if isinstance(value, LatLon):
        return value.to_wgs84_point()
    if isinstance(value, tuple):
        if len(value) != 2:
            raise ValueError("coordinate tuple must be (lon, lat)")
        return Wgs84Point(float(value[0]), float(value[1]))
    if isinstance(value, Mapping):
        point = coordinate_from_mapping(value)
        if point is None:
            raise ValueError("mapping must contain lon/lat or longitude/latitude")
        return point
    if lon is None or lat is None:
        raise ValueError("Both lon and lat are required")
    return Wgs84Point(lon, lat)


def coordinate_from_mapping(row: Mapping[str, Any]) -> Wgs84Point | None:
    """일반적인 좌표 key를 가진 mapping에서 WGS84 좌표를 반환합니다."""

    lon = to_float_or_none(
        first_value(row, "lon", "lng", "longitude", "mapx", "x", "lcLongitude", "경도")
    )
    lat = to_float_or_none(
        first_value(row, "lat", "latitude", "mapy", "y", "lcLatitude", "위도")
    )
    if lon is None or lat is None:
        return None
    return Wgs84Point(lon, lat)


def to_decimal_degrees(value: Any, *, kind: CoordinateKind | None = None) -> float:
    """decimal 또는 DMS 유사 좌표 값을 decimal degrees로 정규화합니다."""

    text = strip_or_none(value)
    if text is None:
        raise ValueError("coordinate value is empty")

    normalized = text.upper().replace("º", "°")
    hemisphere = _extract_hemisphere(normalized)
    numbers = [float(part) for part in _NUMBER_RE.findall(normalized)]
    if not numbers:
        raise ValueError(f"invalid coordinate value: {value!r}")

    degrees = numbers[0]
    minutes = numbers[1] if len(numbers) >= 2 else 0.0
    seconds = numbers[2] if len(numbers) >= 3 else 0.0
    if minutes < 0 or seconds < 0 or minutes >= 60 or seconds >= 60:
        raise ValueError(f"invalid coordinate minutes/seconds: {value!r}")

    sign = -1 if degrees < 0 else 1
    if hemisphere is not None:
        hemisphere_sign = _HEMISPHERE_SIGNS[hemisphere]
        if degrees < 0 and hemisphere_sign > 0:
            raise ValueError(f"conflicting coordinate sign and hemisphere: {value!r}")
        sign = hemisphere_sign

    decimal = sign * (abs(degrees) + minutes / 60 + seconds / 3600)
    return _validate_decimal_degrees(decimal, kind=kind)


def to_decimal_degrees_or_none(
    value: Any,
    *,
    kind: CoordinateKind | None = None,
) -> float | None:
    """빈 좌표 값이면 `None`, 값이 있으면 decimal degrees를 반환합니다."""

    if strip_or_none(value) is None:
        return None
    return to_decimal_degrees(value, kind=kind)


def haversine_distance_m(
    origin: Wgs84Point | LatLon,
    target: Wgs84Point | LatLon,
) -> float:
    """두 WGS84 좌표 사이의 대권 거리를 미터 단위로 반환합니다."""

    first = origin.to_wgs84_point() if isinstance(origin, LatLon) else origin
    second = target.to_wgs84_point() if isinstance(target, LatLon) else target
    radius_m = 6371008.8
    lat1 = math.radians(first.lat)
    lat2 = math.radians(second.lat)
    dlat = lat2 - lat1
    dlon = math.radians(second.lon - first.lon)
    haversine = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 2 * radius_m * math.asin(math.sqrt(haversine))


def transform_xy(
    x: float,
    y: float,
    *,
    source_crs: str,
    target_crs: str,
) -> tuple[float, float]:
    """`pyproj`를 사용해 `(x, y)` 좌표를 다른 좌표계로 변환합니다."""

    transformer = _transformer(source_crs, target_crs)
    new_x, new_y = transformer.transform(float(x), float(y))
    return float(new_x), float(new_y)


def katec_to_wgs84(x: float, y: float) -> Wgs84Point:
    """KATEC `(x, y)`를 WGS84 `Wgs84Point(lon, lat)`로 변환합니다."""

    lon, lat = transform_xy(x, y, source_crs=KATEC_CRS, target_crs=WGS84_CRS)
    return Wgs84Point(lon, lat)


def wgs84_to_katec(lon: float, lat: float) -> KatecPoint:
    """WGS84 `(lon, lat)`를 KATEC `(x, y)`로 변환합니다."""

    point = Wgs84Point(lon, lat)
    x, y = transform_xy(point.lon, point.lat, source_crs=WGS84_CRS, target_crs=KATEC_CRS)
    return KatecPoint(x, y)


def epsg5174_to_wgs84(x: float, y: float) -> Wgs84Point:
    """EPSG:5174 `(x, y)`를 WGS84 `Wgs84Point(lon, lat)`로 변환합니다."""

    lon, lat = transform_xy(x, y, source_crs=EPSG5174_CRS, target_crs=WGS84_CRS)
    return Wgs84Point(lon, lat)


def wgs84_to_epsg5174(lon: float, lat: float) -> KatecPoint:
    """WGS84 `(lon, lat)`를 EPSG:5174 `(x, y)`로 변환합니다."""

    point = Wgs84Point(lon, lat)
    x, y = transform_xy(point.lon, point.lat, source_crs=WGS84_CRS, target_crs=EPSG5174_CRS)
    return KatecPoint(x, y)


def airkorea_tm_to_wgs84(tm_x: float, tm_y: float) -> Wgs84Point:
    """AirKorea TM `(tm_x, tm_y)`를 WGS84 `Wgs84Point(lon, lat)`로 변환합니다."""

    lon, lat = transform_xy(tm_x, tm_y, source_crs=AIRKOREA_TM_CRS, target_crs=WGS84_CRS)
    return Wgs84Point(lon, lat)


def wgs84_to_airkorea_tm(lon: float, lat: float) -> AirKoreaTmPoint:
    """WGS84 `(lon, lat)`를 AirKorea TM `(tm_x, tm_y)`로 변환합니다."""

    point = Wgs84Point(lon, lat)
    tm_x, tm_y = transform_xy(
        point.lon,
        point.lat,
        source_crs=WGS84_CRS,
        target_crs=AIRKOREA_TM_CRS,
    )
    return AirKoreaTmPoint(tm_x, tm_y)


def wgs84_to_kma_grid(latitude: float, longitude: float) -> KmaGridPoint:
    """WGS84 `(latitude, longitude)`를 기상청 DFS `KmaGridPoint`로 변환합니다."""

    validate_latlon(float(latitude), float(longitude))
    nx, ny = _kma_to_grid(float(latitude), float(longitude))
    return KmaGridPoint(nx, ny)


def kma_grid_to_latlon(nx: int, ny: int) -> tuple[float, float]:
    """기상청 DFS `(nx, ny)`를 WGS84 `(lat, lon)`으로 역변환합니다."""

    return _kma_to_latlon(nx, ny)


def kma_grid_to_wgs84(nx: int, ny: int) -> Wgs84Point:
    """기상청 DFS `(nx, ny)`를 WGS84 `Wgs84Point(lon, lat)`로 역변환합니다."""

    lat, lon = kma_grid_to_latlon(nx, ny)
    return Wgs84Point(lon, lat)


def _finite_float(value: Any, field_name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field_name} must be finite")
    return result


def _validate_decimal_degrees(value: float, *, kind: CoordinateKind | None) -> float:
    if not math.isfinite(value):
        raise ValueError(f"coordinate must be finite: {value!r}")
    if kind == "latitude" and not -90 <= value <= 90:
        raise ValueError(f"latitude out of range: {value!r}")
    if kind == "longitude" and not -180 <= value <= 180:
        raise ValueError(f"longitude out of range: {value!r}")
    if kind is None and not -180 <= value <= 180:
        raise ValueError(f"coordinate out of range: {value!r}")
    return value


def _extract_hemisphere(value: str) -> str | None:
    hemispheres = [
        hemisphere
        for word, hemisphere in _HEMISPHERE_WORDS.items()
        if re.search(rf"\b{word}\b", value)
    ]
    hemispheres.extend(_HEMISPHERE_LETTER_RE.findall(value))
    if not hemispheres:
        return None
    unique = set(hemispheres)
    if len(unique) > 1:
        raise ValueError(f"coordinate has multiple hemispheres: {value!r}")
    return hemispheres[0]


@lru_cache(maxsize=32)
def _transformer(source_crs: str, target_crs: str):  # type: ignore[no-untyped-def]
    try:
        from pyproj import Transformer
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency guard
        raise RuntimeError("pyproj is required for this coordinate conversion") from exc
    return Transformer.from_crs(source_crs, target_crs, always_xy=True)


def _kma_project() -> tuple[float, float, float, float, float, float]:
    degrad = math.pi / 180.0
    re = _KMA_RE / _KMA_GRID
    slat1 = _KMA_SLAT1 * degrad
    slat2 = _KMA_SLAT2 * degrad
    olon = _KMA_OLON * degrad
    olat = _KMA_OLAT * degrad

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(
        math.pi * 0.25 + slat1 * 0.5
    )
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = (sf**sn) * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re * sf / (ro**sn)
    return degrad, re, sn, sf, ro, olon


def _kma_to_grid(lat: float, lon: float) -> tuple[int, int]:
    degrad, re, sn, sf, ro, olon = _kma_project()
    ra = math.tan(math.pi * 0.25 + lat * degrad * 0.5)
    ra = re * sf / (ra**sn)
    theta = lon * degrad - olon
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn
    nx = int(ra * math.sin(theta) + _KMA_XO + 0.5)
    ny = int(ro - ra * math.cos(theta) + _KMA_YO + 0.5)
    return nx, ny


def _kma_to_latlon(nx: int, ny: int) -> tuple[float, float]:
    validate_kma_grid(int(nx), int(ny))
    degrad, re, sn, sf, ro, olon = _kma_project()
    xn = int(nx) - _KMA_XO
    yn = ro - (int(ny) - _KMA_YO)
    ra = math.sqrt(xn * xn + yn * yn)
    if sn < 0:
        ra = -ra
    alat = (re * sf / ra) ** (1.0 / sn)
    alat = 2.0 * math.atan(alat) - math.pi * 0.5

    if abs(xn) <= 0.0:
        theta = 0.0
    elif abs(yn) <= 0.0:
        theta = math.pi * 0.5
        if xn < 0:
            theta = -theta
    else:
        theta = math.atan2(xn, yn)

    alon = theta / sn + olon
    return alat / degrad, alon / degrad
