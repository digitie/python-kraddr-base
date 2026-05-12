from __future__ import annotations

from kraddr.base import (
    AirportProvider,
    FuelStationType,
    FuelType,
    PoiKind,
    PoiSource,
    PoiStatus,
    Wgs84Point,
    address_from_mapping,
    bjd_sido_to_opinet,
    fuel_station_type_from_opinet_lpg_yn,
    fuel_type_from_opinet_product,
    get_airport,
    is_budget_fuel_brand,
    list_airports,
    nearest_airport,
    opinet_product_code_for_fuel_type,
    opinet_sido_to_bjd,
    poi_from_mapping,
)


def test_poi_from_mapping_extracts_common_fields_and_redacts_raw() -> None:
    poi = poi_from_mapping(
        {
            "id": "BCH001",
            "name": "해운대해수욕장",
            "lat": "35.1587",
            "lon": "129.1604",
            "address": "부산광역시 해운대구",
            "tel": "051-000-0000",
            "serviceKey": "secret",
        },
        source=PoiSource.PYKHOA,
        kind=PoiKind.BEACH,
        dataset="beach_observatories",
    )

    assert poi.provider_id == "BCH001"
    assert poi.name == "해운대해수욕장"
    assert poi.coordinate == Wgs84Point(129.1604, 35.1587)
    assert poi.address is not None
    assert poi.address.display_address == "부산광역시 해운대구"
    assert poi.contact is not None
    assert poi.contact.tel == "051-000-0000"
    assert "serviceKey" not in poi.raw
    assert poi.status is PoiStatus.UNKNOWN


def test_address_from_mapping_reads_mois_and_opinet_names() -> None:
    address = address_from_mapping(
        {
            "ROAD_NM_ADDR": "서울특별시 종로구 세종대로 209",
            "LOTNO_ADDR": "서울특별시 종로구 세종로 1-91",
            "admCd": "1111011900",
            "rnMgtSn": "111103005028",
            "udrtYn": "0",
            "buldMnnm": "209",
            "buldSlno": "0",
        }
    )

    assert address is not None
    assert address.display_address == "서울특별시 종로구 세종대로 209"
    assert address.has_linkage_codes
    assert address.legal_dong_code == "1111011900"
    assert address.road_name_code == "111103005028"
    assert address.road_name_address_code == "11110119300502800020900000"
    assert address.address_codes.to_orm_dict()["road_name_code"] == "111103005028"
    assert address.to_jibun_address() is not None
    road_address = address.to_road_name_address()
    assert road_address is not None
    assert road_address.building_number_label == "209"
    combined = address.to_address()
    assert combined is not None
    assert combined.sigungu_code == "11110"


def test_airport_registry_and_nearest_airport() -> None:
    icn = get_airport("icn")

    assert icn.name_korean == "인천국제공항"
    assert icn.provider is AirportProvider.IIAC
    assert len(list_airports(provider=AirportProvider.KAC, active=True)) >= 10
    assert nearest_airport(lon=126.79, lat=37.56).code == "GMP"


def test_fuel_common_codes() -> None:
    assert fuel_type_from_opinet_product("B027") is FuelType.GASOLINE
    assert opinet_product_code_for_fuel_type(FuelType.DIESEL) == "D047"
    assert fuel_station_type_from_opinet_lpg_yn("C") is FuelStationType.BOTH
    assert is_budget_fuel_brand("RTE")
    assert opinet_sido_to_bjd("01") == "11"
    assert bjd_sido_to_opinet("51") == "03"
