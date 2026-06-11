from __future__ import annotations

import logging
import random
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Iterator, TYPE_CHECKING

from game.ato.flighttype import FlightType
from game.ato.traveltime import TotEstimator
from game.theater import MissionTarget, NavalControlPoint

if TYPE_CHECKING:
    from game.coalition import Coalition
    from game.ato import Package


class MissionScheduler:
    def __init__(self, coalition: Coalition, desired_mission_length: timedelta) -> None:
        self.coalition = coalition
        self.desired_mission_length = desired_mission_length

    def schedule_missions(self, now: datetime) -> None:
        """Identifies and plans mission for the turn."""

        def start_time_generator(
            count: int, earliest: int, latest: int, margin: int
        ) -> Iterator[timedelta]:
            interval = (latest - earliest) // count
            for time in range(earliest, latest, interval):
                error = random.randint(-margin, margin)
                yield timedelta(seconds=max(0, time + error))

        def cap_patrol_duration(package: Package) -> timedelta:
            """On-station duration of a CAP package's patrol flight plan."""
            for flight in package.flights:
                duration = getattr(flight.flight_plan, "patrol_duration", None)
                if duration is not None:
                    return duration
            return self.coalition.game.settings.desired_barcap_mission_duration

        dca_types = {
            FlightType.BARCAP,
            FlightType.TARCAP,
            FlightType.SCRAMBLE,
        }

        previous_cap_end_time: dict[MissionTarget, datetime] = defaultdict(now.replace)
        previous_cap_start_time: dict[MissionTarget, datetime] = {}
        barcap_overlap = self.coalition.game.settings.barcap_overlap_time
        non_dca_packages = [
            p for p in self.coalition.ato.packages if p.primary_task not in dca_types
        ]

        previous_aewc_end_time: dict[MissionTarget, datetime] = defaultdict(now.replace)

        max_simultaneous_recovery_tankers = 2  # TODO: make configurable
        carrier_etas: dict[MissionTarget, list[datetime]] = defaultdict(list)
        max_carrier_simultaneous_barcaps = 2  # TODO: make configurable
        carrier_barcaps: dict[MissionTarget, int] = defaultdict(int)

        start_time = start_time_generator(
            count=len(non_dca_packages),
            earliest=5 * 60,
            latest=int(self.desired_mission_length.total_seconds()),
            margin=5 * 60,
        )
        for package in self.coalition.ato.packages:
            if package.primary_task is FlightType.RECOVERY:
                continue
            tot = TotEstimator(package).earliest_tot(now)
            if package.auto_asap:
                package.set_tot_asap(now)
            elif package.primary_task in dca_types:
                if isinstance(package.target, NavalControlPoint):
                    # Carriers stack several simultaneous BARCAPs rather than
                    # overlapping waves; keep the legacy queueing for them.
                    previous_end_time = previous_cap_end_time[package.target]
                    if tot > previous_end_time:
                        # Can't get there exactly on time, so get there ASAP.
                        package.time_over_target = tot
                    else:
                        package.time_over_target = previous_end_time
                    departure_time = self._get_departure_time(package)
                    if departure_time is None:
                        continue
                    count = carrier_barcaps[package.target]
                    if count >= max_carrier_simultaneous_barcaps - 1:
                        previous_cap_end_time[package.target] = departure_time
                        carrier_barcaps[package.target] = 0
                    else:
                        carrier_barcaps[package.target] += 1
                else:
                    # Land CPs: schedule overlapping waves so coverage has no
                    # handoff gap, and jitter the first wave so CAP no longer
                    # deterministically arrives at mission start (which let
                    # attackers wait out the front-loaded CAP and strike a clear
                    # sky). With barcap_overlap_time == 0 this reproduces the
                    # legacy back-to-back, no-jitter schedule exactly.
                    previous_start = previous_cap_start_time.get(package.target)
                    if previous_start is None:
                        jitter_ceiling = int(
                            min(
                                barcap_overlap, timedelta(minutes=5)
                            ).total_seconds()
                        )
                        jitter = timedelta(
                            seconds=random.randint(0, jitter_ceiling)
                        )
                        package.time_over_target = tot + jitter
                    else:
                        interval = cap_patrol_duration(package) - barcap_overlap
                        if interval < timedelta(minutes=1):
                            interval = timedelta(minutes=1)
                        desired = previous_start + interval
                        # Can't arrive before the flight can physically get there.
                        package.time_over_target = max(tot, desired)
                    previous_cap_start_time[package.target] = package.time_over_target
            elif package.primary_task is FlightType.AEWC:
                last = previous_aewc_end_time[package.target]
                package.time_over_target = tot if tot > last else last
                departure_time = self._get_departure_time(package)
                if departure_time is None:
                    continue
                previous_aewc_end_time[package.target] = departure_time
            else:
                # But other packages should be spread out a bit. Note that take
                # times are delayed, but all aircraft will become active at
                # mission start. This makes it more worthwhile to attack enemy
                # airfields to hit grounded aircraft, since they're more likely
                # to be present. Runway and air started aircraft will be
                # delayed until their takeoff time by AirConflictGenerator.
                package.time_over_target = next(start_time) + tot
            for f in package.flights:
                if f.departure.is_fleet and not f.is_helo:
                    carrier_etas[f.departure].append(
                        f.flight_plan.landing_time - timedelta(minutes=10)
                    )

        # division by 2 is meant to provide some leeway to avoid filtering out too many ETAs
        duration = self.coalition.game.settings.desired_tanker_on_station_time / 2

        for cp in carrier_etas:
            filtered: list[datetime] = []
            for eta in sorted(carrier_etas[cp]):
                count = len([t for t in filtered if eta < t + duration])
                if count < max_simultaneous_recovery_tankers:
                    filtered.append(eta)
            carrier_etas[cp] = filtered
        for package in [
            p
            for p in self.coalition.ato.packages
            if p.primary_task is FlightType.RECOVERY
        ]:
            if carrier_etas[package.target]:
                package.time_over_target = carrier_etas[package.target].pop(0)

    @staticmethod
    def _get_departure_time(package: Package) -> datetime | None:
        departure_time = package.mission_departure_time
        # Should be impossible for CAP/AEWC
        if departure_time is None:
            logging.error(f"Could not determine mission end time for {package}")
        return departure_time
