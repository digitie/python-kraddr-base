from __future__ import annotations

from io import StringIO

import pytest

from kraddr.base import (
    MAPBOX_MAKI_ICON_SOURCE,
    PLACE_CATEGORY_BY_CODE,
    PLACE_CATEGORY_CODES,
    PLACE_CATEGORY_DEFINITIONS,
    PLACE_CATEGORY_MAPBOX_MAKI_ICON_VALUES,
    PLACE_CATEGORY_MAPBOX_MAKI_ICONS,
    PLACE_CATEGORY_TIER2_NAMES_BY_TIER1,
    PlaceCategoryCode,
    category_label,
    category_path,
    format_category_tree,
    get_category,
    is_known_category_code,
    iter_categories,
    mapbox_maki_icon_for_category,
    mapbox_maki_icon_or_none,
    print_category_tree,
)


def test_place_category_seed_covers_expanded_taxonomy() -> None:
    assert len(PLACE_CATEGORY_DEFINITIONS) == 141
    assert len(PLACE_CATEGORY_BY_CODE) == 141
    assert PLACE_CATEGORY_CODES[0] == "00000000"


def test_place_category_lookup_and_label() -> None:
    category = get_category(PlaceCategoryCode.TOURISM_NATURE_BEACH)

    assert category.code == "01050100"
    assert category.depth == 3
    assert category.parent_code == "01050000"
    assert category.path == ("관광", "자연명소", "해수욕장")
    assert category_label("01050100") == "관광 > 자연명소 > 해수욕장"
    assert category_path("01010101") == ("관광", "테마파크", "놀이공원", "대형 테마파크")
    assert category_path("01010302") == ("관광", "테마파크", "동물원·수족관", "수족관")
    assert category_path("01070400") == ("관광", "국가유산", "한옥·민속마을")
    assert category_path("01080500") == ("관광", "액티비티", "트레킹·둘레길")
    assert category_path("02020101") == ("식음", "카페", "커피전문점", "프랜차이즈 카페")
    assert category_path("05050000") == ("편의", "백화점")
    assert category_path("03060202") == ("숙박", "캠핑장", "글램핑·카라반", "카라반 대여")
    assert category_path("07010200") == ("의료", "병원", "의원")
    assert category_path("06040101") == (
        "교통",
        "휴게소",
        "고속도로휴게소",
        "한국도로공사 휴게소",
    )
    assert category.mapbox_maki_icon == "beach"


def test_place_category_helpers_validate_codes() -> None:
    assert is_known_category_code("03060101")
    assert not is_known_category_code("99999999")

    with pytest.raises(KeyError):
        get_category("99999999")


def test_place_categories_have_mapbox_maki_icons() -> None:
    assert MAPBOX_MAKI_ICON_SOURCE == "https://github.com/mapbox/maki/tree/main/icons"
    assert set(PLACE_CATEGORY_MAPBOX_MAKI_ICONS) == set(PLACE_CATEGORY_CODES)
    assert PLACE_CATEGORY_MAPBOX_MAKI_ICON_VALUES == (
        "airport",
        "amusement-park",
        "aquarium",
        "art-gallery",
        "attraction",
        "bakery",
        "bank",
        "bar",
        "beach",
        "bus",
        "cafe",
        "campsite",
        "car",
        "castle",
        "cinema",
        "clothing-store",
        "convenience",
        "dentist",
        "doctor",
        "fast-food",
        "ferry",
        "fuel",
        "garden",
        "golf",
        "grocery",
        "highway-rest-area",
        "home",
        "hospital",
        "hot-spring",
        "information",
        "library",
        "lodging",
        "marker",
        "monument",
        "mountain",
        "museum",
        "natural",
        "park",
        "parking",
        "pharmacy",
        "pitch",
        "rail",
        "rail-metro",
        "religious-buddhist",
        "restaurant",
        "restaurant-sushi",
        "shop",
        "swimming",
        "taxi",
        "theatre",
        "toilet",
        "town-hall",
        "viewpoint",
        "village",
        "water",
        "zoo",
    )
    assert mapbox_maki_icon_for_category(PlaceCategoryCode.TOURISM_INFORMATION_CENTER) == (
        "information"
    )
    assert mapbox_maki_icon_for_category(PlaceCategoryCode.FOOD_CAFE_COFFEE_FRANCHISE) == ("cafe")
    assert mapbox_maki_icon_for_category(PlaceCategoryCode.TRANSPORT_REST_AREA_HIGHWAY_EX) == (
        "highway-rest-area"
    )
    assert mapbox_maki_icon_for_category(PlaceCategoryCode.CONVENIENCE_DEPARTMENT_STORE) == (
        "clothing-store"
    )
    assert mapbox_maki_icon_for_category(PlaceCategoryCode.TOURISM_HERITAGE_TEMPLE) == (
        "religious-buddhist"
    )
    assert mapbox_maki_icon_for_category("01040202") == "art-gallery"
    assert mapbox_maki_icon_for_category("03060202") == "campsite"
    assert mapbox_maki_icon_or_none("99999999") is None

    with pytest.raises(KeyError):
        mapbox_maki_icon_for_category("99999999")


