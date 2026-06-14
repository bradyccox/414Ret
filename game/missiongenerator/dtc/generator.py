"""Orchestrates DTC export: which airframes get a cartridge, build, and inject."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, TYPE_CHECKING

from game.missiongenerator.dtc.cartridge import DTC_AIRCRAFT_TYPES, build_cartridge
from game.missiongenerator.dtc.injector import inject_cartridges
from game.missiongenerator.dtc.sadata import collect_sa_data

if TYPE_CHECKING:
    from game import Game


class DtcGenerator:
    """Builds and injects native DCS DTC cartridges for player F-16C / F/A-18C flights."""

    def __init__(self, game: Game) -> None:
        self.game = game

    def _player_dtc_types(self) -> set[str]:
        """DCS types of player-flyable flights on the blue coalition that support DTC."""
        types: set[str] = set()
        for package in self.game.blue.ato.packages:
            for flight in package.flights:
                if flight.client_count <= 0:
                    continue
                dcs_type = flight.unit_type.dcs_unit_type.id
                if dcs_type in DTC_AIRCRAFT_TYPES:
                    types.add(dcs_type)
        return types

    def generate(self, output: Path) -> None:
        dcs_types = self._player_dtc_types()
        if not dcs_types:
            return

        sa = collect_sa_data(self.game)
        terrain_name = self.game.theater.terrain.name
        cartridges: dict[str, dict[str, Any]] = {
            dcs_type: build_cartridge(dcs_type, sa, terrain_name)
            for dcs_type in dcs_types
        }
        inject_cartridges(output, cartridges)
        logging.info(
            "MIZ generation: injected DTC cartridges for %s "
            "(%d threats, %d orbits, %d front lines)",
            ", ".join(sorted(dcs_types)),
            len(sa.threats),
            len(sa.orbits),
            len(sa.front_lines),
        )
