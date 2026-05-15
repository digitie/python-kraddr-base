# 장소 기반 위치 타입

이 문서는 `kraddr.base.locations`의 기준 문서다. TripMate 하위 라이브러리가 장소,
시설, 관측소, 주유소, 공항, 휴게소, 해수욕장, 휴양림 같은 POI를 다룰 때 가장 먼저
공유해야 하는 위치 값 객체를 정의한다.

## 책임 범위

`PlaceCoordinate`, `AddressRegion`, `JibunAddress`, `RoadNameAddress`, `Address`는
provider row와 ORM 사이의 작은 DTO다. 이 클래스들은 값을 검증하고, 코드 체계를 잘라
보고, SQLAlchemy model 생성자나 bulk insert에 넘길 수 있는 평면 dict를 만든다.

이 클래스들은 다음 일을 하지 않는다.

- 주소 검색
- 주소 정제 API 호출
- 지오코딩
- 리버스 지오코딩
- provider 인증키나 HTTP 오류 처리

위 기능은 `pyvworld` 같은 상위 provider 라이브러리나 TripMate 서비스 계층에서 수행한다.
`kraddr.base`는 모든 라이브러리가 같은 모양의 값 객체를 주고받게 하는 경계만 담당한다.

## PlaceCoordinate

`PlaceCoordinate`는 장소의 기준 좌표 DTO다. 내부 저장 기준은 WGS84 `EPSG:4326`이고,
축 순서는 `Wgs84Point`와 같은 `(lon, lat)`이다.

주요 기능:

- `lon`, `lat` 범위 검증
- `altitude_m`, `accuracy_m` 보조 값 보존
- provider row의 `lon`, `lng`, `longitude`, `mapx`, `x`, `xValue`, `lat`,
  `latitude`, `mapy`, `y`, `yValue` 같은 흔한 key에서 좌표 추출
- provider가 `-99.000000` 같은 누락 sentinel을 좌표 key에 내려주면 좌표 없음으로 처리
- DMS 문자열이나 hemisphere 표기가 있는 경도/위도에서 `from_values()`로 좌표 생성
- `Wgs84Point`, `LatLon`, `KatecPoint`, `AirKoreaTmPoint`, `KmaGridPoint`와 변환
- `distance_to_m()`, `distance_to_km()` 대권 거리 계산
- `to_wkt()`, `to_ewkt()`, `to_geojson_geometry()` geometry helper
- `to_orm_dict()`, `to_sqlalchemy_values()` 평면 저장 값 생성

예시:

```python
from kraddr.base import PlaceCoordinate

coord = PlaceCoordinate(lon="126.9780", lat="37.5665", accuracy_m="5")
same_coord = PlaceCoordinate.from_values("126° 58' 40.8\" E", "37° 33' 59.4\" N")

assert coord.as_lon_lat() == (126.978, 37.5665)
assert coord.as_lat_lon() == (37.5665, 126.978)
assert same_coord.distance_to_km(coord) < 0.1
assert coord.to_ewkt() == "SRID=4326;POINT(126.978 37.5665)"

values = coord.to_sqlalchemy_values(
    lon_field="lon",
    lat_field="lat",
    geometry_field="geom",
)
```

`to_sqlalchemy_values()`는 SQLAlchemy나 GeoAlchemy2 객체를 직접 만들지 않는다. 기본
런타임 의존성을 작게 유지하기 위해 숫자 컬럼과 WKT/EWKT/GeoJSON 값을 반환한다.
GeoAlchemy2를 쓰는 프로젝트에서는 반환된 `geom` 값을 서비스 계층에서 `WKTElement`로
감싸면 된다.

## AddressRegion

`AddressRegion`은 주소의 행정구역 영역 DTO다. 여러 데이터 소스가 상세 주소 없이
시군구코드까지만 제공하므로, 지번/도로명주소보다 먼저 이 객체를 사용한다.

주요 기능:

- `SigunguCode` 5자리 코드 보존
- 선택적인 `LegalDongCode` 10자리 코드 보존
- 시도/시군구/읍면동/리 이름 보존
- 주소 문자열에서 시도/시군구/읍면동 이름 추출. 단, 주소 문자열만으로는 10자리
  법정동코드를 추정하지 않음
