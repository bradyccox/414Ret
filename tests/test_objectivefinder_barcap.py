"""Tests for the forward defensive CAP line in ObjectiveFinder.

`vulnerable_control_points()` now defends a friendly CP if it anchors an active
front line, in addition to the legacy "enemy airfield within threat range" rule.
"""
from __future__ import annotations

import pytest

import game.commander.objectivefinder as obf
from game.commander.objectivefinder import ObjectiveFinder


class _FakePlayer:
    def __init__(self, is_red: bool) -> None:
        self.is_red = is_red


class _FakeCP:
    def __init__(self, name: str, has_active_frontline: bool) -> None:
        self.name = name
        self.has_active_frontline = has_active_frontline

    def is_friendly(self, player: object) -> bool:
        return True

    def __repr__(self) -> str:
        return f"_FakeCP({self.name})"


class _FakeTheater:
    def __init__(self, control_points: list[_FakeCP]) -> None:
        self.controlpoints = control_points


class _FakeSettings:
    airbase_threat_range = 30
    opfor_autoplanner_aggressiveness = 50


class _FakeGame:
    def __init__(self, control_points: list[_FakeCP]) -> None:
        self.theater = _FakeTheater(control_points)
        self.settings = _FakeSettings()


class _NoAirfields:
    operational_airfields: list[object] = []

    def operational_airfields_within(self, _distance: object) -> list[object]:
        return []


@pytest.fixture(autouse=True)
def _no_airfield_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    # The front-line path returns before this is reached; the other paths must
    # not hit the real distance cache with fake control points.
    monkeypatch.setattr(
        ObjectiveFinder,
        "closest_airfields_to",
        staticmethod(lambda _location: _NoAirfields()),
    )


def _finder(control_points: list[_FakeCP], is_red: bool) -> ObjectiveFinder:
    return ObjectiveFinder(_FakeGame(control_points), _FakePlayer(is_red))  # type: ignore[arg-type]


def test_front_line_cp_is_defended() -> None:
    cp = _FakeCP("front", has_active_frontline=True)
    finder = _finder([cp], is_red=False)
    assert cp in list(finder.vulnerable_control_points())


def test_rear_cp_without_nearby_enemy_airfield_is_not_defended() -> None:
    cp = _FakeCP("rear", has_active_frontline=False)
    finder = _finder([cp], is_red=False)
    assert cp not in list(finder.vulnerable_control_points())


def test_opfor_offensive_roll_skips_front_line(monkeypatch: pytest.MonkeyPatch) -> None:
    # aggressiveness is the ratio of threat ignored: plan_offensively when
    # randint <= aggressiveness. Force a low roll so OPFOR plans offensively;
    # the forward CAP line should be skipped on that roll.
    monkeypatch.setattr(obf, "randint", lambda _a, _b: 1)
    cp = _FakeCP("front", has_active_frontline=True)
    finder = _finder([cp], is_red=True)
    assert cp not in list(finder.vulnerable_control_points())
