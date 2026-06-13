"""Player flights must halt the fast-forward sim at the pre-flight state matching
their start type, so the generated mission spawns them where they chose.

Regression: a WARM (hot-ramp) player flight under the default PLAYER_STARTUP stop
condition used to fast-forward through Taxi/Takeoff into the air, because Taxi only
halted on PLAYER_TAXI. By the time the InFlight halt fired, the flight's spawn_type
was already IN_FLIGHT and the player spawned airborne instead of parked-hot.

The fix ranks the pre-flight phases (StartUp=0, Taxi=1, Takeoff=2) and halts at the
earliest state whose phase is at or after the configured stop condition.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from game.ato.flightstate.atdeparture import AtDeparture
from game.ato.flightstate.inflight import InFlight
from game.ato.starttype import StartType
from game.settings.settings import FastForwardStopCondition


def _depart_halts(stop_phase: int, condition: FastForwardStopCondition) -> bool:
    """Run AtDeparture.should_halt_sim against a minimal fake pre-flight state."""
    fake = SimpleNamespace(
        stop_phase=stop_phase,
        flight=SimpleNamespace(client_count=1, __str__=lambda self: "fake"),
        settings=SimpleNamespace(fast_forward_stop_condition=condition),
        description="Taxiing",
        spawn_type=StartType.WARM,
    )
    return AtDeparture.should_halt_sim(cast(AtDeparture, fake))


def _inflight_halts(start_type: StartType, condition: FastForwardStopCondition) -> bool:
    fake = SimpleNamespace(
        flight=SimpleNamespace(client_count=1, start_type=start_type),
        settings=SimpleNamespace(fast_forward_stop_condition=condition),
    )
    return InFlight.should_halt_sim(cast(InFlight, fake))


# --- phase ordering on the enum -------------------------------------------------


def test_player_preflight_phase_ordering() -> None:
    assert FastForwardStopCondition.PLAYER_STARTUP.player_preflight_phase == 0
    assert FastForwardStopCondition.PLAYER_TAXI.player_preflight_phase == 1
    assert FastForwardStopCondition.PLAYER_TAKEOFF.player_preflight_phase == 2


def test_non_preflight_conditions_have_no_phase() -> None:
    assert FastForwardStopCondition.FIRST_CONTACT.player_preflight_phase is None
    assert FastForwardStopCondition.DISABLED.player_preflight_phase is None
    assert FastForwardStopCondition.MANUAL.player_preflight_phase is None


# --- the regression: WARM (Taxi, phase 1) under PLAYER_STARTUP ------------------


def test_warm_taxi_halts_under_startup_condition() -> None:
    # Taxi (phase 1) >= STARTUP (phase 0): halt here so the player spawns hot on
    # the ramp instead of being fast-forwarded into the air.
    assert _depart_halts(1, FastForwardStopCondition.PLAYER_STARTUP)


def test_runway_takeoff_halts_under_startup_condition() -> None:
    assert _depart_halts(2, FastForwardStopCondition.PLAYER_STARTUP)


def test_cold_startup_halts_under_startup_condition() -> None:
    assert _depart_halts(0, FastForwardStopCondition.PLAYER_STARTUP)


def test_startup_does_not_halt_under_takeoff_condition() -> None:
    # StartUp (phase 0) < TAKEOFF (phase 2): keep fast-forwarding until Takeoff.
    assert not _depart_halts(0, FastForwardStopCondition.PLAYER_TAKEOFF)


def test_taxi_does_not_halt_under_takeoff_condition() -> None:
    assert not _depart_halts(1, FastForwardStopCondition.PLAYER_TAKEOFF)


def test_preflight_does_not_halt_under_first_contact() -> None:
    assert not _depart_halts(0, FastForwardStopCondition.FIRST_CONTACT)
    assert not _depart_halts(1, FastForwardStopCondition.FIRST_CONTACT)
    assert not _depart_halts(2, FastForwardStopCondition.FIRST_CONTACT)


# --- InFlight only halts genuine air starts ------------------------------------


def test_inflight_halts_only_genuine_air_start() -> None:
    assert _inflight_halts(StartType.IN_FLIGHT, FastForwardStopCondition.PLAYER_STARTUP)


def test_inflight_does_not_halt_ground_start_that_reached_flight() -> None:
    # A WARM/COLD/RUNWAY flight should never reach InFlight before halting, but if
    # it somehow does the guard prevents the old "spawned airborne" behavior.
    assert not _inflight_halts(StartType.WARM, FastForwardStopCondition.PLAYER_STARTUP)
    assert not _inflight_halts(StartType.COLD, FastForwardStopCondition.PLAYER_STARTUP)


def test_inflight_does_not_halt_under_first_contact() -> None:
    assert not _inflight_halts(
        StartType.IN_FLIGHT, FastForwardStopCondition.FIRST_CONTACT
    )
