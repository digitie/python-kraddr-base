"""TripMate 지도 도메인 타입과 스키마 기준 helper."""

from __future__ import annotations

from dataclasses import dataclass

from ._enum import StrEnum


class MapFeatureType(StrEnum):
    """TripMate 지도 객체의 최상위 도메인 타입."""

    PLACE = "place"
    EVENT = "event"
    ROUTE = "route"
    AREA = "area"
    NOTICE = "notice"
    WEATHER = "weather"


class GeometryKind(StrEnum):
    """`map_features.geometry_kind`에 저장하는 geometry 형태."""

    POINT = "point"
    LINE = "line"
    POLYGON = "polygon"
    MIXED = "mixed"


class MapFeatureStatus(StrEnum):
    """TripMate 지도 객체의 lifecycle 상태."""

    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    TEMPORARILY_CLOSED = "temporarily_closed"
    DELETED = "deleted"

    @property
    def is_visible_candidate(self) -> bool:
        """지도 노출 후보로 볼 수 있는 상태인지 반환합니다."""

        return self is MapFeatureStatus.ACTIVE


class PlaceKind(StrEnum):
    """`place_details.place_kind` 최초 허용값."""

    TOURIST_SPOT = "tourist_spot"
    RESTAURANT = "restaurant"
    CAFE = "cafe"
    HOTEL = "hotel"
    PARKING = "parking"
    TOILET = "toilet"
    EV_CHARGER = "ev_charger"
    VIEWPOINT = "viewpoint"


class EventKind(StrEnum):
    """`event_details.event_kind` 최초 허용값."""

    FESTIVAL = "festival"
    PERFORMANCE = "performance"
    EXHIBITION = "exhibition"
    MARKET = "market"
    ACTIVITY = "activity"


class RouteKind(StrEnum):
    """`route_details.route_kind` 최초 허용값."""

    WALKING = "walking"
    HIKING = "hiking"
    CYCLING = "cycling"
    DRIVING = "driving"
    SCENIC = "scenic"


class AreaKind(StrEnum):
    """`area_details.area_kind` 최초 허용값."""

    NATIONAL_PARK = "national_park"
    BEACH = "beach"
    TOURISM_ZONE = "tourism_zone"
    MARKET_AREA = "market_area"
    RESTRICTED_AREA = "restricted_area"


class NoticeKind(StrEnum):
    """`notice_details.notice_kind` 최초 허용값."""

    CLOSURE = "closure"
    CONSTRUCTION = "construction"
    TRAFFIC_CONTROL = "traffic_control"
    CONGESTION = "congestion"
    WEATHER_WARNING = "weather_warning"


