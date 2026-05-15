from __future__ import annotations

import pytest

from kraddr.base import (
    Address,
    AddressRegion,
    JibunAddress,
    KatecPoint,
    LegalDongCode,
    PlaceCoordinate,
    RoadNameAddress,
    RoadNameAddressCode,
    RoadNameCode,
    SigunguCode,
    Wgs84Point,
    address_region_from_mapping,
    address_region_from_text,
    jibun_address_from_mapping,
    place_address_from_mapping,
    place_coordinate_from_mapping,
    road_name_address_from_mapping,
)


def test_place_coordinate_normalizes_and_serializes_for_sqlalchemy() -> None:
    coord = PlaceCoordinate(lon="126.9780", lat="37.5665", accuracy_m="3.5")

    assert coord.map_x == 126.978
    assert coord.map_y == 37.5665
    assert coord.as_lon_lat() == (126.978, 37.5665)
    assert coord.as_lat_lon() == (37.5665, 126.978)
    assert coord.to_wgs84_point() == Wgs84Point(126.978, 37.5665)
    assert coord.to_wkt() == "POINT(126.978 37.5665)"
    assert coord.to_ewkt() == "SRID=4326;POINT(126.978 37.5665)"
    assert coord.to_geojson_geometry() == {
        "type": "Point",
        "coordinates": [126.978, 37.5665],
    }
    assert coord.to_sqlalchemy_values(
        lon_field="lon",
        lat_field="lat",
        geometry_field="geom",
    ) == {
        "lon": 126.978,
        "lat": 37.5665,
        "altitude_m": None,
        "accuracy_m": 3.5,
        "srid": 4326,
        "geom": "SRID=4326;POINT(126.978 37.5665)",
    }


def test_place_coordinate_mapping_and_coordinate_conversions() -> None:
    coord = place_coordinate_from_mapping({"mapx": "129.1604", "mapy": "35.1587"})

    assert coord == PlaceCoordinate(lon=129.1604, lat=35.1587)
    assert place_coordinate_from_mapping({"mapX": "126.9769", "mapY": "37.5796"}) == (
        PlaceCoordinate(lon=126.9769, lat=37.5796)
    )
    assert PlaceCoordinate.model_validate({"map_x": "126.9769", "map_y": "37.5796"}) == (
        PlaceCoordinate(lon=126.9769, lat=37.5796)
    )
    assert place_coordinate_from_mapping({"xValue": "127.104165", "yValue": "37.332651"}) == (
        PlaceCoordinate(lon=127.104165, lat=37.332651)
    )
    assert place_coordinate_from_mapping({"xValue": "-99.000000", "yValue": "-99.000000"}) is None
    assert PlaceCoordinate.from_tuple((35.1587, 129.1604), order="lat_lon") == coord
    assert PlaceCoordinate.from_values("129° 9' 37.44\" E", "35° 9' 31.32\" N") == coord
    assert PlaceCoordinate.from_wgs84_point(Wgs84Point(129.1604, 35.1587)) == coord
    assert isinstance(coord.to_katec(), KatecPoint)
    assert coord.to_kma_grid().nx > 0


def test_place_coordinate_uses_opinet_katec_projection() -> None:
    gangnam = PlaceCoordinate(lon=127.0276, lat=37.4979)
    katec = gangnam.to_katec()

    assert katec.x == pytest.approx(314213.3092)
    assert katec.y == pytest.approx(544413.5797)

    station = PlaceCoordinate.from_katec(KatecPoint(314871.8, 544012.0))

    assert station.lon == pytest.approx(127.0350927851)
    assert station.lat == pytest.approx(37.4943428508)
    assert station.distance_to_km(gangnam) == pytest.approx(0.77, abs=0.1)


def test_place_coordinate_rejects_invalid_range() -> None:
    with pytest.raises(ValueError):
        PlaceCoordinate(lon=200, lat=37)
    with pytest.raises(ValueError):
        PlaceCoordinate(lon=127, lat=95)
    with pytest.raises(ValueError):
        PlaceCoordinate(lon=127, lat=37, srid=5174)


