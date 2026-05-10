"""장소의 가장 작은 공통 위치 값 객체."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, Final, Literal, TypeAlias

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from ._convert import first_value, strip_or_none
from .addresses import (
    AddressCodeSet,
    LegalDongCode,
    RoadNameAddressCode,
    RoadNameCode,
    SigunguCode,
    address_code_set_from_mapping,
    coerce_legal_dong_code,
    coerce_road_name_address_code,
    coerce_road_name_code,
    coerce_sigungu_code,
    legal_dong_code_from_mapping,
    normalize_building_number,
    normalize_underground_flag,
    sigungu_code_from_mapping,
)
from .coordinates import (
    WGS84_CRS,
    AirKoreaTmPoint,
    KatecPoint,
    KmaGridPoint,
    LatLon,
    Wgs84Point,
    airkorea_tm_to_wgs84,
    coordinate_from_mapping,
    haversine_distance_m,
    wgs84_to_airkorea_tm,
    wgs84_to_katec,
    wgs84_to_kma_grid,
)

GeometryFormat: TypeAlias = Literal["wkt", "ewkt", "geojson"]
TupleOrder: TypeAlias = Literal["lon_lat", "lat_lon"]

JIBUN_ADDRESS_KEYS: Final[tuple[str, ...]] = (
    "jibun_address",
    "lot_address",
    "lotAddress",
    "jibunAddress",
    "address",
    "addr",
    "LCTN_WHOL_ADDR",
    "LOTNO_ADDR",
    "VAN_ADR",
    "주소",
    "지번주소",
    "소재지",
)
ROAD_ADDRESS_KEYS: Final[tuple[str, ...]] = (
    "road_address",
    "roadAddress",
    "roadAddr",
    "roadAddrPart1",
    "roadNmAddr",
    "NEW_ADR",
    "ROAD_NM_ADDR",
    "ROAD_NM_WHOL_ADDR",
    "도로명주소",
)
POSTAL_CODE_KEYS: Final[tuple[str, ...]] = (
    "postal_code",
    "postalCode",
    "zip",
    "zipCode",
    "zipNo",
    "road_zip",
    "우편번호",
)
SIDO_NAME_KEYS: Final[tuple[str, ...]] = ("sido_name", "siNm", "sido", "시도")
SIGUNGU_NAME_KEYS: Final[tuple[str, ...]] = (
    "sigungu_name",
    "sggNm",
    "sigungu",
    "시군구",
)
EUP_MYEON_DONG_NAME_KEYS: Final[tuple[str, ...]] = (
    "eup_myeon_dong_name",
    "emdNm",
    "emd",
    "읍면동",
    "법정동",
)
RI_NAME_KEYS: Final[tuple[str, ...]] = ("ri_name", "liNm", "ri", "리")

_LOCATION_MODEL_CONFIG: Final[ConfigDict] = ConfigDict(
    extra="forbid",
    frozen=True,
    from_attributes=True,
    populate_by_name=True,
    str_strip_whitespace=True,
)


class PlaceCoordinate(BaseModel):
    """장소의 기준 좌표 DTO.

    TripMate 하위 라이브러리의 장소형 데이터는 이 클래스를 좌표 경계 모델로 사용합니다.
    내부 기준은 WGS84 `EPSG:4326`이며 축 순서는 저장과 geometry 생성에 유리한
    `(lon, lat)`입니다. 지오코딩과 리버스 지오코딩은 이 클래스의 책임이 아닙니다.
    """

    model_config = _LOCATION_MODEL_CONFIG

    lon: float = Field(
        validation_alias=AliasChoices(
            "lon",
            "lng",
            "longitude",
            "mapx",
            "x",
            "lcLongitude",
            "경도",
        )
    )
    lat: float = Field(
        validation_alias=AliasChoices(
            "lat",
            "latitude",
            "mapy",
            "y",
            "lcLatitude",
            "위도",
        )
    )
    altitude_m: float | None = None
    accuracy_m: float | None = None
    srid: int = 4326

    @field_validator("lon", "lat", mode="before")
    @classmethod
    def _normalize_axis(cls, value: Any) -> float:
        return _finite_float(value, "coordinate")

    @field_validator("altitude_m", "accuracy_m", mode="before")
    @classmethod
    def _normalize_optional_float(cls, value: Any) -> float | None:
        return _float_or_none(value)

    @field_validator("srid")
    @classmethod
    def _validate_srid(cls, value: int) -> int:
        if int(value) != 4326:
            raise ValueError("PlaceCoordinate stores only WGS84 EPSG:4326 values")
        return int(value)

    def model_post_init(self, __context: Any) -> None:
        if not -180.0 <= self.lon <= 180.0:
            raise ValueError("lon must be between -180 and 180")
        if not -90.0 <= self.lat <= 90.0:
            raise ValueError("lat must be between -90 and 90")
        if self.accuracy_m is not None and self.accuracy_m < 0:
            raise ValueError("accuracy_m must be greater than or equal to 0")

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> PlaceCoordinate | None:
        """provider row에서 흔한 좌표 key를 찾아 기준 좌표 DTO를 반환합니다."""

        point = coordinate_from_mapping(row)
        if point is None:
            return None
        return cls(
            lon=point.lon,
            lat=point.lat,
            altitude_m=first_value(row, "altitude_m", "altitude", "고도"),
            accuracy_m=first_value(row, "accuracy_m", "accuracy", "정확도"),
        )

    @classmethod
    def from_wgs84_point(cls, point: Wgs84Point) -> PlaceCoordinate:
        """`Wgs84Point(lon, lat)`에서 기준 좌표 DTO를 만듭니다."""

        return cls(lon=point.lon, lat=point.lat)

    @classmethod
    def from_latlon(cls, point: LatLon) -> PlaceCoordinate:
        """`LatLon(lat, lon)`에서 기준 좌표 DTO를 만듭니다."""

        return cls(lon=point.lon, lat=point.lat)

    @classmethod
    def from_tuple(
        cls,
        value: tuple[float, float],
        *,
        order: TupleOrder = "lon_lat",
    ) -> PlaceCoordinate:
        """tuple 좌표를 기준 좌표 DTO로 변환합니다."""

        if len(value) != 2:
            raise ValueError("coordinate tuple must contain exactly two values")
        first, second = value
        if order == "lon_lat":
            return cls(lon=first, lat=second)
        return cls(lon=second, lat=first)

    @classmethod
    def from_katec(cls, point: KatecPoint) -> PlaceCoordinate:
        """KATEC 좌표를 WGS84 기준 좌표 DTO로 변환합니다."""

        return cls.from_wgs84_point(point.to_wgs84())

    @classmethod
    def from_airkorea_tm(cls, point: AirKoreaTmPoint) -> PlaceCoordinate:
        """AirKorea TM 좌표를 WGS84 기준 좌표 DTO로 변환합니다."""

        return cls.from_wgs84_point(airkorea_tm_to_wgs84(point.tm_x, point.tm_y))

    @classmethod
    def from_kma_grid(cls, point: KmaGridPoint) -> PlaceCoordinate:
        """기상청 DFS 격자 좌표를 WGS84 기준 좌표 DTO로 변환합니다."""

        return cls.from_wgs84_point(point.to_wgs84_point())

    @property
    def crs(self) -> str:
        return WGS84_CRS

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
        """UI나 provider 요청에서 자주 쓰는 `(lat, lon)` 순서로 반환합니다."""

        return self.latlon

    def as_geojson_position(self) -> tuple[float, float]:
        """GeoJSON Position 규칙의 `(lon, lat)`를 반환합니다."""

        return self.lonlat

    def to_wgs84_point(self) -> Wgs84Point:
        """기존 dataclass 좌표 값 객체로 변환합니다."""

        return Wgs84Point(self.lon, self.lat)

    def to_latlon(self) -> LatLon:
        """`LatLon(lat, lon)` 값 객체로 변환합니다."""

        return LatLon(self.lat, self.lon)

    def to_katec(self) -> KatecPoint:
        """KATEC 좌표로 변환합니다."""

        return wgs84_to_katec(self.lon, self.lat)

    def to_airkorea_tm(self) -> AirKoreaTmPoint:
        """AirKorea TM 좌표로 변환합니다."""

        return wgs84_to_airkorea_tm(self.lon, self.lat)

    def to_kma_grid(self) -> KmaGridPoint:
        """기상청 DFS 격자 좌표로 변환합니다."""

        return wgs84_to_kma_grid(self.lat, self.lon)

    def distance_to_m(self, other: PlaceCoordinate | Wgs84Point | LatLon) -> float:
        """다른 WGS84 좌표까지의 대권 거리를 미터 단위로 반환합니다."""

        if isinstance(other, PlaceCoordinate):
            target = other.to_wgs84_point()
        elif isinstance(other, LatLon):
            target = other.to_wgs84_point()
        else:
            target = other
        return haversine_distance_m(self.to_wgs84_point(), target)

    def to_wkt(self) -> str:
        """PostGIS 등에 사용할 WKT Point 문자열을 반환합니다."""

        return f"POINT({self.lon} {self.lat})"

    def to_ewkt(self) -> str:
        """SRID를 포함한 EWKT Point 문자열을 반환합니다."""

        return f"SRID={self.srid};{self.to_wkt()}"

    def to_geojson_geometry(self) -> dict[str, object]:
        """GeoJSON Point geometry dict를 반환합니다."""

        return {"type": "Point", "coordinates": [self.lon, self.lat]}

    def to_orm_dict(
        self,
        *,
        lon_field: str = "longitude",
        lat_field: str = "latitude",
        altitude_field: str | None = "altitude_m",
        accuracy_field: str | None = "accuracy_m",
        srid_field: str | None = "srid",
        geometry_field: str | None = None,
        geometry_format: GeometryFormat = "ewkt",
    ) -> dict[str, float | int | str | dict[str, object] | None]:
        """SQLAlchemy model 생성자나 bulk insert에 넘기기 쉬운 dict를 반환합니다.

        SQLAlchemy/GeoAlchemy2 객체를 직접 만들지는 않습니다. 기본 런타임 의존성을 작게
        유지하기 위해 숫자 컬럼 값과 선택적인 WKT/EWKT/GeoJSON 값만 반환합니다.
        """

        values: dict[str, float | int | str | dict[str, object] | None] = {
            lon_field: self.lon,
            lat_field: self.lat,
        }
        if altitude_field is not None:
            values[altitude_field] = self.altitude_m
        if accuracy_field is not None:
            values[accuracy_field] = self.accuracy_m
        if srid_field is not None:
            values[srid_field] = self.srid
        if geometry_field is not None:
            values[geometry_field] = self._format_geometry(geometry_format)
        return values

    def to_sqlalchemy_values(
        self,
        **kwargs: Any,
    ) -> dict[str, float | int | str | dict[str, object] | None]:
        """`to_orm_dict`의 SQLAlchemy 용도 명시 alias입니다."""

        return self.to_orm_dict(**kwargs)

    def _format_geometry(self, geometry_format: GeometryFormat) -> str | dict[str, object]:
        if geometry_format == "wkt":
            return self.to_wkt()
        if geometry_format == "ewkt":
            return self.to_ewkt()
        if geometry_format == "geojson":
            return self.to_geojson_geometry()
        raise ValueError(f"unsupported geometry format: {geometry_format!r}")


class AddressRegion(BaseModel):
    """주소의 행정구역 영역 DTO.

    시군구코드만 있는 provider row와 법정동 하위 코드까지 있는 row를 같은 경계 모델로
    다룹니다. 지번/도로명 상세가 없는 지역 단위 데이터는 이 DTO만으로 표현할 수 있습니다.
    """

    model_config = _LOCATION_MODEL_CONFIG

    sigungu_code: SigunguCode | None = None
    legal_dong_code: LegalDongCode | None = None
    sido_name: str | None = None
    sigungu_name: str | None = None
    eup_myeon_dong_name: str | None = None
    ri_name: str | None = None

    @field_validator("sigungu_code", mode="before")
    @classmethod
    def _coerce_sigungu_code(cls, value: Any) -> SigunguCode | None:
        if value is None:
            return None
        if isinstance(value, Mapping):
            return SigunguCode.model_validate(value)
        return coerce_sigungu_code(value)

    @field_validator("legal_dong_code", mode="before")
    @classmethod
    def _coerce_legal_dong_code(cls, value: Any) -> LegalDongCode | None:
        if value is None:
            return None
        if isinstance(value, Mapping):
            return LegalDongCode.model_validate(value)
        return coerce_legal_dong_code(value)

    @field_validator(
        "sido_name",
        "sigungu_name",
        "eup_myeon_dong_name",
        "ri_name",
        mode="before",
    )
    @classmethod
    def _strip_optional_text(cls, value: Any) -> str | None:
        return strip_or_none(value)

    def model_post_init(self, __context: Any) -> None:
        if self.sigungu_code is not None and self.legal_dong_code is not None:
            if self.sigungu_code.code != self.legal_dong_code.sigungu_code:
                raise ValueError("sigungu_code does not match legal_dong_code")

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> AddressRegion | None:
        """provider row에서 시군구/법정동 코드와 행정구역 이름을 찾아 DTO를 반환합니다."""

        sigungu = sigungu_code_from_mapping(row)
        legal_dong = legal_dong_code_from_mapping(row)
        names = {
            "sido_name": first_value(row, *SIDO_NAME_KEYS),
            "sigungu_name": first_value(row, *SIGUNGU_NAME_KEYS),
            "eup_myeon_dong_name": first_value(row, *EUP_MYEON_DONG_NAME_KEYS),
            "ri_name": first_value(row, *RI_NAME_KEYS),
        }
        if sigungu is None and legal_dong is None and not any(
            strip_or_none(value) is not None for value in names.values()
        ):
            return None
        return cls(sigungu_code=sigungu, legal_dong_code=legal_dong, **names)

    @classmethod
    def from_sigungu_code(
        cls,
        value: SigunguCode | str,
        **kwargs: Any,
    ) -> AddressRegion:
        """시군구코드만 있는 지역 DTO를 만듭니다."""

        return cls(sigungu_code=coerce_sigungu_code(value), **kwargs)

    @classmethod
    def from_legal_dong_code(
        cls,
        value: LegalDongCode | str,
        **kwargs: Any,
    ) -> AddressRegion:
        """법정동코드에서 지역 DTO를 만듭니다."""

        legal_dong = coerce_legal_dong_code(value)
        return cls(
            sigungu_code=legal_dong.to_sigungu_code(),
            legal_dong_code=legal_dong,
            **kwargs,
        )

    @property
    def effective_sigungu_code(self) -> SigunguCode | None:
        if self.sigungu_code is not None:
            return self.sigungu_code
        if self.legal_dong_code is not None:
            return self.legal_dong_code.to_sigungu_code()
        return None

    @property
    def sigungu_code_value(self) -> str | None:
        code = self.effective_sigungu_code
        return code.code if code else None

    @property
    def sido_code(self) -> str | None:
        code = self.effective_sigungu_code
        return code.sido_code if code else None

    @property
    def legal_dong_code_value(self) -> str | None:
        return self.legal_dong_code.code if self.legal_dong_code else None

    @property
    def eup_myeon_dong_code(self) -> str | None:
        return self.legal_dong_code.eup_myeon_dong_code if self.legal_dong_code else None

    @property
    def ri_code(self) -> str | None:
        return self.legal_dong_code.ri_part if self.legal_dong_code else None

    @property
    def has_lower_region_code(self) -> bool:
        """시군구보다 더 세분화된 법정동 코드가 있는지 반환합니다."""

        if self.legal_dong_code is None:
            return False
        return self.legal_dong_code.is_eup_myeon_dong_level or self.legal_dong_code.is_ri_level

    @property
    def administrative_label(self) -> str | None:
        """시도/시군구/읍면동/리를 공백으로 이은 행정구역 표시명을 반환합니다."""

        parts = [
            self.sido_name,
            self.sigungu_name,
            self.eup_myeon_dong_name,
            self.ri_name,
        ]
        text = " ".join(part for part in parts if part)
        return text or None

    def with_legal_dong_code(self, value: LegalDongCode | str) -> AddressRegion:
        """현재 이름 정보를 유지하면서 법정동코드를 추가한 새 DTO를 반환합니다."""

        return AddressRegion(
            sigungu_code=self.effective_sigungu_code,
            legal_dong_code=coerce_legal_dong_code(value),
            sido_name=self.sido_name,
            sigungu_name=self.sigungu_name,
            eup_myeon_dong_name=self.eup_myeon_dong_name,
            ri_name=self.ri_name,
        )

    def to_orm_dict(self, *, prefix: str = "") -> dict[str, str | None]:
        """SQLAlchemy model 생성자나 bulk insert에 넘기기 쉬운 dict를 반환합니다."""

        return {
            f"{prefix}sido_code": self.sido_code,
            f"{prefix}sigungu_code": self.sigungu_code_value,
            f"{prefix}legal_dong_code": self.legal_dong_code_value,
            f"{prefix}eup_myeon_dong_code": self.eup_myeon_dong_code,
            f"{prefix}ri_code": self.ri_code,
            f"{prefix}sido_name": self.sido_name,
            f"{prefix}sigungu_name": self.sigungu_name,
            f"{prefix}eup_myeon_dong_name": self.eup_myeon_dong_name,
            f"{prefix}ri_name": self.ri_name,
        }

    def to_sqlalchemy_values(self, **kwargs: Any) -> dict[str, str | None]:
        """`to_orm_dict`의 SQLAlchemy 용도 명시 alias입니다."""

        return self.to_orm_dict(**kwargs)


class JibunAddress(BaseModel):
    """지번주소 DTO.

    지오코딩 없이 provider가 준 지번주소 문자열과 법정동코드를 보존하고, 법정동코드의
    시도/시군구/읍면동/리 단위 조회와 ORM 저장용 평면 dict 생성을 담당합니다.
    """

    model_config = _LOCATION_MODEL_CONFIG

    address: str | None = Field(
        default=None,
        validation_alias=AliasChoices(*JIBUN_ADDRESS_KEYS),
    )
    region: AddressRegion | None = None
    legal_dong_code: LegalDongCode | None = None
    sido_name: str | None = None
    sigungu_name: str | None = None
    eup_myeon_dong_name: str | None = None
    ri_name: str | None = None
    is_mountain: bool | None = None
    lot_main_number: int | None = None
    lot_sub_number: int | None = None
    postal_code: str | None = None

    @field_validator(
        "address",
        "sido_name",
        "sigungu_name",
        "eup_myeon_dong_name",
        "ri_name",
        "postal_code",
        mode="before",
    )
    @classmethod
    def _strip_optional_text(cls, value: Any) -> str | None:
        return strip_or_none(value)

    @field_validator("legal_dong_code", mode="before")
    @classmethod
    def _coerce_legal_dong_code(cls, value: Any) -> LegalDongCode | None:
        if value is None:
            return None
        if isinstance(value, Mapping):
            return LegalDongCode.model_validate(value)
        return coerce_legal_dong_code(value)

    @field_validator("region", mode="before")
    @classmethod
    def _coerce_region(cls, value: Any) -> AddressRegion | None:
        if value is None:
            return None
        if isinstance(value, AddressRegion):
            return value
        if isinstance(value, Mapping):
            return AddressRegion.model_validate(value)
        return AddressRegion.from_sigungu_code(value)

    @field_validator("is_mountain", mode="before")
    @classmethod
    def _coerce_mountain_flag(cls, value: Any) -> bool | None:
        return _bool_or_none(value, true_values={"산", "mountain"}, false_values={"대지", "land"})

    @field_validator("lot_main_number", "lot_sub_number", mode="before")
    @classmethod
    def _coerce_lot_number(cls, value: Any) -> int | None:
        return _int_or_none(value)

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> JibunAddress | None:
        """provider row에서 지번주소와 법정동코드 후보 필드를 찾아 DTO를 반환합니다."""

        address = strip_or_none(first_value(row, *JIBUN_ADDRESS_KEYS))
        region = AddressRegion.from_mapping(row)
        legal_code = legal_dong_code_from_mapping(row)
        if address is None and legal_code is None and region is None:
            return None
        return cls(
            address=address,
            region=region,
            legal_dong_code=legal_code,
            sido_name=first_value(row, *SIDO_NAME_KEYS),
            sigungu_name=first_value(row, *SIGUNGU_NAME_KEYS),
            eup_myeon_dong_name=first_value(row, *EUP_MYEON_DONG_NAME_KEYS),
            ri_name=first_value(row, *RI_NAME_KEYS),
            is_mountain=first_value(row, "is_mountain", "mountain_yn", "mtYn", "산여부"),
            lot_main_number=first_value(row, "lot_main_number", "lnbrMnnm", "bun", "본번"),
            lot_sub_number=first_value(row, "lot_sub_number", "lnbrSlno", "ji", "부번"),
            postal_code=first_value(row, *POSTAL_CODE_KEYS),
        )

    def model_post_init(self, __context: Any) -> None:
        region = self.effective_region
        if region is None or self.legal_dong_code is None:
            return
        if region.sigungu_code_value != self.legal_dong_code.sigungu_code:
            raise ValueError("region does not match legal_dong_code")

    @property
    def display_address(self) -> str | None:
        """표시용 지번주소 문자열을 반환합니다."""

        return self.address

    @property
    def effective_region(self) -> AddressRegion | None:
        if self.region is not None:
            if self.legal_dong_code is not None and self.region.legal_dong_code is None:
                return self.region.with_legal_dong_code(self.legal_dong_code)
            return self.region
        if self.legal_dong_code is not None:
            return AddressRegion.from_legal_dong_code(
                self.legal_dong_code,
                sido_name=self.sido_name,
                sigungu_name=self.sigungu_name,
                eup_myeon_dong_name=self.eup_myeon_dong_name,
                ri_name=self.ri_name,
            )
        if any((self.sido_name, self.sigungu_name, self.eup_myeon_dong_name, self.ri_name)):
            return AddressRegion(
                sido_name=self.sido_name,
                sigungu_name=self.sigungu_name,
                eup_myeon_dong_name=self.eup_myeon_dong_name,
                ri_name=self.ri_name,
            )
        return None

    @property
    def sido_code(self) -> str | None:
        return self.effective_region.sido_code if self.effective_region else None

    @property
    def sigungu_code(self) -> str | None:
        return self.effective_region.sigungu_code_value if self.effective_region else None

    @property
    def eup_myeon_dong_code(self) -> str | None:
        return self.effective_region.eup_myeon_dong_code if self.effective_region else None

    @property
    def ri_code(self) -> str | None:
        return self.effective_region.ri_code if self.effective_region else None

    @property
    def legal_dong_parts(self) -> dict[str, str | None]:
        """법정동코드 구성 요소를 dict로 반환합니다."""

        return {
            "sido_code": self.sido_code,
            "sigungu_code": self.sigungu_code,
            "eup_myeon_dong_code": self.eup_myeon_dong_code,
            "ri_code": self.ri_code,
        }

    @property
    def lot_number_label(self) -> str | None:
        """본번-부번 표시 문자열을 반환합니다."""

        if self.lot_main_number is None:
            return None
        if self.lot_sub_number in (None, 0):
            return str(self.lot_main_number)
        return f"{self.lot_main_number}-{self.lot_sub_number}"

    @property
    def administrative_label(self) -> str | None:
        """시도/시군구/읍면동/리를 공백으로 이은 행정구역 표시명을 반환합니다."""

        parts = [
            self.sido_name,
            self.sigungu_name,
            self.eup_myeon_dong_name,
            self.ri_name,
        ]
        text = " ".join(part for part in parts if part)
        return text or None

    def to_orm_dict(self, *, prefix: str = "jibun_") -> dict[str, str | int | bool | None]:
        """SQLAlchemy model 생성자나 bulk insert에 넘기기 쉬운 dict를 반환합니다."""

        return {
            f"{prefix}address": self.address,
            "sido_code": self.sido_code,
            "sigungu_code": self.sigungu_code,
            "legal_dong_code": (
                self.effective_region.legal_dong_code_value if self.effective_region else None
            ),
            "legal_dong_sido_code": self.sido_code,
            "legal_dong_sigungu_code": self.sigungu_code,
            "legal_dong_eup_myeon_dong_code": self.eup_myeon_dong_code,
            "legal_dong_ri_code": self.ri_code,
            f"{prefix}sido_name": self.sido_name,
            f"{prefix}sigungu_name": self.sigungu_name,
            f"{prefix}eup_myeon_dong_name": self.eup_myeon_dong_name,
            f"{prefix}ri_name": self.ri_name,
            f"{prefix}is_mountain": self.is_mountain,
            f"{prefix}lot_main_number": self.lot_main_number,
            f"{prefix}lot_sub_number": self.lot_sub_number,
            "postal_code": self.postal_code,
        }

    def to_sqlalchemy_values(self, **kwargs: Any) -> dict[str, str | int | bool | None]:
        """`to_orm_dict`의 SQLAlchemy 용도 명시 alias입니다."""

        return self.to_orm_dict(**kwargs)

    def __str__(self) -> str:
        return self.address or (self.legal_dong_code.code if self.legal_dong_code else "")


class RoadNameAddress(BaseModel):
    """도로명주소 DTO.

    도로명주소 문자열과 도로명주소 코드 체계를 보존하고, 시군구/읍면동/도로명번호/건물번호
    단위의 조회와 ORM 저장용 평면 dict 생성을 담당합니다.
    """

    model_config = _LOCATION_MODEL_CONFIG

    address: str | None = Field(
        default=None,
        validation_alias=AliasChoices(*ROAD_ADDRESS_KEYS),
    )
    region: AddressRegion | None = None
    legal_dong_code: LegalDongCode | None = None
    road_name_code: RoadNameCode | None = None
    road_name_address_code: RoadNameAddressCode | None = None
    building_management_number: str | None = None
    sido_name: str | None = None
    sigungu_name: str | None = None
    eup_myeon_dong_name: str | None = None
    road_name: str | None = None
    is_underground: bool | None = None
    building_main_number: int | None = None
    building_sub_number: int | None = None
    building_name: str | None = None
    postal_code: str | None = None

    @field_validator(
        "address",
        "building_management_number",
        "sido_name",
        "sigungu_name",
        "eup_myeon_dong_name",
        "road_name",
        "building_name",
        "postal_code",
        mode="before",
    )
    @classmethod
    def _strip_optional_text(cls, value: Any) -> str | None:
        return strip_or_none(value)

    @field_validator("legal_dong_code", mode="before")
    @classmethod
    def _coerce_legal_dong_code(cls, value: Any) -> LegalDongCode | None:
        if value is None:
            return None
        if isinstance(value, Mapping):
            return LegalDongCode.model_validate(value)
        return coerce_legal_dong_code(value)

    @field_validator("region", mode="before")
    @classmethod
    def _coerce_region(cls, value: Any) -> AddressRegion | None:
        if value is None:
            return None
        if isinstance(value, AddressRegion):
            return value
        if isinstance(value, Mapping):
            return AddressRegion.model_validate(value)
        return AddressRegion.from_sigungu_code(value)

    @field_validator("road_name_code", mode="before")
    @classmethod
    def _coerce_road_name_code(cls, value: Any) -> RoadNameCode | None:
        if value is None:
            return None
        if isinstance(value, Mapping):
            return RoadNameCode.model_validate(value)
        return coerce_road_name_code(value)

    @field_validator("road_name_address_code", mode="before")
    @classmethod
    def _coerce_road_name_address_code(cls, value: Any) -> RoadNameAddressCode | None:
        if value is None:
            return None
        if isinstance(value, Mapping):
            return RoadNameAddressCode.model_validate(value)
        return coerce_road_name_address_code(value)

    @field_validator("is_underground", mode="before")
    @classmethod
    def _coerce_underground_flag(cls, value: Any) -> bool | None:
        if value is None:
            return None
        return normalize_underground_flag(value) == "1"

    @field_validator("building_main_number", "building_sub_number", mode="before")
    @classmethod
    def _coerce_building_number(cls, value: Any) -> int | None:
        if strip_or_none(value) is None:
            return None
        return int(normalize_building_number(value))

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> RoadNameAddress | None:
        """provider row에서 도로명주소와 주소 코드 후보 필드를 찾아 DTO를 반환합니다."""

        address = strip_or_none(first_value(row, *ROAD_ADDRESS_KEYS))
        region = AddressRegion.from_mapping(row)
        code_set = address_code_set_from_mapping(row)
        if address is None and not code_set.has_any_code and region is None:
            return None
        road_name_address = code_set.road_name_address_code
        return cls(
            address=address,
            region=region,
            legal_dong_code=code_set.legal_dong_code,
            road_name_code=code_set.road_name_code,
            road_name_address_code=road_name_address,
            building_management_number=code_set.building_management_number,
            sido_name=first_value(row, *SIDO_NAME_KEYS),
            sigungu_name=first_value(row, *SIGUNGU_NAME_KEYS),
            eup_myeon_dong_name=first_value(row, *EUP_MYEON_DONG_NAME_KEYS),
            road_name=first_value(row, "road_name", "rn", "rnNm", "도로명"),
            is_underground=(
                road_name_address.is_underground
                if road_name_address is not None
                else first_value(row, "is_underground", "udrtYn", "UDRT_YN", "지하여부")
            ),
            building_main_number=(
                road_name_address.building_main_number
                if road_name_address is not None
                else first_value(row, "building_main_number", "buldMnnm", "BULD_MNNM", "건물본번")
            ),
            building_sub_number=(
                road_name_address.building_sub_number
                if road_name_address is not None
                else first_value(row, "building_sub_number", "buldSlno", "BULD_SLNO", "건물부번")
            ),
            building_name=first_value(row, "building_name", "bdNm", "buldNm", "건물명"),
            postal_code=first_value(row, *POSTAL_CODE_KEYS),
        )

    @classmethod
    def from_components(
        cls,
        *,
        address: str | None = None,
        adm_cd: LegalDongCode | str,
        rn_mgt_sn: RoadNameCode | str,
        udrt_yn: Any,
        buld_mnnm: Any,
        buld_slno: Any = 0,
        **kwargs: Any,
    ) -> RoadNameAddress:
        """도로명주소 API 구성 요소로 도로명주소 DTO를 만듭니다."""

        code = RoadNameAddressCode.from_components(
            adm_cd=adm_cd,
            rn_mgt_sn=rn_mgt_sn,
            udrt_yn=udrt_yn,
            buld_mnnm=buld_mnnm,
            buld_slno=buld_slno,
        )
        return cls(
            address=address,
            region=AddressRegion.from_legal_dong_code(code.legal_dong_code),
            legal_dong_code=code.legal_dong_code,
            road_name_code=code.road_name_code,
            road_name_address_code=code,
            is_underground=code.is_underground,
            building_main_number=code.building_main_number,
            building_sub_number=code.building_sub_number,
            **kwargs,
        )

    def model_post_init(self, __context: Any) -> None:
        region = self.effective_region
        if region is None:
            return
        if self.effective_legal_dong_code is not None:
            if region.sigungu_code_value != self.effective_legal_dong_code.sigungu_code:
                raise ValueError("region does not match legal_dong_code")
        if self.effective_road_name_code is not None:
            if region.sigungu_code_value != self.effective_road_name_code.sigungu_code:
                raise ValueError("region does not match road_name_code")

    @property
    def display_address(self) -> str | None:
        """표시용 도로명주소 문자열을 반환합니다."""

        return self.address

    @property
    def effective_region(self) -> AddressRegion | None:
        if self.region is not None:
            if self.effective_legal_dong_code is not None and self.region.legal_dong_code is None:
                return self.region.with_legal_dong_code(self.effective_legal_dong_code)
            return self.region
        if self.effective_legal_dong_code is not None:
            return AddressRegion.from_legal_dong_code(
                self.effective_legal_dong_code,
                sido_name=self.sido_name,
                sigungu_name=self.sigungu_name,
                eup_myeon_dong_name=self.eup_myeon_dong_name,
            )
        if self.effective_road_name_code is not None:
            return AddressRegion.from_sigungu_code(
                self.effective_road_name_code.sigungu_code,
                sido_name=self.sido_name,
                sigungu_name=self.sigungu_name,
                eup_myeon_dong_name=self.eup_myeon_dong_name,
            )
        if any((self.sido_name, self.sigungu_name, self.eup_myeon_dong_name)):
            return AddressRegion(
                sido_name=self.sido_name,
                sigungu_name=self.sigungu_name,
                eup_myeon_dong_name=self.eup_myeon_dong_name,
            )
        return None

    @property
    def effective_legal_dong_code(self) -> LegalDongCode | None:
        if self.legal_dong_code is not None:
            return self.legal_dong_code
        if self.road_name_address_code is not None:
            return self.road_name_address_code.legal_dong_code
        return None

    @property
    def effective_road_name_code(self) -> RoadNameCode | None:
        if self.road_name_code is not None:
            return self.road_name_code
        if self.road_name_address_code is not None:
            return self.road_name_address_code.road_name_code
        return None

    @property
    def sido_code(self) -> str | None:
        return self.effective_region.sido_code if self.effective_region else None

    @property
    def sigungu_code(self) -> str | None:
        return self.effective_region.sigungu_code_value if self.effective_region else None

    @property
    def eup_myeon_dong_code(self) -> str | None:
        return self.effective_region.eup_myeon_dong_code if self.effective_region else None

    @property
    def road_name_number(self) -> str | None:
        code = self.effective_road_name_code
        return code.road_number if code else None

    @property
    def effective_is_underground(self) -> bool | None:
        if self.is_underground is not None:
            return self.is_underground
        if self.road_name_address_code is not None:
            return self.road_name_address_code.is_underground
        return None

    @property
    def effective_building_main_number(self) -> int | None:
        if self.building_main_number is not None:
            return self.building_main_number
        if self.road_name_address_code is not None:
            return self.road_name_address_code.building_main_number
        return None

    @property
    def effective_building_sub_number(self) -> int | None:
        if self.building_sub_number is not None:
            return self.building_sub_number
        if self.road_name_address_code is not None:
            return self.road_name_address_code.building_sub_number
        return None

    @property
    def building_number_label(self) -> str | None:
        """건물 본번-부번 표시 문자열을 반환합니다."""

        main_number = self.effective_building_main_number
        sub_number = self.effective_building_sub_number
        if main_number is None:
            return None
        if sub_number in (None, 0):
            return str(main_number)
        return f"{main_number}-{sub_number}"

    @property
    def address_codes(self) -> AddressCodeSet:
        """주소 연계 코드 묶음 DTO를 반환합니다."""

        return AddressCodeSet(
            legal_dong_code=self.effective_legal_dong_code,
            road_name_code=self.effective_road_name_code,
            road_name_address_code=self.road_name_address_code,
            building_management_number=self.building_management_number,
        )

    def to_juso_query_dict(self) -> dict[str, str]:
        """도로명주소 API 계열 요청 파라미터 모양으로 반환합니다."""

        if self.road_name_address_code is not None:
            return self.road_name_address_code.to_juso_query_dict()
        if (
            self.effective_legal_dong_code is None
            or self.effective_road_name_code is None
            or self.effective_is_underground is None
            or self.effective_building_main_number is None
        ):
            raise ValueError("road name address components are incomplete")
        code = RoadNameAddressCode.from_components(
            adm_cd=self.effective_legal_dong_code,
            rn_mgt_sn=self.effective_road_name_code,
            udrt_yn=self.effective_is_underground,
            buld_mnnm=self.effective_building_main_number,
            buld_slno=self.effective_building_sub_number or 0,
        )
        return code.to_juso_query_dict()

    def to_orm_dict(self, *, prefix: str = "road_") -> dict[str, str | int | bool | None]:
        """SQLAlchemy model 생성자나 bulk insert에 넘기기 쉬운 dict를 반환합니다."""

        legal_code = self.effective_legal_dong_code
        road_code = self.effective_road_name_code
        return {
            f"{prefix}address": self.address,
            "sido_code": self.sido_code,
            "sigungu_code": self.sigungu_code,
            "legal_dong_code": legal_code.code if legal_code else None,
            "road_name_code": road_code.code if road_code else None,
            "road_name_address_code": (
                self.road_name_address_code.code if self.road_name_address_code else None
            ),
            "building_management_number": self.building_management_number,
            f"{prefix}sido_name": self.sido_name,
            f"{prefix}sigungu_name": self.sigungu_name,
            f"{prefix}eup_myeon_dong_name": self.eup_myeon_dong_name,
            f"{prefix}name": self.road_name,
            f"{prefix}name_number": self.road_name_number,
            f"{prefix}is_underground": self.effective_is_underground,
            f"{prefix}building_main_number": self.effective_building_main_number,
            f"{prefix}building_sub_number": self.effective_building_sub_number,
            f"{prefix}building_name": self.building_name,
            "postal_code": self.postal_code,
        }

    def to_sqlalchemy_values(self, **kwargs: Any) -> dict[str, str | int | bool | None]:
        """`to_orm_dict`의 SQLAlchemy 용도 명시 alias입니다."""

        return self.to_orm_dict(**kwargs)

    def __str__(self) -> str:
        return self.address or (
            self.road_name_address_code.code if self.road_name_address_code else ""
        )


class Address(BaseModel):
    """지번주소와 도로명주소를 함께 담는 장소 주소 DTO.

    지역 단위 데이터는 `region`만 채우고, 지번/도로명 상세가 있는 데이터는 `jibun`과
    `road_name`에 각각 담습니다. 지오코딩 결과를 합치는 상위 모델이 아니라, 이미 확보한
    주소 값을 ORM 경계까지 안정적으로 옮기는 공통 값 객체입니다.
    """

    model_config = _LOCATION_MODEL_CONFIG

    region: AddressRegion | None = None
    jibun: JibunAddress | None = None
    road_name: RoadNameAddress | None = None
    postal_code: str | None = None

    @field_validator("region", mode="before")
    @classmethod
    def _coerce_region(cls, value: Any) -> AddressRegion | None:
        if value is None:
            return None
        if isinstance(value, AddressRegion):
            return value
        if isinstance(value, Mapping):
            return AddressRegion.model_validate(value)
        return AddressRegion.from_sigungu_code(value)

    @field_validator("jibun", mode="before")
    @classmethod
    def _coerce_jibun(cls, value: Any) -> JibunAddress | None:
        if value is None:
            return None
        if isinstance(value, JibunAddress):
            return value
        if isinstance(value, Mapping):
            return JibunAddress.model_validate(value)
        raise TypeError("jibun must be a JibunAddress or mapping")

    @field_validator("road_name", mode="before")
    @classmethod
    def _coerce_road_name(cls, value: Any) -> RoadNameAddress | None:
        if value is None:
            return None
        if isinstance(value, RoadNameAddress):
            return value
        if isinstance(value, Mapping):
            return RoadNameAddress.model_validate(value)
        raise TypeError("road_name must be a RoadNameAddress or mapping")

    @field_validator("postal_code", mode="before")
    @classmethod
    def _strip_postal_code(cls, value: Any) -> str | None:
        return strip_or_none(value)

    def model_post_init(self, __context: Any) -> None:
        region = self.effective_region
        for child in (self.jibun, self.road_name):
            child_region = child.effective_region if child is not None else None
            if region is None or child_region is None:
                continue
            if (
                region.sigungu_code_value is not None
                and child_region.sigungu_code_value is not None
                and region.sigungu_code_value != child_region.sigungu_code_value
            ):
                raise ValueError("address child region does not match Address.region")

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> Address | None:
        """provider row에서 지역/지번/도로명주소를 찾아 통합 주소 DTO를 반환합니다."""

        region = AddressRegion.from_mapping(row)
        code_set = address_code_set_from_mapping(row)
        jibun_has_detail = (
            strip_or_none(
                first_value(
                    row,
                    *JIBUN_ADDRESS_KEYS,
                    "is_mountain",
                    "mountain_yn",
                    "mtYn",
                    "산여부",
                    "lot_main_number",
                    "lnbrMnnm",
                    "bun",
                    "본번",
                    "lot_sub_number",
                    "lnbrSlno",
                    "ji",
                    "부번",
                )
            )
            is not None
        )
        road_has_detail = (
            strip_or_none(
                first_value(
                    row,
                    *ROAD_ADDRESS_KEYS,
                    "road_name",
                    "rn",
                    "rnNm",
                    "도로명",
                    "is_underground",
                    "udrtYn",
                    "UDRT_YN",
                    "지하여부",
                    "building_main_number",
                    "buldMnnm",
                    "BULD_MNNM",
                    "건물본번",
                    "building_sub_number",
                    "buldSlno",
                    "BULD_SLNO",
                    "건물부번",
                    "building_name",
                    "bdNm",
                    "buldNm",
                    "건물명",
                )
            )
            is not None
            or code_set.road_name_code is not None
            or code_set.road_name_address_code is not None
            or code_set.building_management_number is not None
        )
        jibun = JibunAddress.from_mapping(row) if jibun_has_detail else None
        road_name = RoadNameAddress.from_mapping(row) if road_has_detail else None
        postal_code = strip_or_none(first_value(row, *POSTAL_CODE_KEYS))
        if region is None and jibun is None and road_name is None and postal_code is None:
            return None
        return cls(
            region=region,
            jibun=jibun,
            road_name=road_name,
            postal_code=postal_code,
        )

    @property
    def effective_region(self) -> AddressRegion | None:
        if self.region is not None:
            return self.region
        if self.road_name is not None and self.road_name.effective_region is not None:
            return self.road_name.effective_region
        if self.jibun is not None and self.jibun.effective_region is not None:
            return self.jibun.effective_region
        return None

    @property
    def display_address(self) -> str | None:
        """도로명주소를 우선하는 표시용 주소를 반환합니다."""

        if self.road_name is not None and self.road_name.display_address:
            return self.road_name.display_address
        if self.jibun is not None and self.jibun.display_address:
            return self.jibun.display_address
        region = self.effective_region
        return region.administrative_label if region else None

    @property
    def sigungu_code(self) -> str | None:
        region = self.effective_region
        return region.sigungu_code_value if region else None

    @property
    def legal_dong_code(self) -> str | None:
        region = self.effective_region
        return region.legal_dong_code_value if region else None

    @property
    def has_detail_address(self) -> bool:
        """지번주소나 도로명주소 상세 문자열이 있는지 반환합니다."""

        return any(
            (
                self.jibun is not None and self.jibun.display_address is not None,
                self.road_name is not None and self.road_name.display_address is not None,
            )
        )

    @property
    def effective_postal_code(self) -> str | None:
        if self.postal_code is not None:
            return self.postal_code
        if self.road_name is not None and self.road_name.postal_code is not None:
            return self.road_name.postal_code
        if self.jibun is not None and self.jibun.postal_code is not None:
            return self.jibun.postal_code
        return None

    def to_orm_dict(self) -> dict[str, str | int | bool | None]:
        """SQLAlchemy model 생성자나 bulk insert에 넘기기 쉬운 통합 dict를 반환합니다."""

        values: dict[str, str | int | bool | None] = {
            "address": self.display_address,
            "postal_code": self.effective_postal_code,
            "has_detail_address": self.has_detail_address,
        }
        region = self.effective_region
        if region is not None:
            values.update(region.to_orm_dict())
        else:
            values.update(
                {
                    "sido_code": None,
                    "sigungu_code": None,
                    "legal_dong_code": None,
                    "eup_myeon_dong_code": None,
                    "ri_code": None,
                    "sido_name": None,
                    "sigungu_name": None,
                    "eup_myeon_dong_name": None,
                    "ri_name": None,
                }
            )
        if self.jibun is not None:
            values.update(self.jibun.to_orm_dict(prefix="jibun_"))
        else:
            values.update(_empty_jibun_orm_values())
        if self.road_name is not None:
            values.update(self.road_name.to_orm_dict(prefix="road_"))
        else:
            values.update(_empty_road_name_orm_values())
        values["address"] = self.display_address
        values["postal_code"] = self.effective_postal_code
        return values

    def to_sqlalchemy_values(self) -> dict[str, str | int | bool | None]:
        """`to_orm_dict`의 SQLAlchemy 용도 명시 alias입니다."""

        return self.to_orm_dict()

    def __str__(self) -> str:
        return self.display_address or self.sigungu_code or ""


def place_coordinate_from_mapping(row: Mapping[str, Any]) -> PlaceCoordinate | None:
    """mapping에서 기준 좌표 DTO를 생성합니다."""

    return PlaceCoordinate.from_mapping(row)


def address_region_from_mapping(row: Mapping[str, Any]) -> AddressRegion | None:
    """mapping에서 주소 행정구역 DTO를 생성합니다."""

    return AddressRegion.from_mapping(row)


def jibun_address_from_mapping(row: Mapping[str, Any]) -> JibunAddress | None:
    """mapping에서 지번주소 DTO를 생성합니다."""

    return JibunAddress.from_mapping(row)


def road_name_address_from_mapping(row: Mapping[str, Any]) -> RoadNameAddress | None:
    """mapping에서 도로명주소 DTO를 생성합니다."""

    return RoadNameAddress.from_mapping(row)


def place_address_from_mapping(row: Mapping[str, Any]) -> Address | None:
    """mapping에서 통합 주소 DTO를 생성합니다."""

    return Address.from_mapping(row)


def _empty_jibun_orm_values() -> dict[str, str | int | bool | None]:
    return {
        "jibun_address": None,
        "jibun_sido_name": None,
        "jibun_sigungu_name": None,
        "jibun_eup_myeon_dong_name": None,
        "jibun_ri_name": None,
        "jibun_is_mountain": None,
        "jibun_lot_main_number": None,
        "jibun_lot_sub_number": None,
    }


def _empty_road_name_orm_values() -> dict[str, str | int | bool | None]:
    return {
        "road_address": None,
        "road_name_code": None,
        "road_name_address_code": None,
        "building_management_number": None,
        "road_sido_name": None,
        "road_sigungu_name": None,
        "road_eup_myeon_dong_name": None,
        "road_name": None,
        "road_name_number": None,
        "road_is_underground": None,
        "road_building_main_number": None,
        "road_building_sub_number": None,
        "road_building_name": None,
    }


def _finite_float(value: Any, field_name: str) -> float:
    text = strip_or_none(value)
    if text is None:
        raise ValueError(f"{field_name} is empty")
    try:
        result = float(text.replace(",", ""))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a finite number: {value!r}") from exc
    if not math.isfinite(result):
        raise ValueError(f"{field_name} must be finite")
    return result


def _float_or_none(value: Any) -> float | None:
    if strip_or_none(value) is None:
        return None
    return _finite_float(value, "value")


def _int_or_none(value: Any) -> int | None:
    text = strip_or_none(value)
    if text is None:
        return None
    normalized = text.replace(",", "")
    try:
        return int(normalized)
    except ValueError as exc:
        raise ValueError(f"value must be an integer: {value!r}") from exc


def _bool_or_none(
    value: Any,
    *,
    true_values: set[str],
    false_values: set[str],
) -> bool | None:
    if isinstance(value, bool):
        return value
    text = strip_or_none(value)
    if text is None:
        return None
    normalized = text.casefold()
    if normalized in {"y", "yes", "true", "t", "1", "o"} | true_values:
        return True
    if normalized in {"n", "no", "false", "f", "0", "x"} | false_values:
        return False
    raise ValueError(f"value must be boolean-like: {value!r}")
