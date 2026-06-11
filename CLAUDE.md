# CLAUDE.md — 414Ret engineering handoff

This is the **414th Joint Fighter Group's fork of DCS Retribution**. Read this before
touching anything. It explains what the 414th added on top of upstream, where each piece
lives, how to validate changes, and what is still in flight.

If you're a human, the friendly overview is in [`README.md`](README.md). This file is the
deep version for the next coding session.

---

## TL;DR

- Base: upstream `dcs-retribution/dcs-retribution` `dev` @ `dce851ea`.
- On top: SCRAMBLE + JAMMING flight types, an air-defense planning rework, MFD/robustness
  fixes, and the CurrentHill Iran assets pack. ~25 commits.
- **Lua 5.1** sandbox for the mission plugins (no `os`/`io`, no `goto`, definition order
  matters). Python side is normal Python 3.11.
- CI gates: **Black** (`black --check .`) and **mypy** (`mypy game` + `mypy tests` only —
  `qt_ui` is NOT type-checked in CI but DOES get Black-checked). Plus pytest.

---

## Validation (do this before every push)

```powershell
.venv\Scripts\python.exe -m black --check .      # 0 files to reformat
.venv\Scripts\python.exe -m mypy game tests       # 0 new errors
.venv\Scripts\python.exe -m pytest tests -q       # all green
```

Notes learned the hard way:
- CI Black checks the **whole tree** (`.`), including `qt_ui` and `tests`. CI mypy only
  checks `game` and `tests`. So a type error in `qt_ui` will pass CI but a formatting
  miss anywhere will fail it.
- `qt_ui/main.py` has ~5 PRE-EXISTING mypy errors that also exist on upstream `dev`.
  Don't try to "fix" those — they're not in the CI mypy path and aren't ours.
- For test files that fake Retribution objects (duck-typed `Coalition`, `Faction`,
  `AircraftType`), prefer a narrow `# type: ignore[arg-type]` over restructuring, matching
  how the existing fakes are annotated.

---

## The 414th features, by area

### 1. SCRAMBLE flight type — reactive QRA interceptors
RED air-to-air aircraft sit cold/uncontrolled on the ramp and launch only when BLUE
crosses a forward border.

- Enum: `game/ato/flighttype.py` (`FlightType.SCRAMBLE`, in `is_air_to_air`, mapped to
  `AirEntity.FIGHTER`).
- Planner reserve: `game/squadrons/squadron.py` `scramble_reserve` property +
  `can_auto_assign_mission()` guard. Holds back `reactive_scramble_reserve` airframes so
  the pool isn't empty.
- Mission generation: `game/missiongenerator/aircraft/aircraftgenerator.py`
  `_spawn_unused_for()` collects eligible RED untasked uncontrolled A/A into the scramble
  pool (`MAX_SCRAMBLE_GROUPS_PER_AIRFIELD = 4`).
- Lua injection + border: `game/missiongenerator/luagenerator.py`
  `_inject_scramble_script()` and `_scramble_border_points()` (`SCRAMBLE_BORDER_BUFFER`,
  30 nm forward of RED territory). Pool is emitted as `dcsRetribution.scramble_pool`.
- Plugin script: `resources/plugins/scramble/reactive_scramble.lua` (+ `plugin.json`).
  It does **not** key off group names — it wakes whatever is in `scramble_pool`. Requires
  the "Disable untasked OPFOR aircraft at airfields" option to be **unchecked**.
- Settings: `enable_reactive_scramble`, `reactive_scramble_reserve` in
  `game/settings/settings.py`.

**Launch lesson (important):** pooled groups spawn route-less (single `TakeOffParking`,
uncontrolled). `GROUP:StartUncontrolled()` only starts engines; the `setTask(EngageTargets)`
is what actually drives takeoff. Do NOT gate tasking on an `InAir` poll — that deadlocks.
Start, wait `CFG_spawnDelay`, then task. Early builds registered QRA as ONLINE but never
launched because the radar-proximity trigger never fired; the border-penetration trigger
fixes that.

### 2. JAMMING flight type — C-130J EW/ISR
- Enum: `game/ato/flighttype.py` (`FlightType.JAMMING` →
  `AirEntity.ELECTRONIC_COMBAT_JAMMER`).
- Behavior: `game/missiongenerator/aircraft/aircraftbehavior.py` `configure_jamming()`
  (AWACS-style orbit + `WEAPON_HOLD` ROE).
- Spawn fallback: `game/missiongenerator/aircraft/flightgroupspawner.py` tries RUNWAY
  start when no parking is available.
