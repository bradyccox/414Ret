import pytest
from dcs.mapping import Point

from game.ato.flighttype import FlightType
from game.theater.controlpoint import OffMapSpawn, Player
from game.theater.presetlocation import PresetLocation
from game.theater.theatergroundobject import (
    BuildingGroundObject,
    CarrierGroundObject,
    LhaGroundObject,
    MissileSiteGroundObject,
    CoastalSiteGroundObject,
    SamGroundObject,
    VehicleGroupGroundObject,
    EwrGroundObject,
    ShipGroundObject,
    IadsBuildingGroundObject,
    TheaterGroundObject,
)
from game.utils import Heading


def test_mission_types_friendly(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test the mission types that can be planned against friendly Theater Ground Objects
    """
    # Set up dummy inputs
    dummy_location = PresetLocation(
        name="dummy_location", position=Point(0, 0, None), heading=Heading(0)  # type: ignore
    )
    dummy_control_point = OffMapSpawn(
        name="dummy_control_point",
        position=Point(0, 0, None),  # type: ignore
        theater=None,  # type: ignore
        starts_blue=Player.BLUE,
    )

    # Patch is_friendly as it's difficult to set up a proper ControlPoint.
    # mission_types calls self.is_friendly on the TGO, so patch it there.
    monkeypatch.setattr(TheaterGroundObject, "is_friendly", lambda self, player: True)

    # These constructors no longer take a `task` argument (Carrier/LHA/Ship and
    # the missile/coastal/EWR sites hard-code their own GroupTask); SAM and the
    # vehicle group still do. Build each with its real signature.
    ground_objects = [
        CarrierGroundObject(
            name="test", location=dummy_location, control_point=dummy_control_point
        ),
        LhaGroundObject(
            name="test", location=dummy_location, control_point=dummy_control_point
        ),
        MissileSiteGroundObject(
            name="test", location=dummy_location, control_point=dummy_control_point
        ),
        CoastalSiteGroundObject(
            name="test", location=dummy_location, control_point=dummy_control_point
        ),
        SamGroundObject(
            name="test",
            location=dummy_location,
            control_point=dummy_control_point,
            task=None,
        ),
        VehicleGroupGroundObject(
            name="test",
            location=dummy_location,
            control_point=dummy_control_point,
            task=None,
        ),
        EwrGroundObject(
            name="test", location=dummy_location, control_point=dummy_control_point
        ),
        ShipGroundObject(
            name="test", location=dummy_location, control_point=dummy_control_point
        ),
    ]
    for ground_object in ground_objects:
        mission_types = list(ground_object.mission_types(for_player=Player.BLUE))
        assert mission_types == [FlightType.BARCAP]

    for ground_object_type in [BuildingGroundObject, IadsBuildingGroundObject]:
        ground_object = ground_object_type(
            name="test",
            category="ammo",
            location=dummy_location,
            control_point=dummy_control_point,
            task=None,
        )
        mission_types = list(ground_object.mission_types(for_player=Player.BLUE))
        assert mission_types == [FlightType.BARCAP]


def test_mission_types_enemy(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test the mission types that can be planned against enemy Theater Ground Objects
    """
    # Set up dummy inputs
    dummy_location = PresetLocation(
        name="dummy_location", position=Point(0, 0, None), heading=Heading(0)  # type: ignore
    )
    dummy_control_point = OffMapSpawn(
        name="dummy_control_point",
        position=Point(0, 0, None),  # type: ignore
        theater=None,  # type: ignore
        starts_blue=Player.BLUE,
    )

    # Patch is_friendly as it's difficult to set up a proper ControlPoint.
    # mission_types calls self.is_friendly on the TGO, so patch it there.
    monkeypatch.setattr(TheaterGroundObject, "is_friendly", lambda self, player: False)

    # Strategic-recon gate: air defenses (SAM/EWR/IADS) get a TARPS BDA pass;
    # mundane targets (ammo dumps, armor, ships, missile/coastal sites) do not.
    building = BuildingGroundObject(
        name="test",
        category="ammo",
        location=dummy_location,
        control_point=dummy_control_point,
        task=None,
    )
    mission_types = list(building.mission_types(for_player=Player.RED))
    assert len(mission_types) == 9
    assert FlightType.STRIKE in mission_types
    assert FlightType.REFUELING in mission_types
    assert FlightType.ESCORT in mission_types
    assert FlightType.TARCAP in mission_types
    assert FlightType.SEAD_ESCORT in mission_types
    assert FlightType.SEAD_SWEEP in mission_types
    assert FlightType.ARMED_RECON in mission_types
    assert FlightType.SWEEP in mission_types
    assert FlightType.JAMMING in mission_types
    assert FlightType.TARPS not in mission_types  # ammo does not warrant recon

    iads_building = IadsBuildingGroundObject(
        name="test",
        category="ammo",
        location=dummy_location,
        control_point=dummy_control_point,
        task=None,
    )
    mission_types = list(iads_building.mission_types(for_player=Player.RED))
    assert len(mission_types) == 10
    assert FlightType.STRIKE in mission_types
    assert FlightType.DEAD in mission_types
    assert FlightType.REFUELING in mission_types
    assert FlightType.ESCORT in mission_types
    assert FlightType.TARCAP in mission_types
    assert FlightType.SEAD_ESCORT in mission_types
    assert FlightType.SEAD_SWEEP in mission_types
    assert FlightType.ARMED_RECON in mission_types
    assert FlightType.SWEEP in mission_types
    assert FlightType.JAMMING in mission_types
    assert FlightType.TARPS not in mission_types  # ammo does not warrant recon

    ground_object: TheaterGroundObject
    naval_objects = [
        CarrierGroundObject(
            name="test", location=dummy_location, control_point=dummy_control_point
        ),
        LhaGroundObject(
            name="test", location=dummy_location, control_point=dummy_control_point
        ),
        ShipGroundObject(
            name="test", location=dummy_location, control_point=dummy_control_point
        ),
    ]
    for ground_object in naval_objects:
        mission_types = list(ground_object.mission_types(for_player=Player.RED))
        assert len(mission_types) == 11
        assert FlightType.ANTISHIP in mission_types
        assert FlightType.SEAD in mission_types
        assert FlightType.STRIKE in mission_types
        assert FlightType.REFUELING in mission_types
        assert FlightType.ESCORT in mission_types
        assert FlightType.TARCAP in mission_types
        assert FlightType.SEAD_ESCORT in mission_types
        assert FlightType.SEAD_SWEEP in mission_types
        assert FlightType.ARMED_RECON in mission_types
        assert FlightType.SWEEP in mission_types
        assert FlightType.JAMMING in mission_types
        assert FlightType.TARPS not in mission_types

    sam = SamGroundObject(
        name="test",
        location=dummy_location,
        control_point=dummy_control_point,
        task=None,
    )
    mission_types = list(sam.mission_types(for_player=Player.RED))
    assert len(mission_types) == 12
    assert FlightType.DEAD in mission_types
    assert FlightType.SEAD in mission_types
    assert FlightType.STRIKE in mission_types
    assert FlightType.REFUELING in mission_types
    assert FlightType.TARPS in mission_types  # +TARPS: air defenses warrant recon
    assert FlightType.ESCORT in mission_types
    assert FlightType.TARCAP in mission_types
    assert FlightType.SEAD_ESCORT in mission_types
    assert FlightType.SEAD_SWEEP in mission_types
    assert FlightType.ARMED_RECON in mission_types
    assert FlightType.SWEEP in mission_types
    assert FlightType.JAMMING in mission_types

    ewr = EwrGroundObject(
        name="test",
        location=dummy_location,
        control_point=dummy_control_point,
    )
    mission_types = list(ewr.mission_types(for_player=Player.RED))
    assert len(mission_types) == 11
    assert FlightType.DEAD in mission_types
    assert FlightType.STRIKE in mission_types
    assert FlightType.REFUELING in mission_types
    assert FlightType.TARPS in mission_types  # +TARPS: air defenses warrant recon
    assert FlightType.ESCORT in mission_types
    assert FlightType.TARCAP in mission_types
    assert FlightType.SEAD_ESCORT in mission_types
    assert FlightType.SEAD_SWEEP in mission_types
    assert FlightType.ARMED_RECON in mission_types
    assert FlightType.SWEEP in mission_types
    assert FlightType.JAMMING in mission_types

    site_objects = [
        CoastalSiteGroundObject(
            name="test", location=dummy_location, control_point=dummy_control_point
        ),
        MissileSiteGroundObject(
            name="test", location=dummy_location, control_point=dummy_control_point
        ),
    ]
    for ground_object in site_objects:
        mission_types = list(ground_object.mission_types(for_player=Player.RED))
        assert len(mission_types) == 10
        assert FlightType.BAI in mission_types
        assert FlightType.STRIKE in mission_types
        assert FlightType.REFUELING in mission_types
        assert FlightType.ESCORT in mission_types
        assert FlightType.TARCAP in mission_types
        assert FlightType.SEAD_ESCORT in mission_types
        assert FlightType.SEAD_SWEEP in mission_types
        assert FlightType.ARMED_RECON in mission_types
        assert FlightType.SWEEP in mission_types
        assert FlightType.JAMMING in mission_types
        assert FlightType.TARPS not in mission_types

    vehicles = VehicleGroupGroundObject(
        name="test",
        location=dummy_location,
        control_point=dummy_control_point,
        task=None,
    )
    mission_types = list(vehicles.mission_types(for_player=Player.RED))
    assert len(mission_types) == 10
    assert FlightType.BAI in mission_types
    assert FlightType.STRIKE in mission_types
    assert FlightType.REFUELING in mission_types
    assert FlightType.ESCORT in mission_types
    assert FlightType.TARCAP in mission_types
    assert FlightType.SEAD_ESCORT in mission_types
    assert FlightType.SEAD_SWEEP in mission_types
    assert FlightType.ARMED_RECON in mission_types
    assert FlightType.SWEEP in mission_types
    assert FlightType.JAMMING in mission_types
    assert FlightType.TARPS not in mission_types
