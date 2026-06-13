import logging
from abc import ABC

from dcs import Point

from game.ato.flightstate import FlightState


class AtDeparture(FlightState, ABC):
    # Phase rank of this pre-flight state, aligned with
    # FastForwardStopCondition.player_preflight_phase (StartUp=0, Taxi=1, Takeoff=2).
    stop_phase: int

    @property
    def cancelable(self) -> bool:
        return True

    def estimate_position(self) -> Point:
        return self.flight.departure.position

    def should_halt_sim(self) -> bool:
        # Halt at the earliest pre-flight state whose phase is at or after the
        # configured stop condition. A flight enters at its start type's phase
        # (COLD->StartUp, WARM->Taxi, RUNWAY->Takeoff), so e.g. a WARM flight halts
        # here at Taxi even under PLAYER_STARTUP instead of fast-forwarding into the
        # air and spawning the player airborne.
        condition_phase = (
            self.settings.fast_forward_stop_condition.player_preflight_phase
        )
        if (
            self.flight.client_count > 0
            and condition_phase is not None
            and self.stop_phase >= condition_phase
        ):
            logging.info(
                f"Interrupting simulation because {self.flight} has players and "
                f"reached {self.description.lower()} (spawn type "
                f"{self.spawn_type.value})"
            )
            return True
        return False
