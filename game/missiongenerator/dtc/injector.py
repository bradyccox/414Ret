"""Inject cartridge JSON into the saved ``.miz`` archive.

DCS stores cartridges as standalone ``DTC/<name>.dtc`` JSON members inside the mission
zip and matches them to aircraft by the ``type`` field -- there is no per-unit reference
in the ``mission`` table. So injection is a pure post-save archive append; pydcs and the
mission dict are untouched. See ``docs/dev/design/414th-dtc-export-notes.md``.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from game.missiongenerator.dtc.cartridge import cartridge_display_name


def inject_cartridges(miz_path: Path, cartridges: dict[str, dict[str, Any]]) -> None:
    """Append a ``DTC/<display name> DTC_1.dtc`` entry per cartridge to the ``.miz``.

    ``cartridges`` maps DCS aircraft type id -> cartridge dict.
    """
    if not cartridges:
        return
    with zipfile.ZipFile(miz_path, "a", zipfile.ZIP_DEFLATED) as miz:
        existing = set(miz.namelist())
        for dcs_type, cartridge in cartridges.items():
            arcname = f"DTC/{cartridge_display_name(dcs_type)}.dtc"
            if arcname in existing:
                # mission.save() never writes DTC members, so this only guards against a
                # duplicate type slipping through; skip rather than corrupt the archive.
                continue
            miz.writestr(arcname, json.dumps(cartridge, indent=2))
