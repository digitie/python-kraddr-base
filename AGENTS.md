# AGENTS.md

## 역할

이 문서는 `python-kraddr-base`에서 작업하는 에이전트를 위한 운영 가이드입니다. 이 저장소는
TripMate 하위 Python 라이브러리들이 공통으로 쓰는 POI 값 객체, enum, dataclass,
정규화 helper를 담습니다.

## 지시 우선순위

1. 사용자 요청
2. 이 `AGENTS.md`
3. `README.md`
4. 기존 코드와 테스트
5. 최소한의 되돌릴 수 있는 가정

## 프로젝트 기준

- `kraddr.base`는 원격 API 클라이언트가 아닙니다.
- 네트워크 호출, 인증키 처리, endpoint별 HTTP 오류 매핑은 하위 라이브러리에 둡니다.
- 이 패키지는 POI category, 지도 도메인 타입, 좌표, 주소/연락처/공급자 참조,
  공항/주유소 같은 공통 장소 타입을 제공합니다.
- Python 지원 기준은 3.10 이상입니다.
- 기본 런타임 의존성은 주소 DTO 검증용 `pydantic`만 둡니다. `pyproj`가 필요한 좌표
  변환은 `geo` extra로 둡니다.
- 기본 테스트는 네트워크 없이 동작해야 합니다.

## 모듈 지도

- `src/kraddr/base/categories.py`: TripMate 8자리 POI category enum/dataclass/tree helper.
- `src/kraddr/base/domains.py`: TripMate 지도 도메인 enum/dataclass/detail schema hint.
- `src/kraddr/base/addresses.py`: 법정동코드, 도로명코드, 도로명주소관리번호 pydantic DTO/helper.
- `src/kraddr/base/locations.py`: 장소 기반 좌표, 행정구역, 지번주소, 도로명주소, 통합 주소
  pydantic DTO/helper.
- `src/kraddr/base/coordinates.py`: WGS84, KATEC, AirKorea TM, KMA DFS 좌표 값 객체와 변환.
- `src/kraddr/base/poi.py`: provider POI 공통 enum/dataclass와 mapping 정규화 helper.
- `src/kraddr/base/airports.py`: 한국 공항 코드, 메타데이터, 근접 공항 helper.
- `src/kraddr/base/fuel.py`: 주유소 POI용 유종/업종 enum과 Opinet 코드 매핑.
- `src/kraddr/base/_convert.py`: 빈값/숫자/bool/raw payload 정규화 helper.
- `src/kraddr/base/_enum.py`: Python 3.10 호환 문자열 enum 기반 클래스.
- `tests/`: 네트워크 없는 단위 테스트.
- `docs/map-domains.md`: category와 별개로 쓰는 지도 도메인 기준 문서.
- `docs/place-base-types.md`: 모든 하위 라이브러리가 공유하는 장소 위치 DTO 기준 문서.

## 반드시 지킬 것

- 하위 라이브러리의 provider-native 필드명과 endpoint 철자는 이 패키지에서 임의로
  바꾸지 않습니다.
- 좌표 순서를 문서화 없이 섞지 않습니다. `Wgs84Point`는 `(lon, lat)`,
  `LatLon`은 `(lat, lon)`, `KmaGridPoint`는 `(nx, ny)`, 평면좌표는 `(x, y)`입니다.
- 지도 도메인 타입은 category와 별개입니다. 현재 최상위 도메인은 `place`, `event`,
  `route`, `area`, `notice`, `weather`입니다.
- `notice`는 지도 공지이고 `weather`는 날씨/대기질 정보 자체입니다. 단순 시스템 알림,
  ETL 실패, Telegram 운영 알림은 둘 다 아닙니다.
- `pyproj` import는 변환 함수 내부에서 lazy import합니다.
- 실제 API 키, 원본 비밀값, live 응답 fixture는 저장소에 남기지 않습니다.
- 문서의 파일 위치 정보는 프로젝트 루트 기준 상대 경로로 작성합니다.
- Python docstring과 내부 설명 문구는 한글로 작성하되, 코드 식별자와 API 필드명은
  원문을 유지합니다.
- PowerShell에서 한글 파일을 읽을 때는 `Get-Content -Encoding UTF8`을 사용합니다.

## 하위 라이브러리 이관 원칙

- 여러 하위 라이브러리에서 반복되는 타입이나 변환 로직은 `kraddr.base`로 끌어올리고,
  하위 라이브러리는 이 패키지를 직접 import합니다.
- 단순 위임용 wrapper, compatibility alias, mirror dataclass는 새로 만들지 않습니다. 기존
  provider 패키지에 그런 층이 있으면 새 코드에서는 제거하고 `kraddr.base` 타입을 파라미터나
  리턴값으로 직접 사용합니다.
- 이 원칙은 "최소 수정"보다 우선합니다. 공통 구현을 직접 쓰기 위해 공개 API 변경이
  필요하면 문서와 테스트를 함께 갱신해 새 경계를 명확히 합니다.
- `pykrtourpoi`의 category 정의는 `kraddr.base.categories`로 옮기고, `pykrtourpoi`는
  `python-kraddr-base`에 의존합니다. 별도 호환 wrapper를 새로 만들지 않습니다.
- `pymois`, `pyairkorea`, `opinet`, `pykma`, `kex-openapi`, `pykrairport`의 좌표 값 객체는
  새 코드부터 `kraddr.base.coordinates`를 우선 사용합니다.
- `pymcst`, `pykrforest`, `pykhoa`, `pykrtourapi`처럼 provider별 POI row를 갖는 패키지는
  `kraddr.base.poi.PoiRecord` 또는 더 작은 `PoiAddress`, `PoiContact`, `ProviderPoiRef`를
  경계 모델로 사용합니다.
- provider row가 TripMate 지도 객체 후보라면 `kraddr.base.domains.MapFeatureType`을
  `PoiRecord.feature_type`에 함께 싣습니다.
- provider별 특수 코드표는 그 provider 패키지에 남기되, 여러 패키지에서 재사용되는
  축약 enum은 이 패키지로 승격합니다.

## 검증

기본 검증:

```bash
python -m compileall src tests
python -m pytest
```

선택 검증:

```bash
ruff check .
mypy src/kraddr/base
```
