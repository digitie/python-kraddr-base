"""Provider POI 데이터를 공통 형태로 다루기 위한 enum/dataclass/helper."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ._convert import first_value, freeze_raw, strip_or_none
from ._enum import StrEnum
from .coordinates import Wgs84Point, coordinate_from_mapping
from .domains import MapFeatureType, coerce_map_feature_type


class PoiSource(StrEnum):
    """TripMate 하위 POI 공급 라이브러리 식별자."""

    PYMCST = "pymcst"
    PYKRFOREST = "pykrforest"
    PYMOIS = "pymois"
    PYAIRKOREA = "pyairkorea"
    PYKRAIRPORT = "pykrairport"
    KEX_OPENAPI = "kex_openapi"
    PYKMA = "pykma"
    OPINET = "opinet"
    PYKHOA = "pykhoa"
    PYKRTOURAPI = "pykrtourapi"
    PYVWORLD = "pyvworld"
    PYKRTOURPOI = "pykrtourpoi"
    TRIPMATE = "tripmate"


class PoiKind(StrEnum):
    """장소 계열 데이터를 큰 단위로 구분하는 enum."""

    PLACE = "place"
    CULTURE_FACILITY = "culture_facility"
    FOOD = "food"
    LODGING = "lodging"
    FESTIVAL = "festival"
    TRAIL = "trail"
    COURSE = "course"
    BEACH = "beach"
    OBSERVATORY = "observatory"
    STATION = "station"
    AIRPORT = "airport"
    REST_AREA = "rest_area"
    FUEL_STATION = "fuel_station"
    TRANSPORT = "transport"
    WEATHER_LOCATION = "weather_location"
    SAFETY_POINT = "safety_point"
    UNKNOWN = "unknown"


class PoiStatus(StrEnum):
    """여러 provider의 운영/활성 상태를 단순화한 enum."""

    OPEN = "open"
    CLOSED = "closed"
    TEMPORARILY_CLOSED = "temporarily_closed"
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"

    @property
    def is_open_like(self) -> bool | None:
        if self in {PoiStatus.OPEN, PoiStatus.ACTIVE}:
            return True
        if self in {PoiStatus.CLOSED, PoiStatus.TEMPORARILY_CLOSED, PoiStatus.INACTIVE}:
            return False
        return None


class DatasetKind(StrEnum):
    """POI 원천 데이터셋의 배포 형태."""

    OPEN_API = "open_api"
    FILE_DOWNLOAD = "file_download"
    PORTAL_AJAX = "portal_ajax"
    CATALOG = "catalog"
    LINK = "link"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ProviderDataset:
    """하위 provider 패키지가 노출하는 POI 원천 데이터셋 metadata."""

    source: PoiSource | str
    slug: str
    title: str
    provider: str | None = None
    kind: DatasetKind | str = DatasetKind.UNKNOWN
    endpoint: str | None = None
    detail_url: str | None = None
    tags: tuple[str, ...] = ()
    notes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _coerce_source(self.source))
        object.__setattr__(self, "kind", DatasetKind(str(self.kind)))
        object.__setattr__(self, "slug", str(self.slug))
        object.__setattr__(self, "title", str(self.title))
        object.__setattr__(self, "tags", tuple(str(tag) for tag in self.tags))


@dataclass(frozen=True, slots=True)
class PoiAddress:
    """POI 주소와 주소 연계 코드를 담는 값 객체."""

    road_address: str | None = None
    lot_address: str | None = None
    postal_code: str | None = None
    legal_dong_code: str | None = None
    road_name_code: str | None = None
    building_management_number: str | None = None

    @property
    def display_address(self) -> str | None:
        """표시용 주소. 도로명주소가 있으면 우선합니다."""

        return self.road_address or self.lot_address

    @property
    def has_linkage_codes(self) -> bool:
        """주소 master 연계에 쓸 수 있는 코드가 하나라도 있는지 반환합니다."""

        return any(
            (
                self.legal_dong_code,
                self.road_name_code,
                self.building_management_number,
            )
        )


@dataclass(frozen=True, slots=True)
class PoiContact:
    """POI 연락처/링크 정보."""

    tel: str | None = None
    homepage: str | None = None
    email: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderPoiRef:
    """provider 원천 안에서 POI를 다시 찾기 위한 참조."""

    source: PoiSource | str
    dataset: str | None = None
    provider_id: str | None = None
    provider_name: str | None = None
    endpoint: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _coerce_source(self.source))


@dataclass(frozen=True, slots=True)
class PoiRecord:
    """여러 provider에서 온 지도 객체 후보 데이터를 얇게 정규화한 레코드."""

    source: PoiSource | str
    name: str | None
    kind: PoiKind | str = PoiKind.UNKNOWN
    feature_type: MapFeatureType | str | None = None
    provider_id: str | None = None
    dataset: str | None = None
    category_code: str | None = None
    provider_category: str | None = None
    status: PoiStatus | str = PoiStatus.UNKNOWN
    coordinate: Wgs84Point | None = None
    address: PoiAddress | None = None
    contact: PoiContact | None = None
    ref: ProviderPoiRef | None = None
    tags: tuple[str, ...] = ()
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        source = _coerce_source(self.source)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "kind", PoiKind(str(self.kind)))
        if self.feature_type is not None:
            object.__setattr__(self, "feature_type", coerce_map_feature_type(self.feature_type))
        object.__setattr__(self, "status", PoiStatus(str(self.status)))
        object.__setattr__(self, "tags", tuple(str(tag) for tag in self.tags))
        object.__setattr__(self, "raw", freeze_raw(self.raw))
        if self.ref is None:
            object.__setattr__(
                self,
                "ref",
                ProviderPoiRef(
                    source=source,
                    dataset=self.dataset,
                    provider_id=self.provider_id,
                    provider_name=self.name,
                ),
            )

    @property
    def status_enum(self) -> PoiStatus:
        """`status`를 `PoiStatus` enum으로 반환합니다."""

        if isinstance(self.status, PoiStatus):
            return self.status
        return PoiStatus(str(self.status))

    @property
    def feature_type_enum(self) -> MapFeatureType | None:
        """`feature_type`을 `MapFeatureType` enum으로 반환합니다."""

        if self.feature_type is None:
            return None
        if isinstance(self.feature_type, MapFeatureType):
            return self.feature_type
        return coerce_map_feature_type(self.feature_type)

    @property
    def is_open(self) -> bool | None:
        """운영/활성 상태를 bool로 단순화합니다."""

        return self.status_enum.is_open_like

    @property
    def label(self) -> str:
        """사람이 읽을 표시 이름을 반환합니다."""

        return self.name or self.provider_id or self.dataset or str(self.source)


def address_from_mapping(row: Mapping[str, Any]) -> PoiAddress | None:
    """provider row에서 흔한 주소 필드를 찾아 `PoiAddress`로 정규화합니다."""

    address = PoiAddress(
        road_address=strip_or_none(
            first_value(
                row,
                "road_address",
                "roadAddress",
                "roadNmAddr",
                "NEW_ADR",
                "ROAD_NM_ADDR",
                "ROAD_NM_WHOL_ADDR",
                "도로명주소",
            )
        ),
        lot_address=strip_or_none(
            first_value(
                row,
                "lot_address",
                "jibun_address",
                "jibunAddress",
                "address",
                "addr",
                "VAN_ADR",
                "LOTNO_ADDR",
                "LCTN_WHOL_ADDR",
                "주소",
                "소재지",
            )
        ),
        postal_code=strip_or_none(first_value(row, "postal_code", "zip", "zipCode", "road_zip")),
        legal_dong_code=strip_or_none(first_value(row, "legal_dong_code", "ADM_CD")),
        road_name_code=strip_or_none(first_value(row, "road_name_code", "RN_MGT_SN")),
        building_management_number=strip_or_none(
            first_value(row, "building_management_number", "BD_MGT_SN")
        ),
    )
    if not any(
        (
            address.road_address,
            address.lot_address,
            address.postal_code,
            address.legal_dong_code,
            address.road_name_code,
            address.building_management_number,
        )
    ):
        return None
    return address


def contact_from_mapping(row: Mapping[str, Any]) -> PoiContact | None:
    """provider row에서 흔한 연락처/URL 필드를 찾아 `PoiContact`로 정규화합니다."""

    contact = PoiContact(
        tel=strip_or_none(
            first_value(row, "tel", "TEL", "phone", "phoneNumber", "전화번호", "연락처")
        ),
        homepage=strip_or_none(first_value(row, "homepage", "homePage", "url", "URL", "홈페이지")),
        email=strip_or_none(first_value(row, "email", "EMAIL", "이메일")),
    )
    if not any((contact.tel, contact.homepage, contact.email)):
        return None
    return contact


def poi_from_mapping(
    row: Mapping[str, Any],
    *,
    source: PoiSource | str,
    kind: PoiKind | str = PoiKind.UNKNOWN,
    feature_type: MapFeatureType | str | None = None,
    dataset: str | None = None,
    provider_id_keys: tuple[str, ...] = ("id", "code", "UNI_ID", "MNG_NO", "mngNo", "placeCode"),
    name_keys: tuple[str, ...] = (
        "name",
        "title",
        "stationName",
        "restAreaNm",
        "serviceAreaName",
        "BPLC_NM",
        "facName",
        "fcltyNm",
        "장소명",
        "시설명",
        "업소명",
    ),
) -> PoiRecord:
    """provider row를 `PoiRecord`로 얇게 정규화합니다."""

    provider_id = strip_or_none(first_value(row, *provider_id_keys))
    name = strip_or_none(first_value(row, *name_keys))
    return PoiRecord(
        source=source,
        provider_id=provider_id,
        name=name,
        kind=kind,
        feature_type=feature_type,
        dataset=dataset,
        provider_category=strip_or_none(first_value(row, "category", "type", "분류", "구분")),
        coordinate=coordinate_from_mapping(row),
        address=address_from_mapping(row),
        contact=contact_from_mapping(row),
        raw=row,
    )


def _coerce_source(value: PoiSource | str) -> PoiSource | str:
    text = str(value)
    try:
        return PoiSource(text)
    except ValueError:
        return text
