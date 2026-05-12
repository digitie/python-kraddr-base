from __future__ import annotations

from io import StringIO

import pytest

from kraddr.base import (
    TRIPMATE_CATEGORY_BY_CODE,
    TRIPMATE_CATEGORY_CODES,
    TRIPMATE_CATEGORY_DEFINITIONS,
    TripMateCategoryCode,
    category_label,
    category_path,
    format_category_tree,
    get_category,
    is_known_category_code,
    iter_categories,
    print_category_tree,
)


def test_tripmate_category_seed_matches_current_tripmate_count() -> None:
    assert len(TRIPMATE_CATEGORY_DEFINITIONS) == 35
    assert len(TRIPMATE_CATEGORY_BY_CODE) == 35
    assert TRIPMATE_CATEGORY_CODES[0] == "00000000"


def test_tripmate_category_lookup_and_label() -> None:
    category = get_category(TripMateCategoryCode.TOURISM_NATURE_BEACH)

    assert category.code == "01050100"
    assert category.depth == 3
    assert category.parent_code == "01050000"
    assert category.path == ("관광", "자연명소", "해수욕장")
    assert category_label("01050100") == "관광 > 자연명소 > 해수욕장"
    assert category_path("03060202") == ("숙박", "캠핑장", "글램핑·카라반", "카라반 대여")


def test_tripmate_category_helpers_validate_codes() -> None:
    assert is_known_category_code("03060101")
    assert not is_known_category_code("99999999")

    with pytest.raises(KeyError):
        get_category("99999999")


def test_iter_categories_filters_depth() -> None:
    leaf_codes = {category.code for category in iter_categories(depth=4)}

    assert "01030101" in leaf_codes
    assert "03060202" in leaf_codes
    assert "01050100" not in leaf_codes


def test_format_category_tree_prints_full_hierarchy() -> None:
    tree = format_category_tree()

    assert "미분류 [00000000]" in tree
    assert "관광 [01000000]" in tree
    assert "├── 수목원·식물원 [01030000]" in tree
    assert "│   └── 수목원 [01030100]" in tree
    assert "숙박 [03000000]" in tree
    assert "└── 캠핑장 [03060000]" in tree


def test_format_category_tree_can_render_subtree_without_codes() -> None:
    tree = format_category_tree(
        root_code=TripMateCategoryCode.LODGING_CAMPGROUND,
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
    assert "└── 해수욕장 [01050100]" in output