- 법정동코드나 도로명코드가 있으면 시군구코드 자동 파생
- `has_lower_region_code`로 시군구보다 하위 코드가 있는지 확인
- `to_orm_dict()`, `to_sqlalchemy_values()` 평면 저장 값 생성

예시:

```python
from kraddr.base import AddressRegion

region = AddressRegion.from_sigungu_code(
    "11110",
    sido_name="서울특별시",
    sigungu_name="종로구",
)

assert region.sigungu_code_value == "11110"
assert region.legal_dong_code is None
assert region.to_sqlalchemy_values()["sigungu_code"] == "11110"
```

법정동코드가 있는 경우:

```python
region = AddressRegion.from_legal_dong_code("1111011900")

assert region.sigungu_code_value == "11110"
assert region.eup_myeon_dong_code == "11110119"
assert region.has_lower_region_code is True
```

주소 문자열만 있을 때:

```python
region = AddressRegion.from_text("경기 용인시 수지구 풍덕천동 42-1")

assert region.sido_name == "경기도"
assert region.sigungu_name == "용인시 수지구"
assert region.legal_dong_code is None
```

법정동코드가 필요하면 provider가 내려준 `legal_dong_code`/`ADM_CD`를 사용하거나,
`pyvworld`의 `LT_C_ADEMD_INFO` 같은 법정동 경계 조회 결과를 `from_legal_dong_code()`에
넘긴다. 자유 주소 문자열만으로 코드를 임의 매핑하지 않는다.

## JibunAddress

`JibunAddress`는 지번주소 DTO다. 공통 행정구역은 `AddressRegion`에 두고, 지번주소
문자열, 산 여부, 지번 본번/부번처럼 지번 체계에만 속하는 값을 보관한다.

주요 기능:

- 지번주소 문자열과 우편번호 보존
- `AddressRegion` 기반 `sido_code`, `sigungu_code`, `eup_myeon_dong_code`, `ri_code` 조회
- `is_mountain`, `lot_main_number`, `lot_sub_number` 보존
- `lot_number_label`, `administrative_label` 표시 helper
- `to_orm_dict()`, `to_sqlalchemy_values()` 평면 저장 값 생성

예시:

```python
from kraddr.base import AddressRegion, JibunAddress

jibun = JibunAddress(
    region=AddressRegion.from_sigungu_code("11110"),
    address="서울특별시 종로구 세종로 1-91",
    legal_dong_code="1111011900",
    lot_main_number=1,
    lot_sub_number=91,
)

assert jibun.sigungu_code == "11110"
assert jibun.eup_myeon_dong_code == "11110119"
assert jibun.lot_number_label == "1-91"

values = jibun.to_sqlalchemy_values()
```

시군구까지만 있는 데이터도 표현할 수 있다.

```python
jibun = JibunAddress(region=AddressRegion.from_sigungu_code("11110"))

assert jibun.display_address is None
assert jibun.sigungu_code == "11110"
assert jibun.to_sqlalchemy_values()["legal_dong_code"] is None
```

## RoadNameAddress

`RoadNameAddress`는 도로명주소 DTO다. 공통 행정구역은 `AddressRegion`에 두고,
도로명주소 문자열, 도로명코드, 도로명주소관리번호, 건물관리번호, 건물 본번/부번처럼
도로명주소 체계에만 속하는 값을 보관한다.

주요 기능:

- 도로명주소 문자열과 우편번호 보존
- `RoadNameCode` 기반 `sigungu_code`, `road_name_number` 조회
- `RoadNameAddressCode` 기반 법정동/도로명코드, 지하여부, 건물 본번/부번 파생
- `building_number_label` 표시 helper
- 도로명주소 API 계열 파라미터용 `to_juso_query_dict()`
- `to_orm_dict()`, `to_sqlalchemy_values()` 평면 저장 값 생성

예시:

