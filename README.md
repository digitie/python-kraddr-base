# pykrtour

`pykrtour`는 TripMate 하위 Python 라이브러리에서 함께 쓰는 POI 공통 코드입니다.

이 패키지는 API 클라이언트가 아니라, `pymcst`, `pykrforest`, `pymois`, `pyairkorea`,
`pykrairport`, `kex-openapi`, `pykma`, `opinet`, `pykhoa`, `pykrtourapi`,
`pyvworld`, `pykrtourpoi`가 장소/축제/트래킹코스/관측소/공항/휴게소/주유소 데이터를
같은 모양으로 다룰 때 쓰는 작은 타입 계층입니다.

## 포함 범위

- TripMate 8자리 POI 카테고리 코드와 tree helper
- TripMate 지도 도메인 타입(`place`, `event`, `route`, `area`, `notice`, `weather`)과
  detail schema hint
- 장소 기반 좌표, 행정구역, 지번주소, 도로명주소, 통합 주소 DTO와 SQLAlchemy 저장 helper
- 법정동코드, 도로명코드, 도로명주소관리번호 pydantic DTO와 ORM용 평면 dict helper
- WGS84, KATEC, AirKorea TM, KMA DFS 좌표 값 객체와 변환 helper
- provider POI row에서 이름, 주소, 연락처, 좌표를 뽑는 공통 dataclass/utility
- 한국 공항 코드/메타데이터와 근접 공항 helper
- 주유소 POI에 필요한 표준 유종/업종 enum

좌표계 변환 중 `pyproj`가 필요한 기능은 `pykrtour[geo]` extra로 분리했습니다.

## 예시

```python
from pykrtour import (
    Address,
    AddressRegion,
    LegalDongCode,
    MapFeatureType,
    PoiKind,
    PoiSource,
    PlaceCoordinate,
    RoadNameAddressCode,
    SigunguCode,
    Wgs84Point,
    category_label,
    poi_from_mapping,
)

row = {
    "name": "해운대해수욕장",
    "lat": "35.1587",
    "lon": "129.1604",
    "address": "부산광역시 해운대구",
}

poi = poi_from_mapping(
    row,
    source=PoiSource.PYKHOA,
    kind=PoiKind.BEACH,
    feature_type=MapFeatureType.PLACE,
)
assert poi.coordinate == Wgs84Point(129.1604, 35.1587)
assert poi.feature_type is MapFeatureType.PLACE
assert category_label("01050100") == "관광 > 자연명소 > 해수욕장"

coord = PlaceCoordinate(lon="129.1604", lat="35.1587")
assert coord.to_sqlalchemy_values(lon_field="lon", lat_field="lat") == {
    "lon": 129.1604,
    "lat": 35.1587,
    "altitude_m": None,
    "accuracy_m": None,
    "srid": 4326,
}

sigungu = SigunguCode(code="11110")
region = AddressRegion.from_sigungu_code(sigungu, sigungu_name="종로구")
address = Address(region=region)
assert address.to_sqlalchemy_values()["sigungu_code"] == "11110"

legal_dong = LegalDongCode(code="1111011900")
road_address_code = RoadNameAddressCode.from_components(
    adm_cd="3611011000",
    rn_mgt_sn="361103258085",
    udrt_yn="0",
    buld_mnnm="572",
    buld_slno="0",
)
assert legal_dong.sigungu_code == "11110"
assert road_address_code.to_orm_dict()["road_name_address_code"] == "36110110325808500057200000"
```

## 지도 도메인

TripMate 지도 데이터는 category와 별개로 최상위 도메인 타입을 가집니다. category는
관광/음식/숙박 같은 분류이고, 도메인은 지도 객체의 detail schema를 고르는 기준입니다.

- `place`: 장소, 시설, 상점, 주차장, 화장실, 충전소, 전망 지점
- `event`: 축제, 공연, 전시, 장터, 체험
- `route`: 산책로, 등산로, 자전거길, 드라이브 코스
- `area`: 국립공원, 해변, 관광특구, 시장 권역, 제한 구역
- `notice`: 폐쇄, 공사, 교통통제, 혼잡 같은 지도상 공지
- `weather`: 날씨, 해수욕장 예보, 기상특보, 대기질 같은 환경 정보

자세한 기준은 `docs/map-domains.md`에 정리했습니다.

## 장소 기반 타입

모든 하위 라이브러리가 공통으로 쓸 장소 위치 값 객체는 `pykrtour.locations`에 둡니다.

- `PlaceCoordinate`: WGS84 기준 좌표. 좌표 변환, WKT/EWKT/GeoJSON, ORM 저장 dict 제공
- `AddressRegion`: 시군구까지만 있는 지역 row와 법정동 하위 코드 row를 함께 표현
- `JibunAddress`: 지번주소. `AddressRegion` 아래 지번 본번/부번, ORM 저장 dict 제공
- `RoadNameAddress`: 도로명주소. 도로명코드/도로명주소관리번호 분해, 건물번호,
  도로명주소 API 파라미터, ORM 저장 dict 제공
- `Address`: `AddressRegion`, `JibunAddress`, `RoadNameAddress`를 묶는 통합 주소 DTO

주소 검색, 지오코딩, 리버스 지오코딩은 이 값 객체의 책임이 아닙니다. 해당 기능은
`pyvworld` 같은 provider 라이브러리나 서비스 계층에서 수행합니다. 자세한 기준은
`docs/place-base-types.md`에 정리했습니다.

## 설계 원칙

- provider wire value는 각 하위 라이브러리에 남기고, 여기에는 교차 라이브러리에서
  재사용 가능한 값 객체와 변환 규칙만 둡니다.
- 새 공통 타입은 기본적으로 immutable dataclass와 문자열 enum을 사용합니다. ORM 경계에서
  DTO 역할이 필요한 장소 위치/주소 계열은 pydantic 모델로 둡니다.
- 네트워크 호출, 인증키 처리, endpoint별 응답 파싱은 이 패키지 범위가 아닙니다.
- 기존 하위 라이브러리에서 확정된 공통 개념은 이 패키지로 옮기고, 하위 라이브러리는
  `pykrtour`에 의존하도록 조정합니다.
