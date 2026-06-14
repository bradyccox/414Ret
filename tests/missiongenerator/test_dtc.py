"""Tests for the native DCS DTC cartridge export (builder + injector).

These cover the pure, game-independent layers: building a cartridge dict from SA data
(verifying the per-airframe unit quirks) and injecting it into a ``.miz`` archive. The
game-state extraction in ``sadata.py`` needs a full ``Game`` and is exercised in-game.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from game.missiongenerator.dtc.cartridge import (
    F16_TYPE,
    F18_TYPE,
    build_cartridge,
    cartridge_display_name,
)
from game.missiongenerator.dtc.injector import inject_cartridges
from game.missiongenerator.dtc.sadata import OrbitTrack, Polyline, SaData, ThreatRing
from game.utils import meters

_NM_IN_METERS = 1852.0


def _sample_sa() -> SaData:
    return SaData(
        threats=[
            ThreatRing(x=1000.0, y=2000.0, radius_m=20 * _NM_IN_METERS, name="SA-10"),
            ThreatRing(x=3000.0, y=4000.0, radius_m=10 * _NM_IN_METERS, name="SA-6"),
        ],
        orbits=[
            OrbitTrack(
                x=5000.0,
                y=6000.0,
                course_deg=90,
                length_m=18520,
                width_m=9260.0,
                name="Colt 1-1",
            ),
        ],
        front_lines=[Polyline(points=[(0.0, 0.0), (100.0, 200.0)], name="Front")],
    )


def test_f16_cartridge_threat_points_use_metres() -> None:
    cartridge = build_cartridge(F16_TYPE, _sample_sa(), "Syria")

    assert cartridge["type"] == F16_TYPE
    assert cartridge["data"]["terrain"] == "Syria"
    threat_pts = cartridge["data"]["MPD"]["THREAT_PTS"]
    assert len(threat_pts) == 2
    first = threat_pts[0]
    # F-16 threat radius is in metres, and steerpoints start at 56.
    assert first["radius"] == int(20 * _NM_IN_METERS)
    assert first["id"] == "THREAT_PTS56"
    assert first["x"] == 1000.0 and first["y"] == 2000.0


def test_f18_cartridge_mez_uses_nautical_miles() -> None:
    cartridge = build_cartridge(F18_TYPE, _sample_sa(), "Syria")

    assert cartridge["type"] == F18_TYPE
    sa = cartridge["data"]["SA"]
    mez = sa["MEZ_THRTS"]
    assert len(mez) == 2
    # F-18 MEZ radius is in NM (rounded), unlike the F-16's metres.
    assert mez[0]["threat_ring_radius"] == round(
        meters(20 * _NM_IN_METERS).nautical_miles
    )
    assert mez[0]["threat_ring_radius"] == 20

    cap = sa["CAP_PTS"]
    assert len(cap) == 1
    assert cap[0]["course"] == 90 and cap[0]["length"] == 18520

    flot = sa["FAOR_FLOT"]["FLOT"]
    assert len(flot) == 1
    assert [(p["x"], p["y"]) for p in flot[0]["points"]] == [(0.0, 0.0), (100.0, 200.0)]


def test_f16_threat_points_capped_at_15() -> None:
    many = SaData(
        threats=[
            ThreatRing(x=float(i), y=0.0, radius_m=1000.0, name=f"T{i}")
            for i in range(30)
        ]
    )
    threat_pts = build_cartridge(F16_TYPE, many, "Syria")["data"]["MPD"]["THREAT_PTS"]
    # THREAT_PTS only span steerpoints 56-70.
    assert len(threat_pts) == 15
    assert threat_pts[-1]["id"] == "THREAT_PTS70"


def test_template_partitions_preserved() -> None:
    cartridge = build_cartridge(F18_TYPE, _sample_sa(), "Syria")
    # The non-generated partitions from the ME template must survive untouched so the
    # cartridge stays structurally complete and loadable.
    assert "COMM" in cartridge["data"]
    assert "ALR67" in cartridge["data"]


def test_inject_cartridges_adds_dtc_member(tmp_path: Path) -> None:
    miz = tmp_path / "test.miz"
    with zipfile.ZipFile(miz, "w") as z:
        z.writestr("mission", "mission = {}")

    cartridges = {
        F18_TYPE: build_cartridge(F18_TYPE, _sample_sa(), "Syria"),
        F16_TYPE: build_cartridge(F16_TYPE, _sample_sa(), "Syria"),
    }
    inject_cartridges(miz, cartridges)

    with zipfile.ZipFile(miz) as z:
        names = z.namelist()
        assert "mission" in names
        arcname = f"DTC/{cartridge_display_name(F18_TYPE)}.dtc"
        assert arcname in names
        loaded = json.loads(z.read(arcname))
        assert loaded["type"] == F18_TYPE


def test_inject_cartridges_noop_when_empty(tmp_path: Path) -> None:
    miz = tmp_path / "test.miz"
    with zipfile.ZipFile(miz, "w") as z:
        z.writestr("mission", "mission = {}")
    inject_cartridges(miz, {})
    with zipfile.ZipFile(miz) as z:
        assert z.namelist() == ["mission"]


@pytest.mark.parametrize("dcs_type", [F16_TYPE, F18_TYPE])
def test_display_name_round_trips(dcs_type: str) -> None:
    assert cartridge_display_name(dcs_type).endswith(" DTC_1")
