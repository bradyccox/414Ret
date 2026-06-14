# 414th — Native DCS DTC export (design + reverse-engineered schema)

Goal: have Retribution auto-write **native DCS Data Transfer Cartridges** into the
generated `.miz` so F-16C / F/A-18C players spawn with coalition comms, the SA picture
(CAP tracks, corridors, FAOR/FLOT, MEZ threats), threat rings, TACAN, and (optionally)
the route already loaded.

This doc is the ground truth for the storage format. It was reverse-engineered from a
real ME-authored sample (`dtc_sample.miz`, F-16C + F/A-18C, all partitions filled),
decoded with `dtc_schema_dump.py` at the repo root. DCS DTC is **F-16C + F/A-18C only**.

---

## TL;DR architecture (this changes the earlier plan)

- **Cartridges are standalone JSON files inside the `.miz` archive**, in a `DTC/` folder:
  - `DTC/F-16CM bl.50 DTC_1.dtc`
  - `DTC/FA-18C Lot 20 DTC_1.dtc`
  - The file body is JSON (not Lua), pretty-printed.
- **There is NO per-unit reference in the `mission` table.** The unit dicts for the
  F-16/F-18 contained *zero* DTC linkage; the whole `mission` blob has no `dtc` substring.
  A thorough search of every other archive member (`options`, `warehouses`,
  `dictionary`, `mapResource`, `theatre`) found no linkage either.
- **Linkage is by aircraft TYPE + slot index.** The cartridge is matched to aircraft by
  the `"type"` field inside the `.dtc` (e.g. `F-16C_50`, `FA-18C_hornet`) and the
  filename. The `_1` suffix is the cartridge **slot**; `DTC_1` is the default/loaded one.

### Consequences for Retribution
- **We do NOT touch pydcs or the `mission` table.** Implementation = build JSON dicts and
  inject `DTC/*.dtc` entries into the zip *after* `self.mission.save(output)`
  (`game/missiongenerator/missiongenerator.py:140`). Much simpler than per-unit injection.
- **Cartridges are type-scoped.** All F-16s in a mission share one cartridge; all Hornets
  share another. We produce **one cartridge per (airframe type)** present on the player
  coalition. This is a natural fit for coalition-wide data (comms ladder, SA picture,
  threat rings, TACAN) but means a per-flight *own route* cannot differ between two
  flights of the same airframe. See "Route handling" below.
- Per-unit/per-cartridge assignment *may* exist in the in-sim "Load to group" flow, but
  its storage format is **unverified** (the sample did not produce it). Do not build on it
  without a fresh sample proving the format.

---

## Coordinates & units (verified from sample)

- All positions are **DCS world coordinates in meters**, fields `x` (north) / `y` (east) —
  the same projection pydcs/Retribution already use. `Point.x` -> `x`, `Point.y` -> `y`
  **directly, no conversion.**
- `alt` / `elev` are **meters**.
- **Threat ring radius units differ by airframe** (be careful):
  - F-16 `THREAT_PTS[].radius` is in **meters** (sample: `37040` = 20 nm).
  - F/A-18 `MEZ_THRTS[].threat_ring_radius` is in **nautical miles** (sample: `20`).
- TACAN `frequency` is in **Hz** (sample: `977000000`).
- COMM frequency is an **integer in MHz** (e.g. `305`, `124`).
- `modulation`: F-16 COMM used `1`; F-18 COMM used `0`. (AM/FM — confirm per radio.)

---

## File envelope (both airframes)

```json
{
  "data": { ...partitions... , "name": "", "terrain": "Caucasus", "type": "<TYPE>" },
  "name": "<TypeDisplayName> DTC_1",
  "type": "<TYPE>"
}
```

`terrain` is the map name; must match the mission's theatre. `<TYPE>` is the DCS unit
type id (`F-16C_50`, `FA-18C_hornet`).

---

## F-16C partitions (`data` children)

- `COMM`: `COMM1`, `COMM2`, each `Channel_1..Channel_20` = `{ "freq": <MHz int>,
  "modulation": <int> }`. Plus `mirror_COMM1`/`mirror_COMM2` bools.
  (NOTE: F-16 channel objects have **no** `name`; F-18 do — see below.)