- Lua injection: `game/missiongenerator/luagenerator.py` `_has_c130j_flights()` +
  `_inject_c130j_script()`.
- Plugin script: `resources/plugins/c130j/c130j_mission_systems.lua` (+ `plugin.json`).
- Loadout/package wiring: `game/ato/loadouts.py`, `game/ato/package.py`,
  `game/theater/missiontarget.py`, `game/pretense/pretenseaircraftgenerator.py`.

**C-130 EW hard constraints (carried over from the standalone ME script):** do NOT toggle
SAM radar emissions (`enableEmission(false)` crashed DCS — suppression is ROE WEAPON_HOLD
only); the burn-through model intentionally RAISES jam probability with distance; spot
jamming has flat altitude-independent range; the missile-spoof curve is intentionally steep
at close range. Don't "fix" these.

### 3. Air-defense planning rework
Design notes: `docs/dev/design/414th-air-defense-planning-notes.md` (read this for intent).
- Overlapping CAP waves + jitter: `game/commander/missionscheduler.py` (uses
  `barcap_overlap_time`); rounds math in `game/commander/theaterstate.py`.
- Forward CAP line: `game/commander/objectivefinder.py` `vulnerable_control_points()`
  (checks `cp.has_active_frontline`; also fixes an inverted aggressiveness comparison).
- Engagement-range bumps: `game/settings/settings.py` (`cas_engagement_range_distance`
  10→15 nm, `armed_recon_engagement_range_distance` 5→10 nm).

### 4. Auto-hide mobile SAMs on MFD
- `game/armedforces/forcegroup.py`: `hide_on_mfd` field, `_MOBILE_TASKS = {SHORAD, AAA}`,
  propagated through `for_layout()` / `from_preset_group()` / `create_ground_object_for_layout()`.

### 5. Robustness / crash fixes
- Flight-combat-exit `IndexError`: `game/ato/flightstate/inflight.py` guards in
  `__init__` and `next_waypoint_state()`.
- AWACS orbit stacking + direction: `game/ato/flightplans/aewc.py`.
- Tanker orbit placement/deconfliction: `game/ato/flightplans/theaterrefueling.py`.
- Malformed mod payload Lua (CJS Super Hornet v2.4 uses local-var table indices that the
  pydcs Lua parser rejects with `ValueError`): patched loader in `qt_ui/main.py`
  (`_patch_pydcs_payload_loader()`), plus the offending files are skipped with a warning.

### 6. CurrentHill Iran assets pack
- Unit defs: `pydcs_extensions/iranmilitaryassetspack/` (Shahed-136 `CH_Shahed136`,
  `IranFAC_MG`, `IranFAC_MG_AShM`), re-exported from `pydcs_extensions/__init__.py`.
- Radar DB: `game/data/radar_db.py`. Mod removal logic: `game/factions/faction.py`.
- New-game toggle: `game/theater/start_generator.py` (`iranmilitaryassetspack` field),
  `qt_ui/windows/newgame/...` wizard pages.
- Faction: `resources/factions/CH_iran_2020.json` (`[CH] Iran 2020`).

---

## Branch & repo layout

- This repo (`bradyccox/414Ret`) `main` = the consolidated, most-up-to-date 414th build.
- Upstream is `dcs-retribution/dcs-retribution`; the 414th's PR fork is
  `bradyccox/dcs-retribution`. Open upstream PRs carved out of this work:
  - **#784** `codex/currenthill-iran-pack` — the Iran pack (the branch also carries the
    full feature stack).
  - **#786** `codex/fix-aaq33-era-restriction` — targeting-pod era-restriction fix
    (separate, small; NOT part of the feature stack on `main`).
- The 414th's primary "all features" working branch in the dev checkout is
  `414th-all-features`; `main` here = that + the Iran pack + a Black/mypy lint pass.

## Still in flight / deferred

- Full 256-aircraft YAML mission-preference rebalance is **held** until in-game
  scramble/CAP validation is done. Two targeted YAML fixes already landed (Tu-22M3
  anti-ship 800, M-2000C A2A 460).
- Reactive scramble has been validated in code/unit tests but the end-to-end in-game
  launch (border trigger → cold start → takeoff → intercept) should be re-checked after
  any change to the pool or border logic.

## Conventions

- Lua plugins: Lua 5.1 only, vanilla DCS units only (no HighDigitSAMs etc.), define
  functions before first use.
- Keep player-facing plugin behavior and any overview docs in sync with code changes.
- Match the surrounding code's style; run the three validation commands above before
  pushing.
