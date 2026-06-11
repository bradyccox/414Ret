"""Tests for Squadron.scramble_reserve — the QRA aircraft the auto-planner holds back.

Without this the planner commits every air-to-air airframe, leaving no untasked
aircraft for the reactive-scramble interceptor pool.
"""
from __future__ import annotations

from game.ato import FlightType
from game.settings import Settings
from game.squadrons.squadron import Squadron


class _Settings:
    def __init__(self, enabled: bool, reserve: int) -> None:
        self.enable_reactive_scramble = enabled
        self.reactive_scramble_reserve = reserve


class _Player:
    def __init__(self, is_red: bool) -> None:
        self.is_red = is_red


class _Coalition:
    def __init__(self, is_red: bool) -> None:
        self.player = _Player(is_red)


class _Aircraft:
    def __init__(self, caps: set[FlightType]) -> None:
        self._caps = caps

    def capable_of(self, task: FlightType) -> bool:
        return task in self._caps


class _Squadron:
    def __init__(self, is_red, caps, enabled=True, reserve=2) -> None:
        self.coalition = _Coalition(is_red)
        self.aircraft = _Aircraft(caps)
        self.settings = _Settings(enabled, reserve)


def reserve_of(**kwargs) -> int:
    # Evaluate the real property against a minimal stand-in.
    return Squadron.scramble_reserve.fget(_Squadron(**kwargs))  # type: ignore[attr-defined]


def test_red_scramble_capable_squadron_reserves() -> None:
    assert reserve_of(is_red=True, caps={FlightType.SCRAMBLE}, reserve=2) == 2
    assert (
        reserve_of(
            is_red=True,
            caps={FlightType.BARCAP, FlightType.SWEEP, FlightType.SCRAMBLE},
            reserve=3,
        )
        == 3
    )


def test_red_air_to_air_without_scramble_does_not_reserve() -> None:
    assert reserve_of(is_red=True, caps={FlightType.BARCAP, FlightType.SWEEP}) == 0


def test_blue_squadron_does_not_reserve() -> None:
    assert reserve_of(is_red=False, caps={FlightType.BARCAP}, reserve=2) == 0


def test_red_ground_attack_only_does_not_reserve() -> None:
    assert reserve_of(is_red=True, caps={FlightType.CAS, FlightType.STRIKE}) == 0


def test_disabled_setting_disables_reserve() -> None:
    assert reserve_of(is_red=True, caps={FlightType.SCRAMBLE}, enabled=False) == 0


def test_reactive_scramble_is_enabled_by_default() -> None:
    settings = Settings()

    assert settings.enable_reactive_scramble
    assert settings.reactive_scramble_reserve == 2
