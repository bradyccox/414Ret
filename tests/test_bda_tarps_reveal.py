from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from dcs.mapping import Point

from game.ato.flighttype import FlightType
from game.debriefing import AirLosses, Debriefing, GroundLosses
from game.sim.gameupdateevents import GameUpdateEvents
from game.sim.missionresultsprocessor import MissionResultsProcessor
from game.theater import Player
from game.theater.controlpoint import OffMapSpawn
from game.theater.presetlocation import PresetLocation
from game.theater.theatergroundobject import SamGroundObject
from game.utils import Heading, meters


class FakeUnit:
    def __init__(
        self,
        ground_object: SamGroundObject,
        *,
        alive: bool = True,
        alive_at_last_recon: bool = True,
        threat_meters: int = 25_000,
        detection_meters: int = 40_000,
    ) -> None:
        self.ground_object = ground_object
        self.alive = alive
        self.alive_at_last_recon = alive_at_last_recon
        self.threat_meters = threat_meters
        self.detection_meters = detection_meters
        self.is_anti_air = True
        self.is_static = False
        self.icon = "missing"
        self.repairable = False
        self.type = SimpleNamespace(id="fake-sam", name="Fake SAM")

    def kill(self, events: GameUpdateEvents) -> None:
        self.alive = False
        self.ground_object.invalidate_threat_poly()
        events.update_tgo(self.ground_object)

    def sync_confirmed_status(self) -> None:
        self.alive_at_last_recon = self.alive

    def alive_for_player(self, player: Player) -> bool:
        if self.ground_object.is_friendly(player):
            return self.alive
        return self.alive_at_last_recon

    def display_name_for(self, player: Player) -> str:
        suffix = " [DEAD]" if not self.alive_for_player(player) else ""
        return f"0001 | Fake SAM{suffix}"

    def short_name_for(self, player: Player) -> str:
        suffix = " [DEAD]" if not self.alive_for_player(player) else ""
        return f"<b>Fake SAM</b>{suffix}"

    def threat_range_for_player(self, player: Player):
        if not self.alive_for_player(player):
            return meters(0)
        return meters(self.threat_meters)

    def detection_range_for_player(self, player: Player):
        if not self.alive_for_player(player):
            return meters(0)
        return meters(self.detection_meters)


class FakeGroup:
    def __init__(self, ground_object: SamGroundObject, unit: FakeUnit) -> None:
        self.ground_object = ground_object
        self.units = [unit]

    @property
    def unit_count(self) -> int:
        return len(self.units)

    @property
    def alive_units(self) -> int:
        return sum(unit.alive for unit in self.units)

    def alive_units_for_player(self, player: Player) -> int:
        return sum(unit.alive_for_player(player) for unit in self.units)

    def max_threat_range_for_player(self, player: Player):
        return max(
            (unit.threat_range_for_player(player) for unit in self.units), default=meters(0)
        )

    def max_detection_range_for_player(self, player: Player):
        return max(
            (unit.detection_range_for_player(player) for unit in self.units),
            default=meters(0),
        )


def _enemy_sam() -> tuple[SamGroundObject, FakeUnit]:
    location = PresetLocation(
        name="target",
        position=Point(0, 0, None),  # type: ignore[arg-type]
        heading=Heading(0),  # type: ignore[arg-type]
    )
    control_point = OffMapSpawn(
        name="enemy-cp",
        position=Point(0, 0, None),  # type: ignore[arg-type]
        theater=None,  # type: ignore[arg-type]
        starts_blue=Player.RED,
    )
    tgo = SamGroundObject(
        name="Enemy SAM",
        location=location,
        control_point=control_point,
        task=None,
    )
    tgo.is_friendly = lambda player: False  # type: ignore[method-assign]
    unit = FakeUnit(tgo)
    tgo.groups = [FakeGroup(tgo, unit)]  # type: ignore[list-item]
    return tgo, unit


def _processor_with_packages(*packages: Any) -> MissionResultsProcessor:
    game = SimpleNamespace(
        blue=SimpleNamespace(ato=SimpleNamespace(packages=list(packages))),
        red=SimpleNamespace(ato=SimpleNamespace(packages=[])),
    )
    return MissionResultsProcessor(game)  # type: ignore[arg-type]


def _debrief_with_ground_loss(unit: FakeUnit, air_losses: AirLosses | None = None) -> Debriefing:
    debriefing = Debriefing.__new__(Debriefing)
    debriefing.ground_losses = GroundLosses(
        enemy_ground_objects=[
            SimpleNamespace(theater_unit=unit, dcs_unit=MagicMock()),
        ]
    )
    debriefing.air_losses = air_losses or AirLosses(player=[], enemy=[])
    return debriefing


def test_enemy_damage_stays_hidden_without_tarps_recon() -> None:
    tgo, unit = _enemy_sam()
    processor = _processor_with_packages()
    debriefing = _debrief_with_ground_loss(unit)

    processor.commit_ground_losses(debriefing, GameUpdateEvents())

    assert not unit.alive
    assert unit.alive_at_last_recon
    assert tgo.is_dead
    assert not tgo.is_dead_for(Player.BLUE)
    assert tgo.max_threat_range_for(Player.BLUE) > meters(0)


def test_surviving_tarps_reveals_true_enemy_damage() -> None:
    tgo, unit = _enemy_sam()
    tarps_flight = SimpleNamespace(flight_type=FlightType.TARPS, count=1)
    tarps_package = SimpleNamespace(target=tgo, flights=[tarps_flight])
    processor = _processor_with_packages(tarps_package)
    debriefing = _debrief_with_ground_loss(unit, AirLosses(player=[], enemy=[]))

    processor.commit_ground_losses(debriefing, GameUpdateEvents())

    assert not unit.alive
    assert not unit.alive_at_last_recon
    assert tgo.is_dead_for(Player.BLUE)
    assert tgo.max_threat_range_for(Player.BLUE) == meters(0)
