"""Tests for the F-14 TARPS photo-recon flight type and its target gate.

TARPS is a recon/BDA overflight auto-paired with Strike/DEAD packages. These
tests lock in the two design-critical pieces that are cheap to verify without a
full game fixture: the +5 min post-strike TOT offset, and the ``warrants_recon``
target gate that decides which targets get a TARPS pass.
"""

from datetime import timedelta
from typing import Any
from unittest.mock import MagicMock

import pytest
from dcs.mapping import Point

from game.ato.flighttype import FlightType
from game.ato.package import Package
from game.ato.flightplans.tarps import TarpsFlightPlan
from game.dcs.aircrafttype import AircraftType
from game import persistency
from game.theater.controlpoint import OffMapSpawn, Player
from game.theater.presetlocation import PresetLocation
from game.theater.theatergroundobject import (
    BuildingGroundObject,
    EwrGroundObject,
    SamGroundObject,
    TheaterGroundObject,
)
from game.utils import Heading


def test_tarps_flight_type_is_recon_support() -> None:
    # TARPS is a non-combat recon role: neither air-to-air nor air-to-ground.
    assert not FlightType.TARPS.is_air_to_air
    assert not FlightType.TARPS.is_air_to_ground
    assert FlightType.TARPS.entity_type.name == "RECONNAISSANCE"


def test_tarps_tot_offset_is_post_strike() -> None:
    # The whole point of the feature: overfly the target 5 minutes behind the
    # strikers for a post-strike BDA pass.
    plan = object.__new__(TarpsFlightPlan)
    assert plan.default_tot_offset() == timedelta(minutes=5)


def test_tarps_only_package_identifies_tarps_as_primary_task() -> None:
    package = Package(target=MagicMock(), db=MagicMock())
    package.flights.append(MagicMock(flight_type=FlightType.TARPS))
    assert package.primary_task is FlightType.TARPS


@pytest.mark.parametrize(
    "variant_id",
    [
        "F-14A Tomcat (AI)",
        "F-14A Tomcat (Block 135-GR Late)",
        "F-14A Tomcat (Block 135-GR Early)",
        "F-14B Tomcat",
    ],
)
def test_all_tomcat_variants_can_plan_tarps(
    variant_id: str, tmp_path
) -> None:
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16880)
    assert AircraftType.named(variant_id).capable_of(FlightType.TARPS)


@pytest.fixture
def enemy_objects(monkeypatch: pytest.MonkeyPatch) -> Any:
    location = PresetLocation(
        name="loc", position=Point(0, 0, None), heading=Heading(0)  # type: ignore
    )
    control_point = OffMapSpawn(
        name="cp",
        position=Point(0, 0, None),  # type: ignore
        theater=None,  # type: ignore
        starts_blue=Player.BLUE,
    )
    # Treat every target as enemy so mission_types yields the offensive set.
    # (The TGO's own is_friendly is what mission_types calls; patching it here
    # avoids needing a fully-initialized ControlPoint/coalition.)
    monkeypatch.setattr(TheaterGroundObject, "is_friendly", lambda self, player: False)
    return location, control_point


def _building(location: Any, control_point: Any, category: str) -> BuildingGroundObject:
    return BuildingGroundObject(
        name="test",
        category=category,
        location=location,
        control_point=control_point,
        task=None,
    )


def test_air_defenses_warrant_recon(enemy_objects: Any) -> None:
    location, control_point = enemy_objects

    sam = SamGroundObject(
        name="sam", location=location, control_point=control_point, task=None
    )
    assert sam.warrants_recon
    assert FlightType.TARPS in list(sam.mission_types(for_player=Player.RED))

    ewr = EwrGroundObject(name="ewr", location=location, control_point=control_point)
    assert ewr.warrants_recon
    assert FlightType.TARPS in list(ewr.mission_types(for_player=Player.RED))


@pytest.mark.parametrize("category", ["factory", "commandcenter"])
def test_strategic_buildings_warrant_recon(enemy_objects: Any, category: str) -> None:
    location, control_point = enemy_objects
    building = _building(location, control_point, category)
    assert building.warrants_recon
    assert FlightType.TARPS in list(building.mission_types(for_player=Player.RED))


@pytest.mark.parametrize("category", ["ammo", "fuel", "ware", "power"])
def test_mundane_buildings_do_not_warrant_recon(
    enemy_objects: Any, category: str
) -> None:
    location, control_point = enemy_objects
    building = _building(location, control_point, category)
    # No strategic category and no scenery units -> not worth a recon pass.
    assert not building.warrants_recon
    assert FlightType.TARPS not in list(building.mission_types(for_player=Player.RED))
