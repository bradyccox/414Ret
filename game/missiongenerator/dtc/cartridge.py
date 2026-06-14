"""Build per-airframe DTC cartridge dicts by overlaying SA data onto the templates.

Each template (``resources/dtc/templates/<dcs_type>.dtc``) is a real ME-authored
cartridge with the generated arrays emptied but every other partition (COMM, RWR/ELINT,
CMDS) left at the ME defaults, so the result is always structurally complete and loadable.
We only fill the SA/threat partitions; see the design notes for the per-airframe quirks.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from game.missiongenerator.dtc.sadata import OrbitTrack, Polyline, SaData, ThreatRing
from game.utils import meters

TEMPLATE_DIR = Path("resources/dtc/templates")

F16_TYPE = "F-16C_50"
F18_TYPE = "FA-18C_hornet"

#: DCS types that support DTC. Used to gate which player flights get a cartridge.
DTC_AIRCRAFT_TYPES = frozenset({F16_TYPE, F18_TYPE})

#: Cartridge display names (the in-sim DTC name + archive filename stem). These mirror
#: what the Mission Editor produced for the reverse-engineering sample.
_DISPLAY_NAME = {
    F16_TYPE: "F-16CM bl.50",
    F18_TYPE: "FA-18C Lot 20",
}

# F-16 MPD steerpoint ranges (see design notes / DCS changelog).
_F16_THREAT_FIRST_STPT = 56  # THREAT_PTS span steerpoints 56-70...
_F16_THREAT_LAST_STPT = 70  # ...so at most 15 rings fit.
_F16_THREAT_ALT_M = 9144  # 30,000 ft, matching the ME default ring altitude.


def cartridge_display_name(dcs_type: str) -> str:
    return f"{_DISPLAY_NAME[dcs_type]} DTC_1"


def _load_template(dcs_type: str) -> dict[str, Any]:
    path = TEMPLATE_DIR / f"{dcs_type}.dtc"
    return json.loads(path.read_text(encoding="utf-8"))


def _f16_threat_pts(threats: list[ThreatRing]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    capacity = _F16_THREAT_LAST_STPT - _F16_THREAT_FIRST_STPT + 1
    for i, t in enumerate(threats[:capacity]):
        out.append(
            {
                "alt": _F16_THREAT_ALT_M,
                "def_num": 1,
                "elev": 0,
                "id": f"THREAT_PTS{_F16_THREAT_FIRST_STPT + i}",
                "number": i + 1,
                "radius": int(t.radius_m),  # F-16 threat radius is in METRES.
                "ring": True,
                "text": "CST",
                "threatName": "Custom",
                "x": t.x,
                "y": t.y,
            }
        )
    return out


def _f18_mez_thrts(threats: list[ThreatRing]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, t in enumerate(threats):
        out.append(
            {
                "id": f"MEZ_THRTS_{i + 1}",
                "num": i + 1,
                "text": "",
                "threat_level": 1,
                # F-18 MEZ ring radius is in NAUTICAL MILES (F-16 uses metres).
                "threat_ring_radius": round(meters(t.radius_m).nautical_miles),
                "threat_type": "Custom",
                "x": t.x,
                "y": t.y,
            }
        )
    return out


def _f18_cap_pts(orbits: list[OrbitTrack]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, o in enumerate(orbits):
        out.append(
            {
                "id": f"CAP_PTS_{i + 1}",
                "num": i + 1,
                "note": "",
                "course": o.course_deg,
                "diameter": o.width_m,
                "length": o.length_m,
                "turn_direction": "Left",
                "x": o.x,
                "y": o.y,
            }
        )
    return out


def _f18_flot_lines(front_lines: list[Polyline]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, line in enumerate(front_lines):
        line_id = f"FLOT_{i + 1}"
        out.append(
            {
                "id": line_id,
                "num": i + 1,
                "note": "",
                "points": [
                    {"id": f"{line_id}_PT_{k + 1}", "x": x, "y": y}
                    for k, (x, y) in enumerate(line.points)
                ],
            }
        )
    return out


def _build_f16(template: dict[str, Any], sa: SaData) -> None:
    template["data"]["MPD"]["THREAT_PTS"] = _f16_threat_pts(sa.threats)


def _build_f18(template: dict[str, Any], sa: SaData) -> None:
    sa_part = template["data"]["SA"]
    sa_part["MEZ_THRTS"] = _f18_mez_thrts(sa.threats)
    sa_part["CAP_PTS"] = _f18_cap_pts(sa.orbits)
    sa_part["FAOR_FLOT"]["FLOT"] = _f18_flot_lines(sa.front_lines)


def build_cartridge(dcs_type: str, sa: SaData, terrain_name: str) -> dict[str, Any]:
    """Return a complete cartridge dict for ``dcs_type`` with SA data overlaid."""
    cartridge = _load_template(dcs_type)

    name = cartridge_display_name(dcs_type)
    cartridge["name"] = name
    cartridge["type"] = dcs_type
    cartridge["data"]["name"] = ""
    cartridge["data"]["type"] = dcs_type
    cartridge["data"]["terrain"] = terrain_name
    if "MPD" in cartridge["data"]:
        cartridge["data"]["MPD"]["terrain"] = terrain_name

    if dcs_type == F16_TYPE:
        _build_f16(cartridge, sa)
    elif dcs_type == F18_TYPE:
        _build_f18(cartridge, sa)
    return cartridge