class NoticeSeverity(StrEnum):
    """지도 공지의 사용자 영향도."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class WeatherKind(StrEnum):
    """`weather_details.weather_kind` 최초 허용값."""

    CURRENT = "current"
    FORECAST = "forecast"
    ALERT = "alert"
    BEACH = "beach"
    AIR_QUALITY = "air_quality"


class ContentKind(StrEnum):
    """지도 객체가 아닌 콘텐츠의 최초 허용값."""

    ARTICLE = "article"
    CURATED_LIST = "curated_list"
    ITINERARY_TEMPLATE = "itinerary_template"
    GUIDE = "guide"


class TripResourceType(StrEnum):
    """`trip_plan_items.resource_type`에서 쓰는 일정 리소스 타입."""

    PLACE = "place"
    EVENT = "event"
    ROUTE = "route"
    AREA = "area"
    NOTICE = "notice"
    WEATHER = "weather"
    FESTIVAL = "festival"
    TRAIL = "trail"
    SCENIC_ROAD = "scenic_road"
    CUSTOM = "custom"

    @property
    def is_map_feature(self) -> bool:
        """`map_feature_id`로 연결되는 도메인 타입인지 반환합니다."""

        return self.value in MAP_FEATURE_TYPE_VALUES


@dataclass(frozen=True, slots=True)
class MapFeatureColumn:
    """`map_features` 공통 컬럼 참고 정보."""

    name: str
    required: bool
    note: str


@dataclass(frozen=True, slots=True)
class MapFeatureDomain:
    """지도 도메인별 detail table과 세부 kind 기준."""

    feature_type: MapFeatureType
    label: str
    description: str
    detail_table: str
    detail_kind_field: str
    detail_kind_values: tuple[str, ...]
    typical_geometry_kinds: tuple[GeometryKind, ...]

    @property
    def value(self) -> str:
        """문자열 wire value를 반환합니다."""

        return self.feature_type.value


MAP_FEATURE_TYPES: tuple[MapFeatureType, ...] = (
    MapFeatureType.PLACE,
    MapFeatureType.EVENT,
    MapFeatureType.ROUTE,
    MapFeatureType.AREA,
    MapFeatureType.NOTICE,
    MapFeatureType.WEATHER,
)
MAP_FEATURE_TYPE_VALUES: tuple[str, ...] = tuple(item.value for item in MAP_FEATURE_TYPES)

GEOMETRY_KINDS: tuple[GeometryKind, ...] = (
    GeometryKind.POINT,
    GeometryKind.LINE,
    GeometryKind.POLYGON,
    GeometryKind.MIXED,
)
GEOMETRY_KIND_VALUES: tuple[str, ...] = tuple(item.value for item in GEOMETRY_KINDS)

MAP_FEATURE_STATUSES: tuple[MapFeatureStatus, ...] = (
    MapFeatureStatus.DRAFT,
    MapFeatureStatus.ACTIVE,
    MapFeatureStatus.INACTIVE,
    MapFeatureStatus.TEMPORARILY_CLOSED,
    MapFeatureStatus.DELETED,
)
MAP_FEATURE_STATUS_VALUES: tuple[str, ...] = tuple(item.value for item in MAP_FEATURE_STATUSES)

PLACE_KIND_VALUES: tuple[str, ...] = tuple(item.value for item in PlaceKind)
EVENT_KIND_VALUES: tuple[str, ...] = tuple(item.value for item in EventKind)
ROUTE_KIND_VALUES: tuple[str, ...] = tuple(item.value for item in RouteKind)
AREA_KIND_VALUES: tuple[str, ...] = tuple(item.value for item in AreaKind)
NOTICE_KIND_VALUES: tuple[str, ...] = tuple(item.value for item in NoticeKind)
NOTICE_SEVERITY_VALUES: tuple[str, ...] = tuple(item.value for item in NoticeSeverity)
WEATHER_KIND_VALUES: tuple[str, ...] = tuple(item.value for item in WeatherKind)
CONTENT_KIND_VALUES: tuple[str, ...] = tuple(item.value for item in ContentKind)

MAP_FEATURE_DETAIL_TABLES: dict[MapFeatureType, str] = {
    MapFeatureType.PLACE: "place_details",
    MapFeatureType.EVENT: "event_details",
    MapFeatureType.ROUTE: "route_details",
    MapFeatureType.AREA: "area_details",
    MapFeatureType.NOTICE: "notice_details",
    MapFeatureType.WEATHER: "weather_details",
}

MAP_FEATURE_DETAIL_KIND_FIELDS: dict[MapFeatureType, str] = {
    MapFeatureType.PLACE: "place_kind",
    MapFeatureType.EVENT: "event_kind",
    MapFeatureType.ROUTE: "route_kind",
    MapFeatureType.AREA: "area_kind",
    MapFeatureType.NOTICE: "notice_kind",
    MapFeatureType.WEATHER: "weather_kind",
}

MAP_FEATURE_DETAIL_KIND_VALUES: dict[MapFeatureType, tuple[str, ...]] = {
    MapFeatureType.PLACE: PLACE_KIND_VALUES,
    MapFeatureType.EVENT: EVENT_KIND_VALUES,
    MapFeatureType.ROUTE: ROUTE_KIND_VALUES,
    MapFeatureType.AREA: AREA_KIND_VALUES,
    MapFeatureType.NOTICE: NOTICE_KIND_VALUES,
    MapFeatureType.WEATHER: WEATHER_KIND_VALUES,
}

MAP_FEATURE_DOMAINS: dict[MapFeatureType, MapFeatureDomain] = {
    MapFeatureType.PLACE: MapFeatureDomain(
        feature_type=MapFeatureType.PLACE,
        label="장소",
        description="장소, 시설, 상점, 주차장, 화장실, 충전소, 전망 지점",
        detail_table="place_details",
        detail_kind_field="place_kind",
        detail_kind_values=PLACE_KIND_VALUES,
        typical_geometry_kinds=(GeometryKind.POINT, GeometryKind.POLYGON, GeometryKind.MIXED),
    ),
    MapFeatureType.EVENT: MapFeatureDomain(
        feature_type=MapFeatureType.EVENT,
        label="행사",
        description="축제, 공연, 전시, 장터, 체험처럼 기간성이 있는 지도 객체",
        detail_table="event_details",
        detail_kind_field="event_kind",
        detail_kind_values=EVENT_KIND_VALUES,
        typical_geometry_kinds=(GeometryKind.POINT, GeometryKind.POLYGON, GeometryKind.MIXED),
    ),
    MapFeatureType.ROUTE: MapFeatureDomain(
        feature_type=MapFeatureType.ROUTE,
        label="경로",
        description="산책로, 등산로, 자전거길, 드라이브 코스",
        detail_table="route_details",
        detail_kind_field="route_kind",
        detail_kind_values=ROUTE_KIND_VALUES,
        typical_geometry_kinds=(GeometryKind.LINE, GeometryKind.MIXED),
    ),
    MapFeatureType.AREA: MapFeatureDomain(
        feature_type=MapFeatureType.AREA,
        label="구역",
        description="국립공원, 해변, 관광특구, 시장 권역, 제한 구역",
        detail_table="area_details",
        detail_kind_field="area_kind",
        detail_kind_values=AREA_KIND_VALUES,
        typical_geometry_kinds=(GeometryKind.POLYGON, GeometryKind.MIXED),
    ),
    MapFeatureType.NOTICE: MapFeatureDomain(
        feature_type=MapFeatureType.NOTICE,
        label="지도 공지",
        description="폐쇄, 공사, 교통통제, 혼잡, 기상특보 같은 지도상 공지",
        detail_table="notice_details",
        detail_kind_field="notice_kind",
        detail_kind_values=NOTICE_KIND_VALUES,
        typical_geometry_kinds=GEOMETRY_KINDS,
    ),
    MapFeatureType.WEATHER: MapFeatureDomain(
        feature_type=MapFeatureType.WEATHER,
        label="날씨",
        description="날씨, 해수욕장 예보, 기상특보, 대기질처럼 지도에 올리는 환경 정보",
        detail_table="weather_details",
        detail_kind_field="weather_kind",
        detail_kind_values=WEATHER_KIND_VALUES,
        typical_geometry_kinds=GEOMETRY_KINDS,
    ),
}

COMMON_MAP_FEATURE_COLUMNS: tuple[MapFeatureColumn, ...] = (
    MapFeatureColumn("id", True, "내부 지도 객체 UUID"),
    MapFeatureColumn("feature_type", True, "place, event, route, area, notice, weather"),
    MapFeatureColumn("name", True, "지도와 목록의 대표 이름"),
    MapFeatureColumn("category_code", False, "TripMate 카테고리 또는 source별 표시 분류"),
    MapFeatureColumn("geom", True, "SRID 4326 geometry"),
    MapFeatureColumn("geometry_kind", True, "point, line, polygon, mixed"),
    MapFeatureColumn("centroid", True, "marker, 정렬, 근처 검색 기준점"),
    MapFeatureColumn("address", False, "전체 주소 snapshot"),
    MapFeatureColumn("road_address", False, "도로명주소 snapshot"),
    MapFeatureColumn("jibun_address", False, "지번주소 snapshot"),
    MapFeatureColumn("legal_dong_code", False, "법정동코드"),
    MapFeatureColumn("phone", False, "대표 전화번호"),
    MapFeatureColumn("website_url", False, "대표 웹사이트"),
    MapFeatureColumn("status", True, "draft, active, inactive, temporarily_closed, deleted"),
    MapFeatureColumn("is_visible", True, "지도/검색 노출 여부"),
    MapFeatureColumn("primary_source_record_id", False, "대표 원천 row 참조"),
    MapFeatureColumn("extra", True, "공통 컬럼으로 승격하지 않은 보조 값"),
)

MAP_FEATURE_RESOURCE_TYPES: tuple[TripResourceType, ...] = (
    TripResourceType.PLACE,
    TripResourceType.EVENT,
    TripResourceType.ROUTE,
    TripResourceType.AREA,
    TripResourceType.NOTICE,
    TripResourceType.WEATHER,
)
TRIP_RESOURCE_TYPES: tuple[TripResourceType, ...] = (
    *MAP_FEATURE_RESOURCE_TYPES,
    TripResourceType.FESTIVAL,
    TripResourceType.TRAIL,
    TripResourceType.SCENIC_ROAD,
    TripResourceType.CUSTOM,
)
TRIP_RESOURCE_TYPE_VALUES: tuple[str, ...] = tuple(item.value for item in TRIP_RESOURCE_TYPES)


def coerce_map_feature_type(value: MapFeatureType | TripResourceType | str) -> MapFeatureType:
    """지도 도메인 wire value를 `MapFeatureType`으로 변환합니다."""

    text = str(value)
    try:
        return MapFeatureType(text)
    except ValueError as exc:
        raise ValueError(f"Unknown TripMate map feature type: {text!r}") from exc


def is_map_feature_type(value: object) -> bool:
    """값이 TripMate 지도 도메인 타입인지 확인합니다."""

    if value is None:
        return False
    try:
        coerce_map_feature_type(str(value))
    except ValueError:
        return False
    return True


def map_feature_domain(value: MapFeatureType | TripResourceType | str) -> MapFeatureDomain:
    """지도 도메인 타입에 대응하는 schema hint를 반환합니다."""

    return MAP_FEATURE_DOMAINS[coerce_map_feature_type(value)]


def detail_table_for_feature_type(value: MapFeatureType | TripResourceType | str) -> str:
    """지도 도메인 타입에 대응하는 detail table 이름을 반환합니다."""

    return MAP_FEATURE_DETAIL_TABLES[coerce_map_feature_type(value)]


def detail_kind_field_for_feature_type(value: MapFeatureType | TripResourceType | str) -> str:
    """지도 도메인 타입에 대응하는 detail kind 컬럼명을 반환합니다."""

    return MAP_FEATURE_DETAIL_KIND_FIELDS[coerce_map_feature_type(value)]


def detail_kind_values_for_feature_type(
    value: MapFeatureType | TripResourceType | str,
) -> tuple[str, ...]:
    """지도 도메인 타입에 대응하는 detail kind 허용값을 반환합니다."""

    return MAP_FEATURE_DETAIL_KIND_VALUES[coerce_map_feature_type(value)]


def coerce_trip_resource_type(value: TripResourceType | MapFeatureType | str) -> TripResourceType:
    """일정 resource type wire value를 `TripResourceType`으로 변환합니다."""

    text = str(value)
    try:
        return TripResourceType(text)
    except ValueError as exc:
        raise ValueError(f"Unknown TripMate trip resource type: {text!r}") from exc


def is_map_feature_resource_type(value: object) -> bool:
    """일정 resource type이 `map_feature_id` 기반 타입인지 확인합니다."""

    if value is None:
        return False
    try:
        resource_type = coerce_trip_resource_type(str(value))
    except ValueError:
        return False
    return resource_type.is_map_feature


def trip_resource_type_for_feature_type(
    value: MapFeatureType | TripResourceType | str,
) -> TripResourceType:
    """지도 도메인 타입에 대응하는 일정 resource type을 반환합니다."""

    feature_type = coerce_map_feature_type(value)
    return TripResourceType(feature_type.value)