- `ELINT`: `{ "RWR": { ... } }` — a large per-emitter priority/display table
  (`display`, `PRI`, `search`, `unknown` per radar). Big default table; preserve defaults.
- `MPD`:
  - `CMDS`: `CMDSBingoSettings` (`BINGO`,`ChaffNum`,`FlaresNum`,`Other1Num`,`Other2Num`,
    `FDBK`,`REQCTR`) + `CMDSProgramSettings` with programs `AUTO1..3`, `BYP`, `MAN1..4`,
    each `{ Chaff|Flare|Other1|Other2: { BurstInterval, BurstQuantity, SalvoInterval,
    SalvoQuantity } }`. Also a per-missile MWS threshold table.
  - `NAV_PTS`: array of steerpoints. Rich object: `id:"STPT<n>"`, `number`, `type:"STPT"`,
    `x`,`y`,`alt`, `altitudeType`, `speed`, `routeAltitude`, `TOS`/`isTOSEnabled`,
    OAP fields (`OAP_1_*`,`OAP_2_*`,`idOA1`,`idOA2`,`isOAP_1/2`), `R1/R2/R3`,
    `velocityType`, `note`.
  - `DEST`: array, ids `DEST81..` (steerpoints 81-99). `{ alt,id,note,number,text:"D81",x,y }`.
  - `GEO_LINES`: array, ids `GEO_LINES31..` (31-55). `{ alt,id,L1..L4(bool),note,number,x,y }`.
  - `THREAT_PTS`: array, ids `THREAT_PTS56..` (56-70).
    `{ alt,def_num,elev,id,number,radius(meters),ring(bool),text:"CST",threatName:"Custom",x,y }`.
  - `mirror_DEST`, `mirror_GEO_LINES`, `mirror_NAV_PTS`, `mirror_THREAT_PTS` bools.
  - `terrain`.

## F/A-18C partitions (`data` children)

