"""한국 주소 연계 코드 DTO와 정규화 helper."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Final

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from ._convert import first_value, strip_or_none

LEGAL_DONG_CODE_LENGTH: Final[int] = 10
"""법정동코드 전체 길이."""

SIGUNGU_CODE_LENGTH: Final[int] = 5
"""시군구코드 전체 길이."""

ROAD_NAME_CODE_LENGTH: Final[int] = 12
"""도로명코드(`rnMgtSn`) 전체 길이."""

ROAD_NAME_ADDRESS_CODE_LENGTH: Final[int] = 26
"""도로명주소관리번호 전체 길이."""

BUILDING_NUMBER_WIDTH: Final[int] = 5
"""도로명주소관리번호 안에서 건물 본번/부번을 보관하는 자리 수."""

LEGAL_DONG_CODE_KEYS: Final[tuple[str, ...]] = (
    "legal_dong_code",
    "legalDongCode",
    "admCd",
    "ADM_CD",
    "법정동코드",
    "행정구역코드",
)
SIGUNGU_CODE_KEYS: Final[tuple[str, ...]] = (
    "sigungu_code",
    "sigunguCode",
    "sggCd",
    "sggCode",
    "SIGUNGU_CD",
    "시군구코드",
)
ROAD_NAME_CODE_KEYS: Final[tuple[str, ...]] = (
    "road_name_code",
    "roadNameCode",
    "rnMgtSn",
    "RN_MGT_SN",
    "도로명코드",
)
ROAD_NAME_ADDRESS_CODE_KEYS: Final[tuple[str, ...]] = (
    "road_name_address_code",
    "roadNameAddressCode",
    "roadAddrMgtNo",
    "ROAD_ADDR_MGT_NO",
    "도로명주소관리번호",
)
BUILDING_MANAGEMENT_NUMBER_KEYS: Final[tuple[str, ...]] = (
    "building_management_number",
    "buildingManagementNumber",
    "bdMgtSn",
    "BD_MGT_SN",
    "건물관리번호",
)

_SEPARATOR_RE: Final[re.Pattern[str]] = re.compile(r"[\s\-_]")
_CODE_MODEL_CONFIG: Final[ConfigDict] = ConfigDict(
    extra="forbid",
    frozen=True,
    from_attributes=True,
    populate_by_name=True,
    str_strip_whitespace=True,
)


class SigunguCode(BaseModel):
    """시군구코드 DTO.

    값은 5자리 숫자 문자열이며 구성은 `시도(2)+시군구(3)`입니다. 일부 공공데이터는
    법정동코드 10자리 대신 이 코드까지만 제공하므로, 하위 주소가 없는 지역 단위 row의
    기준 코드로 사용합니다.
    """

    model_config = _CODE_MODEL_CONFIG

    code: str = Field(
        min_length=SIGUNGU_CODE_LENGTH,
        max_length=SIGUNGU_CODE_LENGTH,
        validation_alias=AliasChoices(*SIGUNGU_CODE_KEYS, "code"),
    )

    @field_validator("code", mode="before")
    @classmethod
    def _normalize_code(cls, value: Any) -> str:
        return normalize_sigungu_code(value)

    @classmethod
    def from_parts(cls, *, sido: Any, sigungu: Any) -> SigunguCode:
        """시도코드와 시군구 부분 코드로 시군구코드를 만듭니다."""

        sido_part = _normalize_code_part(sido, 2, "sido")
        sigungu_part = _normalize_code_part(sigungu, 3, "sigungu")
        return cls(code=f"{sido_part}{sigungu_part}")

    @classmethod
    def from_mapping(
        cls,
        row: Mapping[str, Any],
        *,
        keys: tuple[str, ...] = SIGUNGU_CODE_KEYS,
    ) -> SigunguCode:
        """mapping에서 시군구코드 후보 필드를 찾아 DTO를 만듭니다."""

        code = sigungu_code_from_mapping(row, keys=keys)
        if code is None:
            raise ValueError("mapping does not contain a sigungu code")
        return code

    @property
    def sido_code(self) -> str:
        return self.code[:2]

    @property
    def sigungu_part(self) -> str:
        return self.code[2:5]

    @property
    def legal_dong_code(self) -> LegalDongCode:
        """시군구 레벨 법정동코드 10자리 표현을 반환합니다."""

        return LegalDongCode(code=f"{self.code}00000")

    def to_orm_dict(self) -> dict[str, str]:
        """ORM DTO로 넘기기 쉬운 평면 dict를 반환합니다."""

        return {
            "sido_code": self.sido_code,
            "sigungu_code": self.code,
            "legal_dong_code": self.legal_dong_code.code,
        }

    def __str__(self) -> str:
        return self.code


class LegalDongCode(BaseModel):
    """법정동코드 DTO.

    값은 10자리 숫자 문자열이며 구성은 `시도(2)+시군구(3)+읍면동(3)+리(2)`입니다.
    """

    model_config = _CODE_MODEL_CONFIG

    code: str = Field(
        min_length=LEGAL_DONG_CODE_LENGTH,
        max_length=LEGAL_DONG_CODE_LENGTH,
        validation_alias=AliasChoices(*LEGAL_DONG_CODE_KEYS, "code"),
    )

    @field_validator("code", mode="before")
    @classmethod
    def _normalize_code(cls, value: Any) -> str:
        return normalize_legal_dong_code(value)

    @classmethod
    def from_parts(
        cls,
        *,
        sido: Any,
        sigungu: Any = "000",
        eup_myeon_dong: Any = "000",
        ri: Any = "00",
    ) -> LegalDongCode:
        """코드 구성 요소로 법정동코드를 만듭니다."""

        sido_part = _normalize_code_part(sido, 2, "sido")
        sigungu_part = _normalize_code_part(sigungu, 3, "sigungu")
        emd_part = _normalize_code_part(eup_myeon_dong, 3, "eup_myeon_dong")
        ri_part = _normalize_code_part(ri, 2, "ri")
        return cls(code=f"{sido_part}{sigungu_part}{emd_part}{ri_part}")

    @classmethod
    def from_mapping(
        cls,
        row: Mapping[str, Any],
        *,
        keys: tuple[str, ...] = LEGAL_DONG_CODE_KEYS,
    ) -> LegalDongCode:
        """mapping에서 법정동코드 후보 필드를 찾아 DTO를 만듭니다."""

        code = legal_dong_code_from_mapping(row, keys=keys)
        if code is None:
            raise ValueError("mapping does not contain a legal dong code")
        return code

    @property
    def adm_cd(self) -> str:
        """도로명주소 API에서 쓰는 `admCd` alias입니다."""

        return self.code

    @property
    def sido_code(self) -> str:
        return self.code[:2]

    @property
    def sigungu_part(self) -> str:
        return self.code[2:5]

    @property
    def sigungu_code(self) -> str:
        return self.code[:5]

    @property
    def eup_myeon_dong_part(self) -> str:
        return self.code[5:8]

    @property
    def eup_myeon_dong_code(self) -> str:
        return self.code[:8]

    @property
    def ri_part(self) -> str:
        return self.code[8:10]

    @property
    def is_sido_level(self) -> bool:
        return self.code[2:] == "00000000"

    @property
    def is_sigungu_level(self) -> bool:
        return self.sigungu_part != "000" and self.code[5:] == "00000"

    @property
    def is_eup_myeon_dong_level(self) -> bool:
        return self.eup_myeon_dong_part != "000" and self.ri_part == "00"

    @property
    def is_ri_level(self) -> bool:
        return self.ri_part != "00"

    @property
    def parent_code(self) -> LegalDongCode | None:
        """상위 행정구역 코드를 반환합니다."""

        if self.is_ri_level:
            return LegalDongCode(code=f"{self.eup_myeon_dong_code}00")
        if self.is_eup_myeon_dong_level:
            return LegalDongCode(code=f"{self.sigungu_code}00000")
        if self.is_sigungu_level:
            return LegalDongCode(code=f"{self.sido_code}00000000")
        return None

    def ancestors(self, *, include_self: bool = False) -> tuple[LegalDongCode, ...]:
        """시도부터 현재 코드까지 상위 코드를 순서대로 반환합니다."""

        values: list[LegalDongCode] = []
        current: LegalDongCode | None = self if include_self else self.parent_code
        while current is not None:
            values.append(current)
            current = current.parent_code
        return tuple(reversed(values))

    def is_descendant_of(self, other: LegalDongCode | str) -> bool:
        """현재 코드가 `other` 하위 코드인지 확인합니다."""

        parent = coerce_legal_dong_code(other)
        if parent.is_sido_level:
            return self.sido_code == parent.sido_code and self.code != parent.code
        if parent.is_sigungu_level:
            return self.sigungu_code == parent.sigungu_code and self.code != parent.code
        if parent.is_eup_myeon_dong_level:
            return self.eup_myeon_dong_code == parent.eup_myeon_dong_code and (
                self.code != parent.code
            )
        return False

    def to_parts(self) -> dict[str, str]:
        """코드 구성 요소를 ORM이나 로그에서 다루기 쉬운 dict로 반환합니다."""

        return {
            "sido_code": self.sido_code,
            "sigungu_code": self.sigungu_code,
            "eup_myeon_dong_code": self.eup_myeon_dong_code,
            "ri_code": self.ri_part,
        }

    def to_orm_dict(self) -> dict[str, str]:
        """ORM DTO로 넘기기 쉬운 평면 dict를 반환합니다."""

        return {"legal_dong_code": self.code, **self.to_parts()}

    def to_sigungu_code(self) -> SigunguCode:
        """현재 법정동코드의 시군구코드 5자리 표현을 반환합니다."""

        return SigunguCode(code=self.sigungu_code)

    def __str__(self) -> str:
        return self.code


class RoadNameCode(BaseModel):
    """도로명코드 DTO.

    값은 12자리 숫자 문자열이며 구성은 `시군구코드(5)+도로명번호(7)`입니다.
    """

    model_config = _CODE_MODEL_CONFIG

    code: str = Field(
        min_length=ROAD_NAME_CODE_LENGTH,
        max_length=ROAD_NAME_CODE_LENGTH,
        validation_alias=AliasChoices(*ROAD_NAME_CODE_KEYS, "code"),
    )

    @field_validator("code", mode="before")
    @classmethod
    def _normalize_code(cls, value: Any) -> str:
        return normalize_road_name_code(value)

    @classmethod
    def from_parts(cls, *, sigungu_code: Any, road_number: Any) -> RoadNameCode:
        """시군구코드와 도로명번호로 도로명코드를 만듭니다."""

        sigungu = normalize_sigungu_code(sigungu_code)
        road = _normalize_code_part(road_number, 7, "road_number")
        return cls(code=f"{sigungu}{road}")

    @classmethod
    def from_mapping(
        cls,
        row: Mapping[str, Any],
        *,
        keys: tuple[str, ...] = ROAD_NAME_CODE_KEYS,
    ) -> RoadNameCode:
        """mapping에서 도로명코드 후보 필드를 찾아 DTO를 만듭니다."""

        code = road_name_code_from_mapping(row, keys=keys)
        if code is None:
            raise ValueError("mapping does not contain a road name code")
        return code

    @property
    def rn_mgt_sn(self) -> str:
        """도로명주소 API에서 쓰는 `rnMgtSn` alias입니다."""

        return self.code

    @property
    def sigungu_code(self) -> str:
        return self.code[:5]

    @property
    def road_number(self) -> str:
        return self.code[5:12]

    def to_orm_dict(self) -> dict[str, str]:
        """ORM DTO로 넘기기 쉬운 평면 dict를 반환합니다."""

        return {
            "road_name_code": self.code,
            "road_name_sigungu_code": self.sigungu_code,
            "road_name_number": self.road_number,
        }

    def __str__(self) -> str:
        return self.code


class RoadNameAddressCode(BaseModel):
    """도로명주소관리번호 DTO.

    값은 26자리 숫자 문자열이며 구성은
    `시군구코드(5)+읍면동(3)+도로명번호(7)+지하여부(1)+건물본번(5)+건물부번(5)`입니다.
    """

    model_config = _CODE_MODEL_CONFIG

    code: str = Field(
        min_length=ROAD_NAME_ADDRESS_CODE_LENGTH,
        max_length=ROAD_NAME_ADDRESS_CODE_LENGTH,
        validation_alias=AliasChoices(*ROAD_NAME_ADDRESS_CODE_KEYS, "code"),
    )

    @field_validator("code", mode="before")
    @classmethod
    def _normalize_code(cls, value: Any) -> str:
        return normalize_road_name_address_code(value)

    @classmethod
    def from_components(
        cls,
        *,
        adm_cd: LegalDongCode | str,
        rn_mgt_sn: RoadNameCode | str,
        udrt_yn: Any,
        buld_mnnm: Any,
        buld_slno: Any = 0,
    ) -> RoadNameAddressCode:
        """도로명주소 API 구성 요소로 도로명주소관리번호를 만듭니다."""

        legal_dong = coerce_legal_dong_code(adm_cd)
        road_name = coerce_road_name_code(rn_mgt_sn)
        if legal_dong.sigungu_code != road_name.sigungu_code:
            raise ValueError(
                "adm_cd and rn_mgt_sn must share the same sigungu code: "
                f"{legal_dong.sigungu_code!r} != {road_name.sigungu_code!r}"
            )
        underground = normalize_underground_flag(udrt_yn)
        main_number = normalize_building_number(buld_mnnm)
        sub_number = normalize_building_number(buld_slno)
        return cls(
            code=(
                f"{legal_dong.sigungu_code}"
                f"{legal_dong.eup_myeon_dong_part}"
                f"{road_name.road_number}"
                f"{underground}"
                f"{main_number}"
                f"{sub_number}"
            )
        )

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> RoadNameAddressCode:
        """mapping에서 도로명주소관리번호 또는 구성 요소를 찾아 DTO를 만듭니다."""

        code = road_name_address_code_from_mapping(row)
        if code is None:
            raise ValueError("mapping does not contain a road name address code")
        return code

    @property
    def sigungu_code(self) -> str:
        return self.code[:5]

    @property
    def eup_myeon_dong_part(self) -> str:
        return self.code[5:8]

    @property
    def road_name_number(self) -> str:
        return self.code[8:15]

    @property
    def underground_flag(self) -> str:
        return self.code[15]

    @property
    def is_underground(self) -> bool:
        return self.underground_flag == "1"

    @property
    def building_main_code(self) -> str:
        return self.code[16:21]

    @property
    def building_sub_code(self) -> str:
        return self.code[21:26]

    @property
    def building_main_number(self) -> int:
        return int(self.building_main_code)

    @property
    def building_sub_number(self) -> int:
        return int(self.building_sub_code)

    @property
    def legal_dong_code(self) -> LegalDongCode:
        return LegalDongCode(code=f"{self.sigungu_code}{self.eup_myeon_dong_part}00")

    @property
    def road_name_code(self) -> RoadNameCode:
        return RoadNameCode(code=f"{self.sigungu_code}{self.road_name_number}")

    @property
    def rn_mgt_sn(self) -> str:
        return self.road_name_code.code

    @property
    def udrt_yn(self) -> str:
        return self.underground_flag

    @property
    def buld_mnnm(self) -> str:
        return str(self.building_main_number)

    @property
    def buld_slno(self) -> str:
        return str(self.building_sub_number)

    def to_juso_query_dict(self) -> dict[str, str]:
        """도로명주소 API 계열 요청 파라미터 모양으로 반환합니다."""

        return {
            "admCd": self.legal_dong_code.code,
            "rnMgtSn": self.rn_mgt_sn,
            "udrtYn": self.udrt_yn,
            "buldMnnm": self.buld_mnnm,
            "buldSlno": self.buld_slno,
        }

    def to_orm_dict(self) -> dict[str, str | int | bool]:
        """ORM DTO로 넘기기 쉬운 평면 dict를 반환합니다."""

        return {
            "road_name_address_code": self.code,
            "legal_dong_code": self.legal_dong_code.code,
            "road_name_code": self.road_name_code.code,
            "is_underground": self.is_underground,
            "building_main_number": self.building_main_number,
            "building_sub_number": self.building_sub_number,
        }

    def __str__(self) -> str:
        return self.code


class AddressCodeSet(BaseModel):
    """POI 주소 row에서 함께 보관할 주소 코드 묶음 DTO."""

    model_config = _CODE_MODEL_CONFIG

    sigungu_code: SigunguCode | None = None
    legal_dong_code: LegalDongCode | None = None
    road_name_code: RoadNameCode | None = None
    road_name_address_code: RoadNameAddressCode | None = None
    building_management_number: str | None = None

    @field_validator("sigungu_code", mode="before")
    @classmethod
    def _coerce_sigungu_code(cls, value: Any) -> SigunguCode | None:
        if value is None:
            return None
        return coerce_sigungu_code(value)

    @field_validator("legal_dong_code", mode="before")
    @classmethod
    def _coerce_legal_dong_code(cls, value: Any) -> LegalDongCode | None:
        if value is None:
            return None
        return coerce_legal_dong_code(value)

    @field_validator("road_name_code", mode="before")
    @classmethod
    def _coerce_road_name_code(cls, value: Any) -> RoadNameCode | None:
        if value is None:
            return None
        return coerce_road_name_code(value)

    @field_validator("road_name_address_code", mode="before")
    @classmethod
    def _coerce_road_name_address_code(cls, value: Any) -> RoadNameAddressCode | None:
        if value is None:
            return None
        return coerce_road_name_address_code(value)

    @field_validator("building_management_number", mode="before")
    @classmethod
    def _strip_building_management_number(cls, value: Any) -> str | None:
        return strip_or_none(value)

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> AddressCodeSet:
        """mapping에서 법정동/도로명주소 계열 코드를 찾아 묶음 DTO를 만듭니다."""

        road_name_address = road_name_address_code_from_mapping(row)
        legal_dong = legal_dong_code_from_mapping(row)
        sigungu = sigungu_code_from_mapping(row)
        road_name = road_name_code_from_mapping(row)
        if legal_dong is None and road_name_address is not None:
            legal_dong = road_name_address.legal_dong_code
        if sigungu is None and legal_dong is not None:
            sigungu = legal_dong.to_sigungu_code()
        if sigungu is None and road_name is not None:
            sigungu = SigunguCode(code=road_name.sigungu_code)
        if sigungu is None and road_name_address is not None:
            sigungu = SigunguCode(code=road_name_address.sigungu_code)
        if road_name is None and road_name_address is not None:
            road_name = road_name_address.road_name_code
        return cls(
            sigungu_code=sigungu,
            legal_dong_code=legal_dong,
            road_name_code=road_name,
            road_name_address_code=road_name_address,
            building_management_number=strip_or_none(
                first_value(row, *BUILDING_MANAGEMENT_NUMBER_KEYS)
            ),
        )

    def model_post_init(self, __context: Any) -> None:
        if self.sigungu_code is not None and self.legal_dong_code is not None:
            if self.sigungu_code.code != self.legal_dong_code.sigungu_code:
                raise ValueError("sigungu_code does not match legal_dong_code")
        if self.road_name_address_code is None:
            return
        derived_legal = self.road_name_address_code.legal_dong_code
        derived_road = self.road_name_address_code.road_name_code
        if (
            self.legal_dong_code is not None
            and self.legal_dong_code.eup_myeon_dong_code != derived_legal.eup_myeon_dong_code
        ):
            raise ValueError("legal_dong_code does not match road_name_address_code")
        if self.road_name_code is not None and self.road_name_code.code != derived_road.code:
            raise ValueError("road_name_code does not match road_name_address_code")
        if self.sigungu_code is not None and self.sigungu_code.code != derived_road.sigungu_code:
            raise ValueError("sigungu_code does not match road_name_address_code")

    @property
    def has_any_code(self) -> bool:
        return any(
            (
                self.legal_dong_code,
                self.sigungu_code,
                self.road_name_code,
                self.road_name_address_code,
                self.building_management_number,
            )
        )

    def to_orm_dict(self) -> dict[str, str | None]:
        """POI 주소 테이블에 넣기 쉬운 평면 dict를 반환합니다."""

        return {
            "sigungu_code": self.sigungu_code.code if self.sigungu_code else None,
            "legal_dong_code": self.legal_dong_code.code if self.legal_dong_code else None,
            "road_name_code": self.road_name_code.code if self.road_name_code else None,
            "road_name_address_code": (
                self.road_name_address_code.code if self.road_name_address_code else None
            ),
            "building_management_number": self.building_management_number,
        }


def coerce_sigungu_code(value: SigunguCode | str) -> SigunguCode:
    """지원하는 입력을 `SigunguCode`로 변환합니다."""

    if isinstance(value, SigunguCode):
        return value
    return SigunguCode(code=value)


def coerce_legal_dong_code(value: LegalDongCode | str) -> LegalDongCode:
    """지원하는 입력을 `LegalDongCode`로 변환합니다."""

    if isinstance(value, LegalDongCode):
        return value
    return LegalDongCode(code=value)


def coerce_road_name_code(value: RoadNameCode | str) -> RoadNameCode:
    """지원하는 입력을 `RoadNameCode`로 변환합니다."""

    if isinstance(value, RoadNameCode):
        return value
    return RoadNameCode(code=value)


def coerce_road_name_address_code(value: RoadNameAddressCode | str) -> RoadNameAddressCode:
    """지원하는 입력을 `RoadNameAddressCode`로 변환합니다."""

    if isinstance(value, RoadNameAddressCode):
        return value
    return RoadNameAddressCode(code=value)


def normalize_legal_dong_code(value: Any) -> str:
    """법정동코드를 10자리 숫자 문자열로 정규화합니다."""

    code = _normalize_numeric_code(value, LEGAL_DONG_CODE_LENGTH, "legal_dong_code")
    if code[:2] == "00":
        raise ValueError("legal_dong_code must have a non-zero sido code")
    return code


def normalize_legal_dong_code_or_none(value: Any) -> str | None:
    """빈값은 `None`, 값이 있으면 법정동코드 문자열을 반환합니다."""

    if strip_or_none(value) is None:
        return None
    return normalize_legal_dong_code(value)


def normalize_sigungu_code(value: Any) -> str:
    """시군구코드를 5자리 숫자 문자열로 정규화합니다."""

    code = _normalize_numeric_code(value, SIGUNGU_CODE_LENGTH, "sigungu_code")
    if code[:2] == "00":
        raise ValueError("sigungu_code must have a non-zero sido code")
    return code


def normalize_sigungu_code_or_none(value: Any) -> str | None:
    """빈값은 `None`, 값이 있으면 시군구코드 문자열을 반환합니다."""

    if strip_or_none(value) is None:
        return None
    return normalize_sigungu_code(value)


def normalize_road_name_code(value: Any) -> str:
    """도로명코드(`rnMgtSn`)를 12자리 숫자 문자열로 정규화합니다."""

    code = _normalize_numeric_code(value, ROAD_NAME_CODE_LENGTH, "road_name_code")
    normalize_sigungu_code(code[:5])
    return code


def normalize_road_name_code_or_none(value: Any) -> str | None:
    """빈값은 `None`, 값이 있으면 도로명코드 문자열을 반환합니다."""

    if strip_or_none(value) is None:
        return None
    return normalize_road_name_code(value)


def normalize_road_name_address_code(value: Any) -> str:
    """도로명주소관리번호를 26자리 숫자 문자열로 정규화합니다."""

    code = _normalize_numeric_code(
        value,
        ROAD_NAME_ADDRESS_CODE_LENGTH,
        "road_name_address_code",
    )
    normalize_sigungu_code(code[:5])
    underground_flag = code[15]
    if underground_flag not in {"0", "1"}:
        raise ValueError("road_name_address_code underground flag must be 0 or 1")
    return code


def normalize_road_name_address_code_or_none(value: Any) -> str | None:
    """빈값은 `None`, 값이 있으면 도로명주소관리번호 문자열을 반환합니다."""

    if strip_or_none(value) is None:
        return None
    return normalize_road_name_address_code(value)


def normalize_building_number(value: Any) -> str:
    """건물 본번/부번을 도로명주소관리번호용 5자리 문자열로 정규화합니다."""

    text = _compact_text(value, "building_number")
    if not text.isdigit():
        raise ValueError(f"building_number must contain only digits: {value!r}")
    number = int(text)
    if not 0 <= number < 10**BUILDING_NUMBER_WIDTH:
        raise ValueError("building_number must be between 0 and 99999")
    return f"{number:0{BUILDING_NUMBER_WIDTH}d}"


def normalize_underground_flag(value: Any) -> str:
    """지하여부 값을 도로명주소 API 규칙의 `0` 또는 `1`로 정규화합니다."""

    if isinstance(value, bool):
        return "1" if value else "0"
    text = strip_or_none(value)
    if text is None:
        raise ValueError("underground flag is empty")
    normalized = text.casefold()
    if normalized in {"0", "false", "f", "n", "no", "지상"}:
        return "0"
    if normalized in {"1", "true", "t", "y", "yes", "지하"}:
        return "1"
    raise ValueError(f"underground flag must be 0 or 1: {value!r}")


def legal_dong_code_from_mapping(
    row: Mapping[str, Any],
    *,
    keys: tuple[str, ...] = LEGAL_DONG_CODE_KEYS,
) -> LegalDongCode | None:
    """mapping에서 법정동코드 후보 필드를 찾아 DTO를 반환합니다."""

    value = first_value(row, *keys)
    if strip_or_none(value) is None:
        return None
    return LegalDongCode(code=value)


def sigungu_code_from_mapping(
    row: Mapping[str, Any],
    *,
    keys: tuple[str, ...] = SIGUNGU_CODE_KEYS,
) -> SigunguCode | None:
    """mapping에서 시군구코드 후보 필드를 찾아 DTO를 반환합니다."""

    value = first_value(row, *keys)
    if strip_or_none(value) is not None:
        return SigunguCode(code=value)
    legal_dong = legal_dong_code_from_mapping(row)
    if legal_dong is not None:
        return legal_dong.to_sigungu_code()
    road_name = road_name_code_from_mapping(row)
    if road_name is not None:
        return SigunguCode(code=road_name.sigungu_code)
    road_name_address = road_name_address_code_from_mapping(row)
    if road_name_address is not None:
        return SigunguCode(code=road_name_address.sigungu_code)
    return None


def road_name_code_from_mapping(
    row: Mapping[str, Any],
    *,
    keys: tuple[str, ...] = ROAD_NAME_CODE_KEYS,
) -> RoadNameCode | None:
    """mapping에서 도로명코드 후보 필드를 찾아 DTO를 반환합니다."""

    value = first_value(row, *keys)
    if strip_or_none(value) is None:
        return None
    return RoadNameCode(code=value)


def road_name_address_code_from_mapping(row: Mapping[str, Any]) -> RoadNameAddressCode | None:
    """mapping에서 도로명주소관리번호 또는 구성 요소를 찾아 DTO를 반환합니다."""

    direct = first_value(row, *ROAD_NAME_ADDRESS_CODE_KEYS)
    if strip_or_none(direct) is not None:
        return RoadNameAddressCode(code=direct)

    adm_cd = first_value(row, *LEGAL_DONG_CODE_KEYS)
    rn_mgt_sn = first_value(row, *ROAD_NAME_CODE_KEYS)
    udrt_yn = first_value(row, "udrtYn", "UDRT_YN", "underground_yn", "지하여부")
    buld_mnnm = first_value(row, "buldMnnm", "BULD_MNNM", "building_main_number", "건물본번")
    buld_slno = first_value(row, "buldSlno", "BULD_SLNO", "building_sub_number", "건물부번")
    values = (adm_cd, rn_mgt_sn, udrt_yn, buld_mnnm, buld_slno)
    if all(strip_or_none(value) is None for value in values):
        return None
    building_values = (udrt_yn, buld_mnnm, buld_slno)
    if all(strip_or_none(value) is None for value in building_values):
        return None
    if any(strip_or_none(value) is None for value in values):
        raise ValueError(
            "road name address code requires admCd, rnMgtSn, udrtYn, buldMnnm, and buldSlno"
        )
    return RoadNameAddressCode.from_components(
        adm_cd=str(adm_cd),
        rn_mgt_sn=str(rn_mgt_sn),
        udrt_yn=udrt_yn,
        buld_mnnm=buld_mnnm,
        buld_slno=buld_slno,
    )


def address_code_set_from_mapping(row: Mapping[str, Any]) -> AddressCodeSet:
    """mapping에서 주소 코드 묶음 DTO를 생성합니다."""

    return AddressCodeSet.from_mapping(row)


def _normalize_numeric_code(value: Any, length: int, field_name: str) -> str:
    text = _compact_text(value, field_name)
    if not text.isdigit():
        raise ValueError(f"{field_name} must contain only digits: {value!r}")
    if len(text) != length:
        raise ValueError(f"{field_name} must be {length} digits: {value!r}")
    return text


def _normalize_code_part(value: Any, length: int, field_name: str) -> str:
    text = _compact_text(value, field_name)
    if not text.isdigit():
        raise ValueError(f"{field_name} must contain only digits: {value!r}")
    if len(text) > length:
        raise ValueError(f"{field_name} must be at most {length} digits: {value!r}")
    return text.zfill(length)


def _compact_text(value: Any, field_name: str) -> str:
    text = strip_or_none(value)
    if text is None:
        raise ValueError(f"{field_name} is empty")
    return _SEPARATOR_RE.sub("", text)
