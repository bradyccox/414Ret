"""Native DCS Data Transfer Cartridge (DTC) export.

Writes ``DTC/*.dtc`` cartridge files into the generated ``.miz`` so F-16C / F/A-18C
players spawn with the coalition SA picture (threat rings, front line, CAP/tanker
tracks) already loaded. See ``docs/dev/design/414th-dtc-export-notes.md`` for the
reverse-engineered storage format and the rationale behind the type-scoped design.
"""

from __future__ import annotations

from game.missiongenerator.dtc.generator import DtcGenerator

__all__ = ["DtcGenerator"]
