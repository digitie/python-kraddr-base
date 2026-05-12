"""TripMate 장소 카테고리 체계.

이 모듈은 TripMate의 현재 장소 카테고리 seed 데이터를 그대로 반영한다. provider
adapter는 ingestion 코드 곳곳에 8자리 문자열을 직접 흩뿌리지 않고 이 모듈의
enum/dataclass 기반 데이터를 참조한다.

2026-05-09 기준 원본은 TripMate 프로젝트 루트 기준 상대 경로로 기록한다.

* ``docs/architecture/place-schema.md``: category code 형태와 Tier 1/Tier 2 용어.
* ``apps/api/app/etl/places/public_data_places.py``:
  현재 TripMate에 적재되는 ``_place_category_seeds()`` row.

TripMate category code는 ``AABBCCDD`` 형식이다.

* ``AA``: Tier 1
* ``BB``: Tier 2
* ``CC``: Tier 3
* ``DD``: Tier 4

없는 단계는 ``00``으로 채운다. 예를 들어 ``01050100``은
``관광 > 자연명소 > 해수욕장``이며 Tier 4 값은 없다.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Final, TextIO

from ._enum import StrEnum

TRIPMATE_CATEGORY_SOURCE: Final = (
    "apps/api/app/etl/places/public_data_places.py::_place_category_seeds"
)
TRIPMATE_CATEGORY_SCHEMA_DOC: Final = "docs/architecture/place-schema.md"
TRIPMATE_CATEGORY_SYNCED_ON: Final = "2026-05-09"


class TripMateTier1Code(StrEnum):
    """``place-schema.md``에서 가져온 TripMate Tier 1 category code."""

    UNCLASSIFIED = "00"
    TOURISM = "01"
    FOOD = "02"
    LODGING = "03"
    HOT_SPRING_SPA = "04"
    CONVENIENCE = "05"
    TRANSPORT = "06"
    MEDICAL = "07"


class TripMateCategoryCode(StrEnum):
    """현재 구현된 TripMate 8자리 category code.

    enum 값은 TripMate의 현재 seed row와 일치한다. provider mapping의 대상
    category가 확정되어 있으면 enum member를 사용하고, DB row, config file,
    upstream source에서 문자열 code가 들어오면 아래 lookup helper를 사용한다.
    """

    UNCLASSIFIED = "00000000"
    TOURISM = "01000000"
    TOURISM_BOTANICAL = "01030000"
    TOURISM_BOTANICAL_GARDEN = "01030100"
    TOURISM_BOTANICAL_GARDEN_NATIONAL = "01030101"
    TOURISM_BOTANICAL_GARDEN_PUBLIC = "01030102"
    TOURISM_BOTANICAL_GARDEN_PRIVATE = "01030103"
    TOURISM_NATURE = "01050000"
    TOURISM_NATURE_BEACH = "01050100"
    TOURISM_INFORMATION = "01060000"
    TOURISM_INFORMATION_CENTER = "01060100"
    TOURISM_INFORMATION_CENTER_PUBLIC = "01060101"
    TOURISM_CULTURAL_FACILITY = "01040000"
    TOURISM_CULTURAL_FACILITY_MUSEUM = "01040100"
    TOURISM_CULTURAL_FACILITY_MUSEUM_PUBLIC = "01040101"
    TOURISM_CULTURAL_FACILITY_MUSEUM_PRIVATE = "01040102"
    TOURISM_CULTURAL_FACILITY_MUSEUM_THEMED = "01040103"
    TOURISM_CULTURAL_FACILITY_ART = "01040200"
    TOURISM_CULTURAL_FACILITY_ART_MUSEUM = "01040201"
    TOURISM_CULTURAL_FACILITY_ART_GALLERY = "01040202"
    LODGING = "03000000"
    LODGING_RECREATION_FOREST = "03030000"
    LODGING_RECREATION_FOREST_NATIONAL = "03030100"
    LODGING_RECREATION_FOREST_NATIONAL_KFS = "03030101"
    LODGING_RECREATION_FOREST_PUBLIC = "03030200"
    LODGING_RECREATION_FOREST_PUBLIC_LOCAL = "03030201"
    LODGING_RECREATION_FOREST_PRIVATE = "03030300"
    LODGING_RECREATION_FOREST_PRIVATE_OPERATOR = "03030301"
    LODGING_CAMPGROUND = "03060000"
    LODGING_CAMPGROUND_AUTO = "03060100"
    LODGING_CAMPGROUND_AUTO_GENERAL_SITE = "03060101"
    LODGING_CAMPGROUND_AUTO_CARAVAN_SITE = "03060102"
    LODGING_CAMPGROUND_GLAMPING_CARAVAN = "03060200"
    LODGING_CAMPGROUND_GLAMPING = "03060201"
    LODGING_CAMPGROUND_CARAVAN_RENTAL = "03060202"


@dataclass(frozen=True, slots=True)
class TripMateCategory:
    """TripMate category seed 한 행.

    속성:
        code: 전체 8자리 ``AABBCCDD`` TripMate category code.
        tier1_code: 2자리 Tier 1 구간.
        tier2_code: 2자리 Tier 2 구간. 없으면 ``"00"``.
        tier3_code: 2자리 Tier 3 구간. 없으면 ``"00"``.
        tier4_code: 2자리 Tier 4 구간. 없으면 ``"00"``.
        tier1_name: 필수 Tier 1 표시명.
        tier2_name: 선택 Tier 2 표시명.
        tier3_name: 선택 Tier 3 표시명.
        tier4_name: 선택 Tier 4 표시명.
        depth: category 깊이. ``0``은 미분류 sentinel이고 ``1``부터 ``4``까지는
            일반 계층이다.
        parent_code: 부모 8자리 category code. root면 ``None``.
        sort_order: TripMate seed 정렬값.
        is_active: TripMate에서 활성 category인지 여부.

    ``path``와 ``label``은 UI text, log, mapping review output에서 쓰는 편의
    property다.
    """

    code: str
    tier1_code: str
    tier2_code: str
    tier3_code: str
    tier4_code: str
    tier1_name: str
    tier2_name: str | None
    tier3_name: str | None
    tier4_name: str | None
    depth: int
    parent_code: str | None
    sort_order: int
    is_active: bool = True

    @property
    def path(self) -> tuple[str, ...]:
        """비어 있지 않은 한국어 category path를 반환한다."""

        return tuple(
            part
            for part in (self.tier1_name, self.tier2_name, self.tier3_name, self.tier4_name)
            if part
        )

    @property
    def label(self) -> str:
        """사람이 읽기 쉬운 `` > `` 연결 category path를 반환한다."""

        return " > ".join(self.path)

    def as_dict(self) -> dict[str, object]:
        """이 category를 DB seed와 호환되는 dict로 반환한다."""

        return {
            "category_code": self.code,
            "tier1_code": self.tier1_code,
            "tier2_code": self.tier2_code,
            "tier3_code": self.tier3_code,
            "tier4_code": self.tier4_code,
            "tier1_name": self.tier1_name,
            "tier2_name": self.tier2_name,
            "tier3_name": self.tier3_name,
            "tier4_name": self.tier4_name,
            "depth": self.depth,
            "parent_category_code": self.parent_code,
            "sort_order": self.sort_order,
            "is_active": self.is_active,
        }


TRIPMATE_TIER1_NAMES: Final[dict[str, str]] = {
    "00": "미분류",
    "01": "관광",
    "02": "식음",
    "03": "숙박",
    "04": "온천·스파",
    "05": "편의",
    "06": "교통",
    "07": "의료",
}
"""``place-schema.md``에서 가져온 TripMate Tier 1 표시명."""


TRIPMATE_TIER2_NAMES_BY_TIER1: Final[dict[str, dict[str, str]]] = {
    "01": {
        "01": "테마파크",
        "02": "자연경관",
        "03": "수목원·식물원",
        "04": "문화시설",
        "05": "국가유산",
        "06": "액티비티",
    },
    "02": {"01": "음식점", "02": "카페"},
    "03": {
        "01": "호텔",
        "02": "리조트",
        "03": "휴양림",
        "04": "모텔",
        "05": "펜션",
        "06": "캠핑장",
        "07": "게스트하우스",
    },
    "04": {"01": "온천", "02": "찜질방·사우나", "03": "스파·테라피"},
    "05": {"01": "편의점", "02": "은행", "03": "마트", "04": "슈퍼마켓"},
    "06": {"01": "주차장", "02": "주유소", "03": "정류장", "04": "휴게소"},
    "07": {"01": "병원", "02": "약국"},
}
"""``place-schema.md``에서 가져온 TripMate Tier 2 표시명."""


def _category(
    code: TripMateCategoryCode,
    tier1_name: str,
    tier2_name: str | None,
    tier3_name: str | None,
    tier4_name: str | None,
    depth: int,
    parent_code: TripMateCategoryCode | None,
    sort_order: int,
) -> TripMateCategory:
    return TripMateCategory(
        code=code.value,
        tier1_code=code.value[0:2],
        tier2_code=code.value[2:4],
        tier3_code=code.value[4:6],
        tier4_code=code.value[6:8],
        tier1_name=tier1_name,
        tier2_name=tier2_name,
        tier3_name=tier3_name,
        tier4_name=tier4_name,
        depth=depth,
        parent_code=parent_code.value if parent_code else None,
        sort_order=sort_order,
    )


TRIPMATE_CATEGORY_DEFINITIONS: Final[tuple[TripMateCategory, ...]] = (
    _category(TripMateCategoryCode.UNCLASSIFIED, "미분류", None, None, None, 0, None, 0),
    _category(TripMateCategoryCode.TOURISM, "관광", None, None, None, 1, None, 10),
    _category(
        TripMateCategoryCode.TOURISM_BOTANICAL,
        "관광",
        "수목원·식물원",
        None,
        None,
        2,
        TripMateCategoryCode.TOURISM,
        30,
    ),
    _category(
        TripMateCategoryCode.TOURISM_BOTANICAL_GARDEN,
        "관광",
        "수목원·식물원",
        "수목원",
        None,
        3,
        TripMateCategoryCode.TOURISM_BOTANICAL,
        31,
    ),
    _category(
        TripMateCategoryCode.TOURISM_BOTANICAL_GARDEN_NATIONAL,
        "관광",
        "수목원·식물원",
        "수목원",
        "국립수목원",
        4,
        TripMateCategoryCode.TOURISM_BOTANICAL_GARDEN,
        311,
    ),
    _category(
        TripMateCategoryCode.TOURISM_BOTANICAL_GARDEN_PUBLIC,
        "관광",
        "수목원·식물원",
        "수목원",
        "공립수목원",
        4,
        TripMateCategoryCode.TOURISM_BOTANICAL_GARDEN,
        312,
    ),
    _category(
        TripMateCategoryCode.TOURISM_BOTANICAL_GARDEN_PRIVATE,
        "관광",
        "수목원·식물원",
        "수목원",
        "사립수목원",
        4,
        TripMateCategoryCode.TOURISM_BOTANICAL_GARDEN,
        313,
    ),
    _category(
        TripMateCategoryCode.TOURISM_NATURE,
        "관광",
        "자연명소",
        None,
        None,
        2,
        TripMateCategoryCode.TOURISM,
        50,
    ),
    _category(
        TripMateCategoryCode.TOURISM_NATURE_BEACH,
        "관광",
        "자연명소",
        "해수욕장",
        None,
        3,
        TripMateCategoryCode.TOURISM_NATURE,
        51,
    ),
    _category(
        TripMateCategoryCode.TOURISM_INFORMATION,
        "관광",
        "관광안내",
        None,
        None,
        2,
        TripMateCategoryCode.TOURISM,
        60,
    ),
    _category(
        TripMateCategoryCode.TOURISM_INFORMATION_CENTER,
        "관광",
        "관광안내",
        "관광안내소",
        None,
        3,
        TripMateCategoryCode.TOURISM_INFORMATION,
        61,
    ),
    _category(
        TripMateCategoryCode.TOURISM_INFORMATION_CENTER_PUBLIC,
        "관광",
        "관광안내",
        "관광안내소",
        "공공 관광안내소",
        4,
        TripMateCategoryCode.TOURISM_INFORMATION_CENTER,
        611,
    ),
    _category(
        TripMateCategoryCode.TOURISM_CULTURAL_FACILITY,
        "관광",
        "문화시설",
        None,
        None,
        2,
        TripMateCategoryCode.TOURISM,
        40,
    ),
    _category(
        TripMateCategoryCode.TOURISM_CULTURAL_FACILITY_MUSEUM,
        "관광",
        "문화시설",
        "박물관",
        None,
        3,
        TripMateCategoryCode.TOURISM_CULTURAL_FACILITY,
        41,
    ),
    _category(
        TripMateCategoryCode.TOURISM_CULTURAL_FACILITY_MUSEUM_PUBLIC,
        "관광",
        "문화시설",
        "박물관",
        "국공립 박물관",
        4,
        TripMateCategoryCode.TOURISM_CULTURAL_FACILITY_MUSEUM,
        411,
    ),
    _category(
        TripMateCategoryCode.TOURISM_CULTURAL_FACILITY_MUSEUM_PRIVATE,
        "관광",
        "문화시설",
        "박물관",
        "사립 박물관",
        4,
        TripMateCategoryCode.TOURISM_CULTURAL_FACILITY_MUSEUM,
        412,
    ),
    _category(
        TripMateCategoryCode.TOURISM_CULTURAL_FACILITY_MUSEUM_THEMED,
        "관광",
        "문화시설",
        "박물관",
        "테마 박물관",
        4,
        TripMateCategoryCode.TOURISM_CULTURAL_FACILITY_MUSEUM,
        413,
    ),
    _category(
        TripMateCategoryCode.TOURISM_CULTURAL_FACILITY_ART,
        "관광",
        "문화시설",
        "미술관·갤러리",
        None,
        3,
        TripMateCategoryCode.TOURISM_CULTURAL_FACILITY,
        42,
    ),
    _category(
        TripMateCategoryCode.TOURISM_CULTURAL_FACILITY_ART_MUSEUM,
        "관광",
        "문화시설",
        "미술관·갤러리",
        "미술관",
        4,
        TripMateCategoryCode.TOURISM_CULTURAL_FACILITY_ART,
        421,
    ),
    _category(
        TripMateCategoryCode.TOURISM_CULTURAL_FACILITY_ART_GALLERY,
        "관광",
        "문화시설",
        "미술관·갤러리",
        "갤러리",
        4,
        TripMateCategoryCode.TOURISM_CULTURAL_FACILITY_ART,
        422,
    ),
    _category(TripMateCategoryCode.LODGING, "숙박", None, None, None, 1, None, 300),
    _category(
        TripMateCategoryCode.LODGING_RECREATION_FOREST,
        "숙박",
        "휴양림",
        None,
        None,
        2,
        TripMateCategoryCode.LODGING,
        330,
    ),
    _category(
        TripMateCategoryCode.LODGING_RECREATION_FOREST_NATIONAL,
        "숙박",
        "휴양림",
        "국립휴양림",
        None,
        3,
        TripMateCategoryCode.LODGING_RECREATION_FOREST,
        331,
    ),
    _category(
        TripMateCategoryCode.LODGING_RECREATION_FOREST_NATIONAL_KFS,
        "숙박",
        "휴양림",
        "국립휴양림",
        "산림청 운영",
        4,
        TripMateCategoryCode.LODGING_RECREATION_FOREST_NATIONAL,
        3311,
    ),
    _category(
        TripMateCategoryCode.LODGING_RECREATION_FOREST_PUBLIC,
        "숙박",
        "휴양림",
        "공립휴양림",
        None,
        3,
        TripMateCategoryCode.LODGING_RECREATION_FOREST,
        332,
    ),
    _category(
        TripMateCategoryCode.LODGING_RECREATION_FOREST_PUBLIC_LOCAL,
        "숙박",
        "휴양림",
        "공립휴양림",
        "지자체 운영",
        4,
        TripMateCategoryCode.LODGING_RECREATION_FOREST_PUBLIC,
        3321,
    ),
    _category(
        TripMateCategoryCode.LODGING_RECREATION_FOREST_PRIVATE,
        "숙박",
        "휴양림",
        "사립휴양림",
        None,
        3,
        TripMateCategoryCode.LODGING_RECREATION_FOREST,
        333,
    ),
    _category(
        TripMateCategoryCode.LODGING_RECREATION_FOREST_PRIVATE_OPERATOR,
        "숙박",
        "휴양림",
        "사립휴양림",
        "민간 운영",
        4,
        TripMateCategoryCode.LODGING_RECREATION_FOREST_PRIVATE,
        3331,
    ),
    _category(
        TripMateCategoryCode.LODGING_CAMPGROUND,
        "숙박",
        "캠핑장",
        None,
        None,
        2,
        TripMateCategoryCode.LODGING,
        360,
    ),
    _category(
        TripMateCategoryCode.LODGING_CAMPGROUND_AUTO,
        "숙박",
        "캠핑장",
        "오토캠핑장",
        None,
        3,
        TripMateCategoryCode.LODGING_CAMPGROUND,
        361,
    ),
    _category(
        TripMateCategoryCode.LODGING_CAMPGROUND_AUTO_GENERAL_SITE,
        "숙박",
        "캠핑장",
        "오토캠핑장",
        "일반 사이트",
        4,
        TripMateCategoryCode.LODGING_CAMPGROUND_AUTO,
        3611,
    ),
    _category(
        TripMateCategoryCode.LODGING_CAMPGROUND_AUTO_CARAVAN_SITE,
        "숙박",
        "캠핑장",
        "오토캠핑장",
        "카라반·캠핑카 사이트",
        4,
        TripMateCategoryCode.LODGING_CAMPGROUND_AUTO,
        3612,
    ),
    _category(
        TripMateCategoryCode.LODGING_CAMPGROUND_GLAMPING_CARAVAN,
        "숙박",
        "캠핑장",
        "글램핑·카라반",
        None,
        3,
        TripMateCategoryCode.LODGING_CAMPGROUND,
        362,
    ),
    _category(
        TripMateCategoryCode.LODGING_CAMPGROUND_GLAMPING,
        "숙박",
        "캠핑장",
        "글램핑·카라반",
        "글램핑",
        4,
        TripMateCategoryCode.LODGING_CAMPGROUND_GLAMPING_CARAVAN,
        3621,
    ),
    _category(
        TripMateCategoryCode.LODGING_CAMPGROUND_CARAVAN_RENTAL,
        "숙박",
        "캠핑장",
        "글램핑·카라반",
        "카라반 대여",
        4,
        TripMateCategoryCode.LODGING_CAMPGROUND_GLAMPING_CARAVAN,
        3622,
    ),
)
"""TripMate에 현재 구현된 category seed row."""


TRIPMATE_CATEGORY_BY_CODE: Final[dict[str, TripMateCategory]] = {
    category.code: category for category in TRIPMATE_CATEGORY_DEFINITIONS
}
"""8자리 TripMate category code를 key로 쓰는 조회용 table."""


TRIPMATE_CATEGORY_CODES: Final[tuple[str, ...]] = tuple(
    category.code for category in TRIPMATE_CATEGORY_DEFINITIONS
)
"""현재 구현된 모든 TripMate category code. 순서는 seed 순서를 따른다."""


def get_category(code: str | TripMateCategoryCode) -> TripMateCategory:
    """8자리 code에 해당하는 TripMate category를 반환한다.

    예외:
        KeyError: ``code``가 현재 구현된 TripMate seed 집합에 없을 때 발생한다.
    """

    text_code = code.value if isinstance(code, TripMateCategoryCode) else str(code)
    return TRIPMATE_CATEGORY_BY_CODE[text_code]


def is_known_category_code(code: str | TripMateCategoryCode) -> bool:
    """``code``가 현재 TripMate seed 집합에 있으면 ``True``를 반환한다."""

    text_code = code.value if isinstance(code, TripMateCategoryCode) else str(code)
    return text_code in TRIPMATE_CATEGORY_BY_CODE


def iter_categories(
    *,
    depth: int | None = None,
    active_only: bool = True,
) -> Iterator[TripMateCategory]:
    """TripMate category를 seed 순서대로 순회한다.

    인자:
        depth: 선택 category depth filter. 예를 들어 ``4``를 넘기면 현재 Tier 4로
            정의된 leaf category만 순회한다.
        active_only: 비활성 category를 건너뛸지 여부. 현재 TripMate seed row는 모두
            활성 상태지만, 이후 category가 제거되지 않고 deprecate될 때 provider
            코드를 안정적으로 유지하기 위한 flag다.
    """

    for category in TRIPMATE_CATEGORY_DEFINITIONS:
        if depth is not None and category.depth != depth:
            continue
        if active_only and not category.is_active:
            continue
        yield category


def _category_node_name(category: TripMateCategory) -> str:
    if category.depth == 0:
        return category.tier1_name
    if category.depth == 1:
        return category.tier1_name
    if category.depth == 2:
        return category.tier2_name or category.label
    if category.depth == 3:
        return category.tier3_name or category.label
    if category.depth == 4:
        return category.tier4_name or category.label
    return category.label


def _category_node_label(category: TripMateCategory, *, include_codes: bool) -> str:
    name = _category_node_name(category)
    if not include_codes:
        return name
    return f"{name} [{category.code}]"


def _iter_category_tree_lines(
    parent_code: str | None,
    *,
    children_by_parent: dict[str | None, list[TripMateCategory]],
    prefix: str,
    include_codes: bool,
) -> Iterator[str]:
    children = children_by_parent.get(parent_code, [])

    for index, category in enumerate(children):
        is_last = index == len(children) - 1
        connector = "" if parent_code is None else ("└── " if is_last else "├── ")
        yield f"{prefix}{connector}{_category_node_label(category, include_codes=include_codes)}"

        child_prefix = prefix
        if parent_code is not None:
            child_prefix += "    " if is_last else "│   "
        yield from _iter_category_tree_lines(
            category.code,
            children_by_parent=children_by_parent,
            prefix=child_prefix,
            include_codes=include_codes,
        )


def format_category_tree(
    *,
    root_code: str | TripMateCategoryCode | None = None,
    include_codes: bool = True,
    active_only: bool = True,
) -> str:
    """TripMate category 전체 또는 일부를 트리 문자열로 반환한다.

    인자:
        root_code: 특정 category를 root로 삼아 하위 트리만 보고 싶을 때 넘긴다.
            ``None``이면 현재 구현된 모든 root category를 출력한다.
        include_codes: 각 node label에 8자리 category code를 함께 표시할지 여부.
        active_only: 비활성 category를 제외할지 여부.
    """

    categories = list(iter_categories(active_only=active_only))
    children_by_parent: dict[str | None, list[TripMateCategory]] = {}
    for category in categories:
        children_by_parent.setdefault(category.parent_code, []).append(category)

    for children in children_by_parent.values():
        children.sort(key=lambda category: (category.sort_order, category.code))

    if root_code is None:
        return "\n".join(
            _iter_category_tree_lines(
                None,
                children_by_parent=children_by_parent,
                prefix="",
                include_codes=include_codes,
            )
        )

    root = get_category(root_code)
    if active_only and not root.is_active:
        return ""

    lines = [_category_node_label(root, include_codes=include_codes)]
    lines.extend(
        _iter_category_tree_lines(
            root.code,
            children_by_parent=children_by_parent,
            prefix="",
            include_codes=include_codes,
        )
    )
    return "\n".join(lines)


def print_category_tree(
    *,
    root_code: str | TripMateCategoryCode | None = None,
    include_codes: bool = True,
    active_only: bool = True,
    stream: TextIO | None = None,
) -> None:
    """TripMate category tree를 출력한다.

    출력 문자열이 필요한 코드나 테스트에서는 ``format_category_tree``를 사용한다.
    """

    target = stream if stream is not None else sys.stdout
    print(
        format_category_tree(
            root_code=root_code,
            include_codes=include_codes,
            active_only=active_only,
        ),
        file=target,
    )


def category_path(code: str | TripMateCategoryCode) -> tuple[str, ...]:
    """``code``에 해당하는 한국어 category path를 반환한다."""

    return get_category(code).path


def category_label(code: str | TripMateCategoryCode, *, separator: str = " > ") -> str:
    """``code``의 category path를 ``separator``로 연결한 label로 반환한다."""

    return separator.join(category_path(code))
