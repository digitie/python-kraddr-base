# TripMate 지도 도메인 타입

이 문서는 `kraddr.base.domains`의 기준 문서다. TripMate 지도 데이터는 8자리
category와 별개로, 지도/일정/검색에서 쓰는 최상위 도메인 타입을 가진다.

## 참고한 TripMate 문서

- `tripmate/docs/architecture/map-feature-schema.md`
- `tripmate/docs/api/trips.md`
- `tripmate/docs/architecture/user-trip-schema.md`
- `tripmate/docs/architecture/weather-air-quality-schema.md`
- `tripmate/apps/api/app/models/place.py`
- `tripmate/apps/api/app/models/trip.py`

확인한 기준은 다음과 같다.

- 2026-04-29 기준 TripMate 백엔드는 기존 `places` 중심 구조를 `map_features`
  중심 구조로 대체했다.
- 기존 구현 문서와 모델의 `feature_type`은 `place`, `event`, `route`, `area`,
  `notice`를 허용한다.
- 날씨/대기질 문서는 별도 raw/serving table과 `map_feature_id` 연결을 사용한다.
- 2026-05-10부터 `kraddr.base`의 공통 도메인 기준에는 사용자 결정에 따라 `weather`를
  추가한다. TripMate 백엔드가 이 값을 사용하려면 `map_features.feature_type`,
  `feature_mapping_candidates.candidate_feature_type`, `trip_plan_items.resource_type`
  제약과 detail table migration도 함께 확장해야 한다.

## 최종 도메인

| 값 | 의미 | detail table | detail kind |
| --- | --- | --- | --- |
| `place` | 장소, 시설, 상점, 주차장, 화장실, 충전소, 전망 지점 | `place_details` | `place_kind` |
| `event` | 축제, 공연, 전시, 장터, 체험 | `event_details` | `event_kind` |
| `route` | 산책로, 등산로, 자전거길, 드라이브 코스 | `route_details` | `route_kind` |
| `area` | 국립공원, 해변, 관광특구, 시장 권역, 제한 구역 | `area_details` | `area_kind` |
| `notice` | 폐쇄, 공사, 교통통제, 혼잡 같은 지도상 공지 | `notice_details` | `notice_kind` |
| `weather` | 날씨, 해수욕장 예보, 기상특보, 대기질처럼 지도에 올리는 환경 정보 | `weather_details` | `weather_kind` |

`content`는 지도 객체가 아니다. 기사, 큐레이션 목록, 여행 템플릿, 가이드처럼 좌표가
없을 수 있는 데이터는 별도 content 계열 테이블에서 관리하고, 필요한 경우
`content_feature_links`로 지도 객체와 연결한다.

## category와 domain의 관계

`category_code`는 관광/음식/숙박/교통 같은 분류 체계이고, `feature_type`은 지도에서
그릴 객체의 형태와 detail schema를 고르는 기준이다.

예를 들어 해수욕장은 점 위치만 있으면 `feature_type='place'`와
`category_code='01050100'`으로 저장할 수 있고, 실제 해변 polygon이 있으면
`feature_type='area'`와 `area_kind='beach'`로 승격할 수 있다. 해수욕장 수온이나
파고 예보처럼 환경 정보 자체를 지도 레이어로 보여주면 `feature_type='weather'`와
`weather_kind='beach'`를 쓴다.

## notice와 weather 구분

`notice`는 사용자에게 보여줄 지도 공지다. 공사, 폐쇄, 교통통제, 혼잡처럼 어떤 장소,
경로, 구역의 이용 상태를 알리는 객체에 쓴다. 기존 `notice_kind='weather_warning'`은
기상특보가 특정 geometry나 feature와 연결되어 지도 공지로 표현되는 경우다.

`weather`는 날씨와 대기질 자체를 지도에서 비교하거나 조회하는 객체다. 단기/중기 예보,
해수욕장 날씨, AirKorea 측정소/대기질, 특정 여행지 주변 관광코스 날씨처럼 지도 좌표나
구역을 기준으로 표시할 환경 정보에 쓴다.

## 최초 detail kind 값

`kraddr.base.domains`는 현재 다음 값을 공통 기준으로 둔다.

| 컬럼 | 허용값 |
| --- | --- |
| `place_kind` | `tourist_spot`, `restaurant`, `cafe`, `hotel`, `parking`, `toilet`, `ev_charger`, `viewpoint` |
| `event_kind` | `festival`, `performance`, `exhibition`, `market`, `activity` |
| `route_kind` | `walking`, `hiking`, `cycling`, `driving`, `scenic` |
| `area_kind` | `national_park`, `beach`, `tourism_zone`, `market_area`, `restricted_area` |
| `notice_kind` | `closure`, `construction`, `traffic_control`, `congestion`, `weather_warning` |
| `weather_kind` | `current`, `forecast`, `alert`, `beach`, `air_quality` |

provider별 특수 코드표는 각 provider 패키지에 남긴다. 위 값은 여러 하위 라이브러리와
TripMate 백엔드가 공유해야 하는 축약 기준만 담는다.

## 공통 map_features 기준

`map_features`는 지도 viewport 조회, marker 표시, 검색, 여행 일정 연결의 공통 기준이다.
`geom`과 `centroid`는 SRID 4326을 사용하고, `geometry_kind`는 `point`, `line`,
`polygon`, `mixed` 중 하나다.

공통 컬럼으로는 `id`, `feature_type`, `name`, `category_code`, `geom`,
`geometry_kind`, `centroid`, 주소 snapshot, 연락처, `status`, `is_visible`,
`primary_source_record_id`, `extra`를 둔다. 공통 컬럼으로 승격하지 않은 provider별 값은
detail table의 `extra`나 원천 `raw_payload`에 보존한다.

점 위치는 `kraddr.base.locations.PlaceCoordinate`를 기준 DTO로 사용한다. 이 DTO는 WGS84
`longitude`, `latitude` 숫자 컬럼과 PostGIS용 WKT/EWKT 값을 만들 수 있지만, 지오코딩과
리버스 지오코딩은 수행하지 않는다.

주소 snapshot과 함께 코드 기반 연계가 가능한 경우 `legal_dong_code`, `road_name_code`,
`road_name_address_code`, `building_management_number`를 보존한다. 법정동코드는
`kraddr.base.addresses.LegalDongCode`, 도로명코드는 `RoadNameCode`, 도로명주소관리번호는
`RoadNameAddressCode`로 검증한 뒤 ORM DTO용 평면 dict로 넘길 수 있다.
시군구코드까지만 있는 원천 row는 `kraddr.base.locations.AddressRegion`으로 보존하고,
지번/도로명 상세가 있을 때만 `JibunAddress`, `RoadNameAddress`, `Address`에 결합한다.
건물명이나 상세주소처럼 주소 본문과 분리해야 하는 값은 `Address.detail_address`에 보존한다.

## 여행 일정 연결

`trip_plan_items.resource_type`에서 `place`, `event`, `route`, `area`, `notice`,
`weather`는 `map_feature_id`로 연결되는 타입이다. 기존 전국문화축제 serving table과의
호환을 위한 `festival`, 아직 전용 지도 객체로 승격되지 않은 `trail`, `scenic_road`,
사용자 입력용 `custom`은 별도 식별자나 snapshot을 쓴다.
