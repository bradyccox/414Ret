"""Unit tests for BARCAP wave scheduling in MissionScheduler.

These exercise the overlapping-wave logic for land control points without
standing up a full Game/Coalition by faking the minimal surface the scheduler
touches and stubbing TotEstimator.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

import game.commander.missionscheduler as ms
from game.ato.flighttype import FlightType

NOW = datetime(2020, 1, 1, 0, 0, 0)
DURATION = timedelta(minutes=60)


class _FakeFlightPlan:
    def __init__(self, patrol_duration: timedelta) -> None:
        self.patrol_duration = patrol_duration
        self.landing_time = NOW + patrol_duration


class _FakeDeparture:
    is_fleet = False


class _FakeFlight:
    def __init__(self, patrol_duration: timedelta) -> None:
        self.flight_plan = _FakeFlightPlan(patrol_duration)
        self.departure = _FakeDeparture()
        self.is_helo = False


class _LandTarget:
    """A non-naval mission target (BARCAP over a land control point)."""


class _FakePackage:
    def __init__(self, target: object, duration: timedelta = DURATION) -> None:
        self.primary_task = FlightType.BARCAP
        self.auto_asap = False
        self.target = target
        self._duration = duration
        self.flights = [_FakeFlight(duration)]
        self.time_over_target: datetime | None = None

    @property
    def mission_departure_time(self) -> datetime:
        assert self.time_over_target is not None
        return self.time_over_target + self._duration


class _FakeSettings:
    def __init__(self, overlap: timedelta) -> None:
        self.barcap_overlap_time = overlap
        self.desired_barcap_mission_duration = DURATION
        self.desired_tanker_on_station_time = timedelta(minutes=60)


class _FakeGame:
    def __init__(self, settings: _FakeSettings) -> None:
        self.settings = settings


class _FakeAto:
    def __init__(self, packages: list[_FakePackage]) -> None:
        self.packages = packages


class _FakeCoalition:
    def __init__(self, packages: list[_FakePackage], settings: _FakeSettings) -> None:
        self.ato = _FakeAto(packages)
        self.game = _FakeGame(settings)


class _StubTotEstimator:
    """earliest_tot is always `now` (CAP launches from the defended base)."""

    def __init__(self, package: _FakePackage) -> None:
        self.package = package

    def earliest_tot(self, now: datetime) -> datetime:
        return now


def _schedule(overlap: timedelta, rounds: int) -> list[datetime]:
    target = _LandTarget()
    packages = [_FakePackage(target) for _ in range(rounds)]
    coalition = _FakeCoalition(packages, _FakeSettings(overlap))
    scheduler = ms.MissionScheduler(coalition, timedelta(minutes=120))
    scheduler.schedule_missions(NOW)
    tots = [p.time_over_target for p in packages]
    assert all(t is not None for t in tots)
    return tots  # type: ignore[return-value]


@pytest.fixture(autouse=True)
def _stub_tot_estimator(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ms, "TotEstimator", _StubTotEstimator)


def test_overlapping_waves_are_spaced_by_duration_minus_overlap() -> None:
    overlap = timedelta(minutes=15)
    tots = _schedule(overlap, rounds=3)

    interval = DURATION - overlap  # 45 minutes of fresh coverage per wave
    assert tots[1] - tots[0] == interval
    assert tots[2] - tots[1] == interval


def test_first_wave_is_jittered_but_bounded() -> None:
    overlap = timedelta(minutes=15)
    # Run several times; the first wave should always land within the jitter
    # ceiling (min(overlap, 5 min)) after the earliest possible TOT (== NOW).
    ceiling = min(overlap, timedelta(minutes=5))
    for _ in range(50):
        first = _schedule(overlap, rounds=1)[0]
        assert NOW <= first <= NOW + ceiling


def test_zero_overlap_reproduces_legacy_back_to_back_schedule() -> None:
    tots = _schedule(timedelta(0), rounds=3)
    # No jitter, and waves chained exactly end-to-end (spacing == duration).
    assert tots[0] == NOW
    assert tots[1] - tots[0] == DURATION
    assert tots[2] - tots[1] == DURATION
