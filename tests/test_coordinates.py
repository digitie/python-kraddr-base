from __future__ import annotations

import pytest

from pykrtour import (
    CoordinateReferenceSystem,
    KmaGridPoint,
    LatLon,
    Wgs84Point,
    coerce_latlon,
    coerce_wgs84_point,
    coordinate_from_mapping,
    haversine_distance_m,
    kma_grid_to_wgs84,
    to_decimal_degrees,
    wgs84_to_kma_grid,
)


def test_wgs84_point_standardizes_lon_lat_order() -> None:
    point = Wgs84Point(lon=126.978, lat=37.5665)

    assert point.as_tuple() == (126.978, 37.5665)
    assert point.as_lat_lon() == (37.5665, 126.978)
    assert point.as_geojson_position() == (126.978, 37.5665)
    assert point.to_wkt() == "POINT(126.978 37.5665)"
    assert point.crs is CoordinateReferenceSystem.WGS84


def test_latlon_keeps_human_readable_order_and_converts_to_point() -> None:
    value = LatLon("37.5665", "126.9780")  # type: ignore[arg-type]

    assert value.as_tuple() == (37.5665, 126.978)
    assert value.to_wgs84_point() == Wgs84Point(126.978, 37.5665)
    assert coerce_latlon({"latitude": "37.5", "longitude": "127.0"}) == LatLon(37.5, 127.0)
    assert coerce_wgs84_point({"lat": "37.5", "lon": "127.0"}) == Wgs84Point(127.0, 37.5)


def test_coordinate_from_mapping_accepts_common_provider_keys() -> None:
    assert coordinate_from_mapping({"mapx": "129.1604", "mapy": "35.1587"}) == Wgs84Point(
        129.1604,
        35.1587,
    )
    assert coordinate_from_mapping({}) is None


def test_coordinate_validation_rejects_out_of_range_values() -> None:
    with pytest.raises(ValueError):
        Wgs84Point(200, 37)
    with pytest.raises(ValueError):
        LatLon(95, 127)


def test_dms_coordinate_parser() -> None:
    assert to_decimal_degrees("34° 45' 36\" N", kind="latitude") == pytest.approx(34.76)
    assert to_decimal_degrees("126° 22' 49\" E", kind="longitude") == pytest.approx(
        126.38027777777778
    )
    assert to_decimal_degrees("126.38027777 East", kind="longitude") == pytest.approx(
        126.38027777
    )


def test_kma_grid_conversion_known_seoul_point() -> None:
    grid = wgs84_to_kma_grid(37.5665, 126.9780)

    assert grid == KmaGridPoint(60, 127)
    assert kma_grid_to_wgs84(60, 127).lat == pytest.approx(37.5799, abs=0.02)


def test_haversine_distance_m() -> None:
    seoul = Wgs84Point(126.978, 37.5665)
    gimpo = Wgs84Point(126.791, 37.5583)

    assert haversine_distance_m(seoul, gimpo) == pytest.approx(16_500, rel=0.2)