```python
from kraddr.base import RoadNameAddress

road = RoadNameAddress.from_components(
    address="세종특별자치시 한누리대로 2130",
    adm_cd="3611011000",
    rn_mgt_sn="361103258085",
    udrt_yn="0",
    buld_mnnm="572",
    buld_slno="0",
)

assert road.road_name_address_code.code == "36110110325808500057200000"
assert road.sigungu_code == "36110"
assert road.building_number_label == "572"

values = road.to_sqlalchemy_values()
```

도로명주소도 시군구까지만 있는 지역 row를 표현할 수 있다.

```python
from kraddr.base import AddressRegion, RoadNameAddress

road = RoadNameAddress(region=AddressRegion.from_sigungu_code("11110"))

assert road.sigungu_code == "11110"
assert road.road_name_code is None
```

## Address

`Address`는 `AddressRegion`, `JibunAddress`, `RoadNameAddress`를 묶는 통합 주소 DTO다.
도로명주소와 지번주소가 모두 있으면 도로명주소를 표시용 주소로 우선하고, 상세 주소가
있으면 `detail_address`에 보존한다. 상세 주소가 없으면 자유 주소 문자열이나 `region`만
담을 수 있다. 자유 주소 문자열에서는 행정구역
이름만 추출하고, 법정동코드는 provider 코드나 검증된 외부 조회 결과가 있을 때만 보존한다.

예시:

```python
from kraddr.base import Address, AddressRegion

plain = Address.from_text("경기 용인시 수지구 풍덕천동 42-1")

assert plain.display_address == "경기 용인시 수지구 풍덕천동 42-1"
assert plain.legal_dong_code is None

address = Address(region=AddressRegion.from_sigungu_code("11110"))

assert address.sigungu_code == "11110"
assert address.has_detail_address is False
assert address.to_sqlalchemy_values()["road_address"] is None
```

provider row에서 통합 주소를 만들 때는 `Address.from_mapping()`을 직접 쓴다.

```python
from kraddr.base import Address

address = Address.from_mapping(
    {
        "sigungu_code": "11110",
        "svarAddr": "경기 용인시 수지구 풍덕천동 42-1",
        "ROAD_NM_ADDR": "서울특별시 종로구 세종대로 209",
        "LOTNO_ADDR": "서울특별시 종로구 세종로 1-91",
        "admCd": "1111011900",
        "detail_address": "정부서울청사",
    }
)

assert address.sigungu_code == "11110"
assert address.detail_address == "정부서울청사"
```

## provider row 정규화

provider row를 값 객체로 바꿀 때는 각 클래스의 `from_mapping()`을 직접 쓴다.

```python
from kraddr.base import (
    Address,
    AddressRegion,
    JibunAddress,
    PlaceCoordinate,
    RoadNameAddress,
)

row = {
    "mapx": "126.9780",
    "mapy": "37.5665",
    "ROAD_NM_ADDR": "서울특별시 종로구 세종대로 209",
    "LOTNO_ADDR": "서울특별시 종로구 세종로 1-91",
    "admCd": "1111011900",
}

coord = PlaceCoordinate.from_mapping(row)
region = AddressRegion.from_mapping(row)
jibun = JibunAddress.from_mapping(row)
road = RoadNameAddress.from_mapping(row)
address = Address.from_mapping(row)
```

provider별 특수 필드명은 provider 패키지에서 먼저 다듬는 것이 원칙이다. 다만 여러
라이브러리에서 반복되는 공개 API 필드명은 이 helper들이 공통 후보 key로 지원한다.

## SQLAlchemy 저장 기준

이 패키지는 SQLAlchemy를 직접 의존하지 않는다. 대신 다음처럼 model 생성자에 바로 넘길
수 있는 dict를 만든다.

```python
coord_values = coord.to_sqlalchemy_values(
    lon_field="longitude",
    lat_field="latitude",
    geometry_field="geom",
    geometry_format="ewkt",
)
address_values = {
    **address.to_sqlalchemy_values(),
}
```

숫자 위경도 컬럼만 쓰는 저장소는 `longitude`, `latitude` 값을 그대로 쓰면 된다. PostGIS
geometry 컬럼을 쓰는 저장소는 `geom`의 EWKT 문자열을 서비스 계층에서 GeoAlchemy2
객체로 변환한다.
