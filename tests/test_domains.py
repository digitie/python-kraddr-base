from __future__ import annotations

import pytest

from kraddr.base import (
    MAP_FEATURE_TYPE_VALUES,
    TRIP_RESOURCE_TYPE_VALUES,
    MapFeatureType,
    PoiKind,
    PoiSource,
    TripResourceType,
    WeatherKind,
    coerce_map_feature_type,
    detail_kind_field_for_feature_type,
    detail_kind_values_for_feature_type,
    detail_table_for_feature_type,
    is_map_feature_resource_type,
    is_map_feature_type,
    map_feature_domain,
    poi_from_mapping,
    trip_resource_type_for_feature_type,
)


def test_map_feature_domains_include_weather() -> None:
    assert MAP_FEATURE_TYPE_VALUES == ("place", "event", "route", "area", "notice", "weather")
    assert detail_table_for_feature_type("weather") == "weather_details"
    assert detail_kind_field_for_feature_type(MapFeatureType.WEATHER) == "weather_kind"
    assert WeatherKind.AIR_QUALITY.value in detail_kind_values_for_feature_type("weather")

    weather = map_feature_domain("weather")
    assert weather.feature_type is MapFeatureType.WEATHER
    assert weather.label == "날씨"


def test_map_feature_type_coercion_and_resource_types() -> None:
    assert coerce_map_feature_type(TripResourceType.WEATHER) is MapFeatureType.WEATHER
    assert trip_resource_type_for_feature_type(MapFeatureType.ROUTE) is TripResourceType.ROUTE
    assert is_map_feature_type("notice")
    assert not is_map_feature_type("festival")
    assert is_map_feature_resource_type("weather")
    assert not is_map_feature_resource_type("festival")
    assert "weather" in TRIP_RESOURCE_TYPE_VALUES

    with pytest.raises(ValueError):
        coerce_map_feature_type("content")


def test_poi_record_can_carry_map_feature_type() -> None:
    poi = poi_from_mapping(
        {"id": "KMA-DFS-60-127", "name": "서울 단기예보", "lat": "37.5665", "lon": "126.9780"},
        source=PoiSource.PYKMA,
        kind=PoiKind.WEATHER_LOCATION,
        feature_type=MapFeatureType.WEATHER,
        dataset="weather_short_term",
    )

    assert poi.feature_type is MapFeatureType.WEATHER
    assert poi.feature_type_enum is MapFeatureType.WEATHER
