from datetime import date
from pathlib import Path
import re
from types import SimpleNamespace
from typing import cast

import pytest
from dcs.planes import F_16C_50, FA_18C_hornet

from game.data.weapons import Weapon, WeaponGroup, WeaponType
from game.ato.loadouts import Loadout
from game.dcs.aircrafttype import AircraftType
from game.factions.faction import Faction


def _bare_weapon(clsid: str) -> Weapon:
    group = WeaponGroup(
        name=f"test-{clsid}",
        type=WeaponType.UNKNOWN,
        introduction_year=None,
        fallback_name=None,
    )
    return Weapon(clsid=clsid, weapon_group=group)


def _f16c_50() -> AircraftType:
    return cast(
        AircraftType,
        SimpleNamespace(dcs_unit_type=F_16C_50, has_built_in_target_pod=False),
    )


def _fa_18c_hornet() -> AircraftType:
    return cast(
        AircraftType,
        SimpleNamespace(dcs_unit_type=FA_18C_hornet, has_built_in_target_pod=False),
    )


@pytest.mark.parametrize(
    "clsid",
    [
        "{LAU-131 - 7 AGR-20A}",
        "{LAU-131 - 7 AGR-20 M282}",
        "{BRU-32 GBU-12}",
        "DIS_GBU_12",
    ],
)
def test_accepts_laser_code_true_for_laser_guided_weapons(clsid: str) -> None:
    assert _bare_weapon(clsid).accepts_laser_code() is True


@pytest.mark.parametrize(
    "clsid",
    [
        "<CLEAN>",
        "{AUF2_MK82}",
        "definitely-not-a-real-clsid",
    ],
)
def test_accepts_laser_code_false_for_non_laser_or_unknown(clsid: str) -> None:
    assert _bare_weapon(clsid).accepts_laser_code() is False


def test_aaq_33_has_era_data_and_degrades_on_pre_intro_f16() -> None:
    weapon = Weapon.with_clsid("{AN_AAQ_33}")

    assert weapon is not None
    assert weapon.weapon_group.name == "AN/AAQ-33 - Advanced Targeting Pod"
    assert weapon.weapon_group.introduction_year == 2005

    faction = cast(Faction, SimpleNamespace(weapons_introduction_year_overrides={}))
    assert weapon.available_on(date(2004, 1, 1), faction) is False
    assert weapon.available_on(date(2005, 1, 1), faction) is True

    loadout = Loadout("Test", {11: weapon}, date=None)
    aircraft = _f16c_50()
    degraded = loadout.degrade_for_date(aircraft, date(2004, 1, 1), faction)

    degraded_weapon = degraded.pylons.get(11)
    assert degraded_weapon is None


def test_f16_litening_is_not_available_before_viper_integration_year() -> None:
    litening = Weapon.with_clsid("{A111396E-D3E8-4b9c-8AC9-2432489304D5}")

    assert litening is not None
    assert litening.weapon_group.name == "AN/AAQ-28 LITENING"
    assert litening.weapon_group.introduction_year == 1999

    faction = cast(Faction, SimpleNamespace(weapons_introduction_year_overrides={}))
    aircraft = _f16c_50()
    loadout = Loadout("Test", {11: litening}, date=None, is_custom=True)

    degraded = loadout.degrade_for_date(aircraft, date(2002, 1, 1), faction)
    assert degraded.pylons.get(11) is None

    available = loadout.degrade_for_date(aircraft, date(2005, 1, 1), faction)
    assert available.pylons.get(11) == litening


def test_f16_2002_sead_sweep_keeps_hts_but_removes_targeting_pod() -> None:
    hts = Weapon.with_clsid("{AN_ASQ_213}")
    atp = Weapon.with_clsid("{AN_AAQ_33}")

    assert hts is not None
    assert atp is not None

    faction = cast(Faction, SimpleNamespace(weapons_introduction_year_overrides={}))
    aircraft = _f16c_50()
    loadout = Loadout("Retribution SEAD Sweep", {10: hts, 11: atp}, date=None)

    degraded = loadout.degrade_for_date(aircraft, date(2002, 1, 1), faction)

    assert degraded.pylons.get(10) == hts
    assert degraded.pylons.get(11) is None


