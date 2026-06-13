# 414Ret - 414th Joint Fighter Group's DCS Retribution Fork

This repository is the **414th Joint Fighter Group's customized build of
[DCS Retribution](https://github.com/dcs-retribution/dcs-retribution)** - a turn-based
dynamic campaign generator for [DCS World](https://www.digitalcombatsimulator.com/en/products/world/).

It is a snapshot of upstream Retribution (`dev` branch) **plus the 414th's own
air-defense, electronic-warfare, and assets-pack features**. The unmodified upstream
project README is preserved as [`README.upstream.md`](README.upstream.md).

> **For AI assistants / other Claude sessions:** read [`CLAUDE.md`](CLAUDE.md) first.
> It is the engineering handoff doc - architecture, where each feature lives, the
> branch layout, and what is still in flight.

---

## What's different from upstream

This fork is upstream `dev` at commit `dce851ea` with the following 414th additions
stacked on top (newest first):

### New flight types
- **`FlightType.JAMMING`** - standoff electronic-warfare support flown by the C-130J,
  acting as an EC-130H Compass Call / RC-130H Rivet Joint platform. Driven by the
  bundled `c130j_mission_systems.lua` plugin.

### Air-defense planning rework
- **Per-squadron QRA intercept reserve** from upstream PR `#782`. BARCAP-capable
  squadrons can hold aircraft back on alert via `intercept_reserve`, with coalition
  defaults and Moose `AI_A2A_DISPATCHER` runtime interception.
- **Overlapping BARCAP waves** with jittered timing so CAP doesn't all arrive at once
  (`barcap_overlap_time` setting).
- **Forward CAP line** that pushes CAP toward friendly control points anchoring active
  front lines instead of orbiting deep.
- OPFOR-aggressiveness direction fix and CAS / Armed-Recon engagement-range bumps.

### Quality-of-life & robustness
- **Auto-hide mobile SAMs (SHORAD/AAA/MANPAD) on the MFD** at campaign generation
  (`hide_on_mfd`), including escorts generated inside an armor or missile group
  (which previously slipped onto the datalink). Standalone MERAD/LORAD sites stay
  visible for SEAD.
- **Crash fixes:** flight-combat-exit `IndexError`, AWACS orbit stacking, tanker orbit
  placement/deconfliction, and malformed mod-aircraft payload Lua (e.g. CJS Super
  Hornet v2.4 files that use local-variable table indices).

### Assets
- **CurrentHill Iran assets pack** support: Shahed-136, IRGCN FAC variants, and a
  dedicated `[CH] Iran 2020` faction, behind a new-game mod toggle.

A per-feature breakdown with file paths lives in [`CLAUDE.md`](CLAUDE.md).

---

## Running it

Same as upstream Retribution. Quick start (Windows, PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python qt_ui\main.py
```

You need a working DCS World install and the MOOSE-dependent features assume the
bundled mission plugins under `resources/plugins/` are present. See
[`README.upstream.md`](README.upstream.md) for the full upstream setup, dependencies,
and wiki links.

### Dev checks (must pass before pushing)

```powershell
.venv\Scripts\python.exe -m black --check .      # formatting
.venv\Scripts\python.exe -m mypy game tests       # type checking (CI only checks game + tests)
.venv\Scripts\python.exe -m pytest tests -q       # unit tests
```

---

## Relationship to the 414th workspace

The 414th also maintains a separate **mission-building workspace** (campaign plans,
`.miz` files, and any Mission-Editor-loaded scripts not yet integrated here, such as
the standalone MANTIS IADS). That workspace is private.

Features that started as standalone ME scripts and are now fully integrated into this
repo (do not use the standalone versions):
- **C-130J EW/ISR** → `resources/plugins/c130j/` (`FlightType.JAMMING`)
- **QRA / AI_A2A_DISPATCHER** → `resources/plugins/intercept/` (per-squadron `intercept_reserve`)

This repo is the **engine-level** side: capabilities planned and spawned automatically
by the campaign generator rather than hand-placed in the Mission Editor.

---

## License & credit

DCS Retribution is licensed under the LGPL (see [`LICENSE`](LICENSE)). All upstream
authorship and the project's history are preserved. The 414th additions are provided
under the same terms. Upstream project: <https://github.com/dcs-retribution/dcs-retribution>.
