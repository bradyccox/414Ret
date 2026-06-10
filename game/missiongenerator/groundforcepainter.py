from __future__ import annotations

import logging
import random
from typing import Any, Optional

from dcs.unit import Ship
from dcs.unitgroup import Vehicle

from game.factions.faction import Faction


class GroundForcePainter:
    _missing_livery_warnings: set[tuple[str, Any]] = set()

    def __init__(self, faction: Faction, vehicle: Vehicle) -> None:
        self.faction = faction
        self.vehicle = vehicle

    def log_missing_livery_once(self) -> None:
        key = (self.faction.name, self.vehicle.type)
        if key in self._missing_livery_warnings:
            return
        self._missing_livery_warnings.add(key)
        logging.warning(
            f"Faction {self.faction.name} is missing livery for ground unit {self.vehicle.type}"
        )

    def livery_from_faction(self) -> Optional[str]:
        faction = self.faction
        try:
            if (
                choices := faction.liveries_overrides_ground_forces.get(
                    self.vehicle.type
                )
            ) is not None:
                return random.choice(choices)
        except AttributeError:
            self.log_missing_livery_once()
            return None
        self.log_missing_livery_once()
        return None

    def determine_livery(self) -> Optional[str]:
        if (livery := self.livery_from_faction()) is not None:
            return livery
        return None

    def apply_livery(self) -> None:
        livery = self.determine_livery()
        if livery is None:
            return
        self.vehicle.livery_id = livery


class NavalForcePainter:
    _missing_livery_warnings: set[tuple[str, Any]] = set()

    def __init__(self, faction: Faction, vessel: Ship) -> None:
        self.faction = faction
        self.vessel = vessel

    def log_missing_livery_once(self) -> None:
        key = (self.faction.name, self.vessel.type)
        if key in self._missing_livery_warnings:
            return
        self._missing_livery_warnings.add(key)
        logging.warning(
            f"Faction {self.faction.name} is missing livery for naval unit {self.vessel.type}"
        )

    def livery_from_faction(self) -> Optional[str]:
        faction = self.faction
        try:
            if (
                choices := faction.liveries_overrides_ground_forces.get(
                    self.vessel.type
                )
            ) is not None:
                return random.choice(choices)
        except AttributeError:
            self.log_missing_livery_once()
            return None
        self.log_missing_livery_once()
        return None

    def determine_livery(self) -> Optional[str]:
        if (livery := self.livery_from_faction()) is not None:
            return livery
        return None

    def apply_livery(self) -> None:
        livery = self.determine_livery()
        if livery is None:
            return
        self.vessel.livery_id = livery