def test_jibun_address_exposes_legal_dong_parts_and_orm_values() -> None:
    jibun = JibunAddress(
        address="서울특별시 종로구 세종로 1-91",
        legal_dong_code="1111011900",
        sido_name="서울특별시",
        sigungu_name="종로구",
        eup_myeon_dong_name="세종로",
        lot_main_number="1",
        lot_sub_number="91",
    )

    assert jibun.display_address == "서울특별시 종로구 세종로 1-91"
    assert jibun.sigungu_code == "11110"
    assert jibun.eup_myeon_dong_code == "11110119"
    assert jibun.ri_code == "00"
    assert jibun.lot_number_label == "1-91"
    assert jibun.administrative_label == "서울특별시 종로구 세종로"
    assert jibun.to_sqlalchemy_values()["legal_dong_code"] == "1111011900"
    assert jibun.to_sqlalchemy_values()["jibun_lot_sub_number"] == 91


def test_address_region_accepts_sigungu_only_rows() -> None:
    region = AddressRegion.from_sigungu_code(
        "11110",
        sido_name="서울특별시",
        sigungu_name="종로구",
    )

    assert region.effective_sigungu_code == SigunguCode(code="11110")
    assert region.sido_code == "11"
    assert region.sigungu_code_value == "11110"
    assert region.legal_dong_code is None
    assert region.has_lower_region_code is False
    assert region.administrative_label == "서울특별시 종로구"
    assert region.to_sqlalchemy_values()["sigungu_code"] == "11110"


def test_address_region_from_mapping_derives_sigungu_from_legal_dong() -> None:
    region = address_region_from_mapping(
        {
            "ADM_CD": "1111011900",
            "siNm": "서울특별시",
            "sggNm": "종로구",
            "emdNm": "세종로",
        }
    )

    assert region is not None
    assert region.effective_sigungu_code == SigunguCode(code="11110")
    assert region.legal_dong_code == LegalDongCode(code="1111011900")
    assert region.has_lower_region_code is True
    assert region.eup_myeon_dong_code == "11110119"


def test_address_region_from_text_extracts_names_without_guessing_codes() -> None:
    region = address_region_from_text("경기 용인시 수지구 풍덕천동 42-1")

    assert region is not None
    assert region.sido_name == "경기도"
    assert region.sigungu_name == "용인시 수지구"
    assert region.eup_myeon_dong_name == "풍덕천동"
    assert region.legal_dong_code is None
    assert region.sigungu_code is None


def test_jibun_address_accepts_sigungu_only_region() -> None:
    jibun = JibunAddress(region=AddressRegion.from_sigungu_code("11110"))

    assert jibun.display_address is None
    assert jibun.sigungu_code == "11110"
    assert jibun.eup_myeon_dong_code is None
    assert jibun.to_sqlalchemy_values()["sigungu_code"] == "11110"
    assert jibun.to_sqlalchemy_values()["legal_dong_code"] is None


def test_jibun_address_from_mapping_reads_provider_keys() -> None:
    jibun = jibun_address_from_mapping(
        {
            "LOTNO_ADDR": "서울특별시 종로구 세종로 1-91",
            "ADM_CD": "1111011900",
            "lnbrMnnm": "1",
            "lnbrSlno": "91",
            "mtYn": "0",
        }
    )

    assert jibun is not None
    assert jibun.legal_dong_code == LegalDongCode(code="1111011900")
    assert jibun.is_mountain is False
    assert jibun.lot_number_label == "1-91"


def test_road_name_address_composes_codes_and_orm_values() -> None:
    road = RoadNameAddress.from_components(
        address="세종특별자치시 한누리대로 2130",
        adm_cd="3611011000",
        rn_mgt_sn="361103258085",
        udrt_yn="0",
        buld_mnnm="572",
        buld_slno="0",
        postal_code="30151",
    )

    assert road.road_name_address_code == RoadNameAddressCode(
        code="36110110325808500057200000"
    )
    assert road.effective_legal_dong_code == LegalDongCode(code="3611011000")
    assert road.effective_road_name_code == RoadNameCode(code="361103258085")
    assert road.sigungu_code == "36110"
    assert road.road_name_number == "3258085"
    assert road.building_number_label == "572"
    assert road.to_juso_query_dict()["buldMnnm"] == "572"
    assert road.to_sqlalchemy_values()["road_name_address_code"] == (
        "36110110325808500057200000"
    )