def test_hornet_litening_is_not_available_before_atflir_year() -> None:
    litening = Weapon.with_clsid("{AAQ-28_LEFT}")

    assert litening is not None
    assert litening.weapon_group.name == "AN/AAQ-28 LITENING"
    assert litening.weapon_group.introduction_year == 1999

    faction = cast(Faction, SimpleNamespace(weapons_introduction_year_overrides={}))
    aircraft = _fa_18c_hornet()
    loadout = Loadout("Test", {4: litening}, date=None, is_custom=True)

    degraded = loadout.degrade_for_date(aircraft, date(2002, 1, 1), faction)
    degraded_weapon = degraded.pylons.get(4)
    assert degraded_weapon is not None
    assert degraded_weapon.weapon_group.type is not WeaponType.TGP

    available = loadout.degrade_for_date(aircraft, date(2003, 1, 1), faction)
    assert available.pylons.get(4) == litening


def test_hornet_2002_atflir_does_not_fall_back_to_litening() -> None:
    atflir = Weapon.with_clsid("{AN_ASQ_228}")

    assert atflir is not None
    assert atflir.weapon_group.name == "AN/ASQ-228 ATFLIR"
    assert atflir.weapon_group.introduction_year == 2003

    faction = cast(Faction, SimpleNamespace(weapons_introduction_year_overrides={}))
    aircraft = _fa_18c_hornet()
    loadout = Loadout("Test", {4: atflir}, date=None)

    degraded = loadout.degrade_for_date(aircraft, date(2002, 1, 1), faction)

    degraded_weapon = degraded.pylons.get(4)
    assert degraded_weapon is not None
    assert degraded_weapon.weapon_group.type is not WeaponType.TGP


@pytest.mark.parametrize(
    ("clsid", "group_name", "introduction_year"),
    [
        ("{F-15E_AAQ-33_XR_ATP-SE}", "AN/AAQ-33 - Advanced Targeting Pod", 2005),
        ("{F-15E_AAQ-28_LITENING}", "AN/AAQ-28 LITENING", 1999),
        ("{SUPERHORNET_PYLON_05_TP_ASQ228}", "AN/ASQ-228 ATFLIR", 2003),
        ("{SUPERHORNET_PYLON_06_CN_TP_AAQ28}", "AN/AAQ-28 LITENING", 1999),
        ("_NiteHawk_FLIR", "AN/AAS-38 Nite Hawk", 1984),
        ("{HB_PAVE_SPIKE_FAST_TRACK}", "AN/AVQ-23 Pave Spike", 1974),
        ("{HB_PAVE_SPIKE_FAST_ON_ADAPTER_IN_AERO7}", "AN/AVQ-23 Pave Spike", 1974),
        ("{JAS39_Litening}", "AN/AAQ-28 LITENING", 1999),
        ("{JAS39_FLIR}", "AN/AAQ-28 LITENING", 1999),
        ("{LITENING_POD}", "AN/AAQ-28 LITENING", 1999),
        ("{DAMOCLES}", "DAMOCLES", 2009),
        ("{F111C_FLIR}", "AN/AVQ-26 Pave Tack", 1982),
        ("DIS_WMD7", "AVIC WMD-7", 2007),
        ("Herc_BattleStation_TGP", "Hercules Battle Station with TGP", 2020),
    ],
)
def test_targeting_pod_variants_have_era_data(
    clsid: str, group_name: str, introduction_year: int
) -> None:
    weapon = Weapon.with_clsid(clsid)

    assert weapon is not None
    assert weapon.weapon_group.type is WeaponType.TGP
    assert weapon.weapon_group.name == group_name
    assert weapon.weapon_group.introduction_year == introduction_year


def test_custom_payload_targeting_pods_do_not_fall_back_to_unknown() -> None:
    payload_clsids: set[str] = set()
    for path in Path("resources/customized_payloads").glob("*.lua"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        payload_clsids.update(re.findall(r'\["CLSID"\]\s*=\s*"([^"]+)"', text))

    def is_targeting_pod(weapon: Weapon) -> bool:
        name = weapon.name.upper()
        return "NAV POD" not in name and any(
            marker in name
            for marker in (
                "AAQ",
                "AAS-38",
                "ATFLIR",
                "DAMOCLES",
                "LANTIRN",
                "LITENING",
                "NITE HAWK",
                "AVQ",
                "PAVE SPIKE",
                "PAVE TACK",
                "TGP",
                "WMD",
            )
        )

    targeting_pods = [
        weapon
        for clsid in sorted(payload_clsids)
        if (weapon := Weapon.with_clsid(clsid)) is not None and is_targeting_pod(weapon)
    ]

    assert targeting_pods
    for weapon in targeting_pods:
        assert weapon.weapon_group.type is WeaponType.TGP, weapon.clsid
        assert weapon.weapon_group.introduction_year is not None, (
            weapon.clsid,
            weapon.weapon_group.name,
        )