- `COMM`: `COMM1`,`COMM2`, `Channel_1..20` = `{ "frequency": <MHz int>, "modulation":
  <int>, "name": "CH n" }`. (Key is `frequency` + has `name`, unlike F-16's `freq`.)
- `ALR67`: RWR/threat table (analogue of F-16 `ELINT`).
- `SA` (the SA-page graphics partition):
  - `CAP_PTS`: `{ id:"CAP_PTS_<n>", num, x, y, course, diameter(m), length(m),
    turn_direction:"Left"|"Right", note }`. A racetrack: diameter+length+course+turn.
  - `CORRIDORS`: `{ id:"CORR_<n>", num, note, points:[{id:"CORR_<n>_PT_<k>",x,y}] }`.
  - `FAOR_FLOT`: `{ FAOR:[{id,num,note,points:[{id,x,y}]}], FLOT:[...same...] }`.
  - `MEZ_THRTS`: `{ id:"MEZ_THRTS_<n>", num, text, threat_level(int), threat_ring_radius
    (NM), threat_type:"Custom", x, y }`.
  - `SETTINGS`: `DCLTR_SETTINGS` (`MREJ1`,`MREJ2` -> per-layer declutter bools) +
    `SENSORS_SETTINGS` (`FF_tracks`,`FRIEND_Symbols`,`PPLI_tracks`,`RWR_Symbols`,
    `SURV_tracks`,`UNK_tracks`).
  - `Default_CAP_Point`, `Default_CORRIDORS_Point`, `Default_FAOR_Line`,
    `Default_FLOT_Line`, `Default_MEZ_THRTS_Level` (ints), `mirror_MEZ_THRTS` bool.
- `TCN`: array of TACAN beacons `{ callsign, channel, display_name, elevation,
  frequency(Hz), x, y }`.
- `WYPT`: `{ mirror_NAV_PTS(bool), NAV_PTS:[{ id:"STPT<n>", alt, altitudeType, idOA,
  idOA_Line, isOA, OA_* fields, R1/R1_order/R2/R3, text_note, ... , x, y }] }`.
  (Single OA per point, vs F-16's OA1/OA2.)

---

## Retribution data -> DTC mapping

| DTC field | Retribution source |
|---|---|
| F-18 `SA.CAP_PTS` | BARCAP/TARCAP racetrack geometry (center, course, leg length) |
| F-18 `SA.CORRIDORS` | ingress/egress corridor + tanker tracks |
| F-18 `SA.FAOR_FLOT.FLOT` | front line trace |
| F-18 `SA.MEZ_THRTS` / F-16 `THREAT_PTS` | SAM network sites + threat radii |
| F-18 `TCN` | tanker/airfield TACAN beacons |
| `COMM` | per-coalition radio preset ladder |
| `MPD.CMDS` | faction/airframe countermeasure program defaults |
| `NAV_PTS` / `DEST` | package/flight waypoints (see route handling) |

## Route handling (the one open product decision)

Because cartridges are type-scoped, NAV_PTS/DEST can't differ between two flights of the
same airframe. Options:
- **(A, recommended)** Don't inject own-route waypoints. Inject only coalition-shared
  data: COMM, SA (CAP/CORRIDORS/FAOR/FLOT/MEZ), THREAT_PTS, TACAN, CMDS. No conflict with
  ME flight plans; every value is genuinely coalition-wide.
- **(B)** Also inject a shared route (identical steerpoints for all same-type jets) — only
  sensible for single-flight or single-airframe packages.

---

## Implementation outline

- `game/missiongenerator/dtc/` package:
  - `model.py` — typed dataclasses for the cartridge + partitions.
  - `f16.py`, `f18.py` — airframe-specific envelope/key differences.
  - `builders.py` — map Retribution (packages, flights, threat zones, front line,
    tankers, comms) -> partition dicts.
  - `injector.py` — write `DTC/<name>.dtc` JSON entries into the saved `.miz` zip.
- Hook after `self.mission.save(output)` in `missiongenerator.py`.
- Settings: a `generate_dtc` toggle (default off until in-game validated).
- Tests: builder unit tests from fakes; JSON round-trip; injector adds expected entries.

## Implemented (v1) vs deferred

Shipped (`game/missiongenerator/dtc/`, gated by the `generate_dtc` setting, default off):
- **F/A-18C** `SA`: `MEZ_THRTS` (enemy threat rings, radius in NM), `CAP_PTS` (player CAP
  **and** tanker racetracks), `FAOR_FLOT.FLOT` (front line trace).
- **F-16C** `MPD.THREAT_PTS` (enemy threat rings, radius in metres, capped at 15 = stpts
  56-70).
- Cartridges are built by overlaying SA data onto the captured ME templates
  (`resources/dtc/templates/<dcs_type>.dtc`), so COMM / RWR(ELINT/ALR67) / CMDS keep their
  ME defaults and the cartridge stays structurally complete. Injected as `DTC/*.dtc` zip
  members after `mission.save()`.

Deferred (each needs more work or another decoded sample):
- **F-16 `GEO_LINES`** (front line / corridors as drawn lines): the per-point `L1`-`L4`
  line-connection flags were all `false` in the sample, so their semantics are undecoded.
  Decode with a sample that actually draws GEO lines before implementing.
- **`CORRIDORS`** (ingress/egress lanes) and **`TCN`** (airfield TACAN beacons): TCN needs
  beacon->map-position wiring (`Beacons` carries freq/channel but no position).
- **COMM / CMDS generation**: templates currently carry stock ME defaults; pydcs already
  bakes per-flight radio presets into units independently of DTC.
- **Per-flight own routes** (`NAV_PTS`/`DEST`): impossible under type-scoping (decided).
- Re-decode helper: `dtc_schema_dump.py` (repo root) against a fresh sample `.miz`.

## Validation
- `black --check .`, `mypy game tests`, `pytest tests -q`
  (`tests/missiongenerator/test_dtc.py`).
- In-game: load a generated mission, ramp-start an F-16 and an F/A-18, confirm the default
  cartridge auto-loads with the expected COMM/SA/threat data.

## Scratch artifacts (delete before commit)
- `dtc_schema_dump.py`, `dtc_dump.txt` at repo root — analysis only, not part of the feature.