def test_road_name_address_from_mapping_accepts_partial_codes() -> None:
    road = road_name_address_from_mapping(
        {
            "ROAD_NM_ADDR": "서울특별시 종로구 세종대로 209",
            "admCd": "1111011900",
            "rnMgtSn": "111103005028",
        }
    )

    assert road is not None
    assert road.display_address == "서울특별시 종로구 세종대로 209"
    assert road.effective_legal_dong_code == LegalDongCode(code="1111011900")
    assert road.effective_road_name_code == RoadNameCode(code="111103005028")
    assert road.road_name_address_code is None


def test_road_name_address_accepts_sigungu_only_region() -> None:
    road = RoadNameAddress(region=AddressRegion.from_sigungu_code("11110"))

    assert road.display_address is None
    assert road.sigungu_code == "11110"
    assert road.eup_myeon_dong_code is None
    assert road.to_sqlalchemy_values()["sigungu_code"] == "11110"
    assert road.to_sqlalchemy_values()["road_name_code"] is None


def test_address_combines_region_jibun_and_road_name() -> None:
    address = place_address_from_mapping(
        {
            "sigungu_code": "11110",
            "ROAD_NM_ADDR": "서울특별시 종로구 세종대로 209",
            "LOTNO_ADDR": "서울특별시 종로구 세종로 1-91",
            "admCd": "1111011900",
            "rnMgtSn": "111103005028",
            "zipNo": "03172",
            "detail_address": "정부서울청사",
        }
    )

    assert address is not None
    assert isinstance(address, Address)
    assert address.sigungu_code == "11110"
    assert address.legal_dong_code == "1111011900"
    assert address.display_address == "서울특별시 종로구 세종대로 209"
    assert address.detail_address == "정부서울청사"
    assert address.has_detail_address is True
    assert address.to_sqlalchemy_values()["road_address"] == "서울특별시 종로구 세종대로 209"
    assert address.to_sqlalchemy_values()["jibun_address"] == "서울특별시 종로구 세종로 1-91"
    assert address.to_sqlalchemy_values()["detail_address"] == "정부서울청사"


def test_address_from_text_preserves_raw_address_without_guessing_code() -> None:
    address = Address.from_text("경기 용인시 수지구 풍덕천동 42-1")

    assert address is not None
    assert address.address == "경기 용인시 수지구 풍덕천동 42-1"
    assert address.display_address == "경기 용인시 수지구 풍덕천동 42-1"
    assert address.region is not None
    assert address.region.sido_name == "경기도"
    assert address.region.sigungu_name == "용인시 수지구"
    assert address.region.eup_myeon_dong_name == "풍덕천동"
    assert address.legal_dong_code is None
    assert address.has_detail_address is True


def test_address_from_mapping_merges_provider_code_with_parsed_text() -> None:
    address = Address.from_mapping(
        {
            "svarAddr": "경기 용인시 수지구 풍덕천동 42-1",
            "ADM_CD": "4146510100",
        }
    )

    assert address is not None
    assert address.address == "경기 용인시 수지구 풍덕천동 42-1"
    assert address.display_address == "경기 용인시 수지구 풍덕천동 42-1"
    assert address.effective_region is not None
    assert address.effective_region.sido_name == "경기도"
    assert address.effective_region.sigungu_name == "용인시 수지구"
    assert address.effective_region.eup_myeon_dong_name == "풍덕천동"
    assert address.legal_dong_code == "4146510100"
    assert address.sigungu_code == "41465"


def test_address_from_mapping_accepts_expressway_addr_key() -> None:
    address = Address.from_mapping({"addr": "경기도 용인시 수지구 풍덕천동 42-1"})

    assert address is not None
    assert address.address == "경기도 용인시 수지구 풍덕천동 42-1"
    assert address.display_address == "경기도 용인시 수지구 풍덕천동 42-1"
    assert address.region is not None
    assert address.region.sido_name == "경기도"
    assert address.region.sigungu_name == "용인시 수지구"
    assert address.region.eup_myeon_dong_name == "풍덕천동"


def test_address_can_hold_only_region() -> None:
    address = Address(region=AddressRegion.from_sigungu_code("11110"))

    assert address.sigungu_code == "11110"
    assert address.display_address is None
    assert address.has_detail_address is False
    assert address.to_sqlalchemy_values()["sigungu_code"] == "11110"
    assert address.to_sqlalchemy_values()["road_address"] is None

    mapped = place_address_from_mapping({"sigungu_code": "11110"})

    assert mapped is not None
    assert mapped.sigungu_code == "11110"
    assert mapped.jibun is None
    assert mapped.road_name is None