def test_iter_categories_filters_depth() -> None:
    leaf_codes = {category.code for category in iter_categories(depth=4)}

    assert "01010101" in leaf_codes
    assert "01030101" in leaf_codes
    assert "02020101" in leaf_codes
    assert "03060202" in leaf_codes
    assert "06040101" in leaf_codes
    assert "07020100" not in leaf_codes
    assert "01050100" not in leaf_codes


def test_place_category_code_segments_match_paths_and_parents() -> None:
    for category in PLACE_CATEGORY_DEFINITIONS:
        segments = (
            category.code[0:2],
            category.code[2:4],
            category.code[4:6],
            category.code[6:8],
        )
        expected_depth = (
            0 if category.code == "00000000" else sum(segment != "00" for segment in segments)
        )

        assert category.depth == expected_depth
        assert category.path == tuple(
            name
            for name in (
                category.tier1_name,
                category.tier2_name,
                category.tier3_name,
                category.tier4_name,
            )
            if name
        )

        if category.depth <= 1:
            assert category.parent_code is None
            continue

        assert category.parent_code is not None
        assert PLACE_CATEGORY_BY_CODE[category.parent_code].path == category.path[:-1]


def test_place_category_tier2_table_matches_definitions() -> None:
    for tier1_code, tier2_names in PLACE_CATEGORY_TIER2_NAMES_BY_TIER1.items():
        for tier2_code, tier2_name in tier2_names.items():
            category = get_category(f"{tier1_code}{tier2_code}0000")

            assert category.depth == 2
            assert category.tier2_name == tier2_name


def test_format_category_tree_prints_full_hierarchy() -> None:
    tree = format_category_tree()

    assert "미분류 [00000000]" in tree
    assert "관광 [01000000]" in tree
    assert "├── 수목원·식물원 [01030000]" in tree
    assert "│   ├── 수목원 [01030100]" in tree
    assert "숙박 [03000000]" in tree
    assert "├── 캠핑장 [03060000]" in tree


def test_format_category_tree_can_render_subtree_without_codes() -> None:
    tree = format_category_tree(
        root_code=PlaceCategoryCode.LODGING_CAMPGROUND,
        include_codes=False,
    )

    assert tree.splitlines()[0] == "캠핑장"
    assert "├── 오토캠핑장" in tree
    assert "└── 글램핑·카라반" in tree
    assert "03060000" not in tree


def test_print_category_tree_writes_to_stream() -> None:
    stream = StringIO()

    print_category_tree(root_code="01050000", stream=stream)

    output = stream.getvalue()
    assert output.splitlines()[0] == "자연명소 [01050000]"
    assert "├── 해수욕장 [01050100]" in output
    assert "└── 전망대 [01050300]" in output
