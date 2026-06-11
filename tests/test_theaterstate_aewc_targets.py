from __future__ import annotations

from dataclasses import dataclass

from game.ato import FlightType
from game.commander.theaterstate import TheaterState


@dataclass
class _FakeAircraft:
    can_aewec: bool = True

    def capable_of(self, task: FlightType) -> bool:
        return self.can_aewec and task is FlightType.AEWC


@dataclass
class _FakeSquadron:
    aircraft: _FakeAircraft
    untasked_aircraft: int


@dataclass
class _FakeCP:
    name: str
    position: str
    squadrons: list[_FakeSquadron]


class _FakeThreatZones:
    def __init__(self, distances: dict[str, float]) -> None:
        self.distances = distances

    def distance_to_threat(self, position: str) -> float:
        return self.distances[position]


class _FakeFinder:
    def __init__(self, cps: list[_FakeCP], fallback: _FakeCP) -> None:
        self._cps = cps
        self._fallback = fallback

    def friendly_control_points(self) -> list[_FakeCP]:
        return self._cps

    def farthest_friendly_control_point(self) -> _FakeCP:
        return self._fallback


class _FakePlayer:
    def __init__(self, is_blue: bool) -> None:
        self.is_blue = is_blue


def test_aewc_targets_choose_the_closest_supported_base_first() -> None:
    carrier = _FakeCP(
        "carrier",
        "carrier_pos",
        [_FakeSquadron(_FakeAircraft(), 1), _FakeSquadron(_FakeAircraft(), 1)],
    )
    e3 = _FakeCP("e3", "e3_pos", [_FakeSquadron(_FakeAircraft(), 1)])
    finder = _FakeFinder([carrier, e3], fallback=carrier)
    threat_zones = _FakeThreatZones({"carrier_pos": 100.0, "e3_pos": 10.0})

    targets = TheaterState._aewc_targets_for(finder, threat_zones, _FakePlayer(True))

    assert [target.name for target in targets] == ["e3", "carrier", "carrier"]


def test_aewc_targets_reverse_for_red() -> None:
    carrier = _FakeCP(
        "carrier",
        "carrier_pos",
        [_FakeSquadron(_FakeAircraft(), 1)],
    )
    e3 = _FakeCP("e3", "e3_pos", [_FakeSquadron(_FakeAircraft(), 1)])
    finder = _FakeFinder([carrier, e3], fallback=carrier)
    threat_zones = _FakeThreatZones({"carrier_pos": 100.0, "e3_pos": 10.0})

    targets = TheaterState._aewc_targets_for(finder, threat_zones, _FakePlayer(False))

    assert [target.name for target in targets] == ["carrier", "e3"]
