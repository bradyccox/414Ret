-- Intercept (QRA) — drives AI_A2A_DISPATCHER per coalition from
-- dcsRetribution.Intercept. Aircraft are placed as late-activated template
-- groups by the mission generator; ParkDefender spawns parked instances and
-- recycles them on RTB, consuming a resource permanently on a kill.
--
-- Detection (dr-ktw0): the dispatcher's DETECTION_AREAS is fed from the real
-- EWR/SAM-as-EWR group names published in dcsRetribution.IADS for the
-- coalition (the same source Skynet uses). The previous FilterPrefixes("EWR")
-- matched almost nothing, because DCS EWR group names are suffix-form
-- ("1L13 EWR", "55G6 EWR").
--
-- Detection has two sources: the IADS EWR/SAM-as-EWR network (primary, wide
-- area) and a hidden/invisible/immortal backstop EWR at each alert base
-- (guaranteed fallback — catches anything that slips through or survives after
-- the EWR network is destroyed). The backstop always spawns; it is independent
-- of GciRadius.
--
-- GciRadius (groundControlledInterceptionMaxRadius, default 100 NM) caps how
-- far from a base a detected raid can trigger a scramble. The dispatcher only
-- scrambles GCI once AirbaseDistance <= GciRadius. The IADS network provides
-- the real detection range; GciRadius just prevents scrambling against very
-- distant threats heading elsewhere.
--
-- The backstop EWR DCS type is supplied per record by the mission generator
-- (rec.backstopEwrType) rather than hardcoded here. If the type is unknown to
-- the running DCS build, mist.dynAdd silently spawns nothing; we therefore
-- verify each backstop group exists before trusting it as a detection source
-- and fall back to the EWR network for that base otherwise.
--
-- Build timing: backstop EWRs are spawned with mist.dynAdd up front, but the
-- detection SET_GROUP (and the dispatcher) are assembled BUILD_DELAY seconds
-- later. mist.dynAdd registers a group via a birth event on the next frame, so
-- a SET_GROUP:FilterStart() built synchronously would not yet see the backstop.
-- The short delay lets the groups register first.
--
-- AI_A2A_DISPATCHER:New() calls self:__Start(5) internally — no explicit
-- dispatcher:Start() call is needed or valid (no such method exists).
--
-- Spawn path: NON-VISIBLE / fresh-spawn-on-scramble. We deliberately do NOT
-- call SetSquadronVisible. That keeps Moose's AI_A2A_DISPATCHER:ResourceActivate
-- in its else branch, which spawns a fresh group at scramble time honoring the
-- configured takeoff method (SetDefaultTakeoffInAir below).
--
-- Takeoff method history (all validated in-DCS):
--   1. Visible/ParkDefender pre-park: ParkDefender hardcodes SPAWN.Takeoff.Cold
--      (ignores SetDefaultTakeoff*), so F-16s sat cold and never completed the
--      cold-start→taxi sequence. SetSquadronVisible also clamps ResourceCount to
--      free parking spots and forces Grouping=1. Abandoned.
--   2. Non-visible ParkingHot (warm): F-16s DID scramble warm but still never
--      taxied out of congested ramps (e.g. Tiyas, packed with OCA + ~30 rotary
--      BARCAP — confirmed in-DCS), while
--      the identical code launched fine from uncluttered bases like H3. Ground
--      movement, not takeoff method, was the blocker.
--   3. Runway: SetDefaultTakeoffFromRunway spawned fine at uncluttered H3 (jets on
--      the runway, immediate takeoff) but at saturated Tiyas Moose could not place
--      them on the runway and dumped them into hangars, where they sat. Every
--      ground spawn (cold/hot/runway) fails on a fully-packed ramp.
--   4. In-air (current): the only method that escapes the congested ground. It was
--      blocked by a Moose bug (air-spawn's BASE:CreateEventTakeoff is mis-scheduled
--      → self is a plain table → self:F() crash → defenders never activate). The
--      BASE.CreateEventTakeoff monkeypatch above repairs that without touching the
--      vendored Moose.lua, so in-air now works. Upstream fix filed as MOOSE PR
--      #2595 (Core/Spawn.lua: pass the args as varargs, not a single table);
--      drop the monkeypatch once that lands in the vendored Moose.lua.
--
-- The non-visible path keeps full reserve and real 2-ship grouping (the visible
-- path lost both).
--
-- SetSquadronGci speed args are in km/h (WaypointAir divides by 3.6 to get m/s).
-- 900/1200 km/h ≈ 485/648 kt — reasonable for jet interceptors.

env.info("DCSRetribution|Intercept: configuring QRA dispatchers")

intercept_survivors = intercept_survivors or {}

-- Registry: maps squadronId -> { dispatcher, squadronName }. Populated by the
-- deferred dispatcher build (BUILD_DELAY seconds in), then read by the refresh
-- loop.
local intercept_registry = {}

-- QRA tuning (comms, GCI radius, engagement range) is sourced from the Campaign
-- Doctrine settings and carried on each Intercept record by the mission generator
-- (gciMaxRadiusNm/engagementRangeNm/commsEnabled). The values are global, so each
-- record in a coalition carries the same trio; build_dispatcher reads them from
-- records[1]. add_key_value serializes everything as a string, hence tonumber()
-- for the numerics and a string compare ("false") for the boolean.
local NM = 1852  -- metres per nautical mile
local DETECTION_GROUPING_M = 30000  -- contact-clustering radius for DETECTION_AREAS
-- BUILD_DELAY serves two purposes: (1) let mist.dynAdd backstop EWRs register their
-- birth events before SET_GROUP:FilterStart() runs (needs ~1 frame, so 5s was fine);
-- (2) give in-flight BLUE spawns time to move away from their start positions before
-- the dispatcher arms. Without this, any BLUE aircraft that spawns within GciRadius
-- of a RED base at T+0 immediately triggers a scramble. 90 s is enough for AI flights
-- to reach their cruise altitude/speed and clear the immediate vicinity.
local BUILD_DELAY = 90
local QRA_SPAWN_ALTITUDE_M = 6000
-- EngageFloor/Ceiling in SetSquadronGci2 are the TARGET altitude band the GCI
-- task will fire on — not the interceptors' patrol altitude.  Setting these to
-- 5500/9000 meant the EngageTargets task silently skipped anything below 5500 m
-- (e.g. MQ-9s, low-level strike packages).  Widen to cover all DCS airspace.
local QRA_ENGAGE_FLOOR_M = 100     -- ~330 ft BARO: catches helicopters & low-level
local QRA_ENGAGE_CEILING_M = 15000 -- ~49 000 ft: covers everything in DCS
local qra_announced_groups = { BLUE = {}, RED = {} }

-- ---------------------------------------------------------------------------
-- MOOSE BUG WORKAROUND — air-spawn takeoff event
-- Upstream fix filed as MOOSE PR #2595
-- (https://github.com/FlightControl-Master/MOOSE/pull/2595). REMOVE THIS WHOLE
-- `do … end` BLOCK once that PR is released and pulled into Retribution's
-- vendored resources/plugins/base/Moose.lua — check the SpawnAtAirbase call site
-- there passes the args as varargs (no surrounding braces) before deleting.
-- Core/Spawn.lua SpawnAtAirbase schedules the synthetic takeoff event as:
--   self:ScheduleOnce(5, BASE.CreateEventTakeoff, {GroupSpawned, time, dcsObject})
-- ScheduleOnce forwards its trailing args as VARARGS, so that single table becomes
-- argument #1 — i.e. CreateEventTakeoff runs with the {group,time,dcs} table as
-- `self`. A plain table has no :F(), so the first line (self:F(...)) errors, the
-- takeoff event never fires, and air-spawned AI_A2A_DISPATCHER defenders never
-- activate (observed: zero QRA flew on either side with takeoff=Air). A sibling
-- call site uses SCHEDULER:New(nil, fn, {args}, 5) — which DOES treat the table as
-- the arg list — and is correct; the SpawnAtAirbase one is the regression.
--
-- We don't touch the vendored Moose.lua: override BASE.CreateEventTakeoff to
-- detect the mis-packed call (self is the args table, has no :F) and fire a proper
-- takeoff event; all well-formed calls delegate to the original untouched. Remove
-- once the upstream fix is vendored. Upstream fix = drop the braces at that line so
-- the args pass as varargs.
-- ---------------------------------------------------------------------------
do
    local _orig_create_event_takeoff = BASE.CreateEventTakeoff
    function BASE:CreateEventTakeoff(EventTime, Initiator)
        if type(self) == "table" and type(self.F) ~= "function" then
            -- self is the mis-packed {GroupSpawned, time, dcsObject} table.
            world.onEvent({
                id = world.event.S_EVENT_TAKEOFF,
                time = self[2],
                initiator = self[3],
            })
            return
        end
        return _orig_create_event_takeoff(self, EventTime, Initiator)
    end
end

-- Collect the EWR / SAM-as-EWR group names the IADS generator published for a
-- coalition. SamAsEwr entries already carry the DCS GROUP name, but standalone
-- Ewr entries carry the UNIT name (Skynet convention: dcs_name_for_group
-- returns unit_name for EWR/CC roles). SET_GROUP filters by group name, so we
-- resolve unit names to their parent group via UNIT:FindByName → GetGroup.
local function ewr_group_names(coalition_name)
    local names = {}
    local seen = {}
    local iads = dcsRetribution.IADS and dcsRetribution.IADS[coalition_name]
    if iads then
        for _, role in ipairs({ "Ewr", "SamAsEwr" }) do
            local list = iads[role]
            if list then
                for _, node in pairs(list) do
                    if node.dcsGroupName then
                        local group_name = node.dcsGroupName
                        local grp = GROUP:FindByName(group_name)
                        if not grp then
                            local unit = UNIT:FindByName(group_name)
                            if unit then
                                local parent = unit:GetGroup()
                                if parent then
                                    group_name = parent:GetName()
                                end
                            end
                        end
                        if not seen[group_name] then
                            seen[group_name] = true
                            names[#names + 1] = group_name
                        end
                    end
                end
            end
        end
    end
    return names
end

-- Make the backstop EWR invisible to enemy AI and immortal so the backstop
-- cannot be shot out. Deferred a few seconds so Moose has registered the
-- freshly spawned group.
local function protect_group(group_name)
    mist.scheduleFunction(function()
        local grp = GROUP:FindByName(group_name)
        if grp then
            grp:SetCommandInvisible(true)
            grp:SetCommandImmortal(true)
        end
    end, {}, timer.getTime() + 5)
end

-- Attempts to spawn a hidden backstop EWR. Returns true when a spawn was issued
-- (a valid type and country were supplied); the caller still verifies the group
-- actually exists before relying on it, since mist.dynAdd drops unknown types.
local function spawn_backstop_ewr(group_name, vec2, ewr_type, country_id)
    if not ewr_type or ewr_type == "" or not country_id then
        return false
    end
    mist.dynAdd({
        countryId = country_id,
        category = "vehicle",
        groupName = group_name,
        hidden = true,
        units = {
            {
                type = ewr_type,
                x = vec2.x,
                y = vec2.y,
                heading = 0,
                skill = "Excellent",
                name = group_name .. " radar",
            },
        },
    })
    protect_group(group_name)
    return true
end

local function build_dispatcher(coalition_name, records)
    if #records == 0 then return end

    -- Global QRA tuning, identical across this coalition's records (see header).
    local comms_enabled = records[1].commsEnabled ~= "false"
    local scramble_radius_nm = tonumber(records[1].gciMaxRadiusNm) or 100
    local engagement_range_nm = tonumber(records[1].engagementRangeNm) or 60

    -- Always spawn a hidden backstop EWR at each defended base so there is a
    -- guaranteed detection source even when the IADS network is destroyed.
    -- This is independent of GciRadius — the backstop ensures detection, while
    -- GciRadius (set below) controls how far out a raid triggers a scramble.
    local backstop_names = {}
    do
        local seen_bases = {}
        for _, rec in ipairs(records) do
            local base_name = rec.airbaseName
            if not seen_bases[base_name] then
                seen_bases[base_name] = true
                local airbase = AIRBASE:FindByName(base_name)
                if airbase then
                    local vec2 = airbase:GetVec2()
                    local ewr_name = "QRA_Backstop_" .. coalition_name .. "_" .. base_name
                    if spawn_backstop_ewr(ewr_name, vec2, rec.backstopEwrType, tonumber(rec.countryId)) then
                        backstop_names[#backstop_names + 1] = ewr_name
                    end
                end
            end
        end
    end

    -- Assemble the dispatcher once the backstop groups have registered.
    mist.scheduleFunction(function()
        local detection_prefixes = ewr_group_names(coalition_name)
        for _, ewr_name in ipairs(backstop_names) do
            if GROUP:FindByName(ewr_name) then
                detection_prefixes[#detection_prefixes + 1] = ewr_name
            else
                env.info("DCSRetribution|Intercept: backstop EWR '"..ewr_name
                         .."' did not spawn (unknown type?); base falls back to EWR network.")
            end
        end

        if #detection_prefixes == 0 then
            env.info("DCSRetribution|Intercept: no detection sources for "
                     ..coalition_name.."; QRA will not scramble.")
            return
        end

        local det_set = SET_GROUP:New()
            :FilterCoalitions(string.lower(coalition_name))
            :FilterPrefixes(detection_prefixes)
            :FilterStart()

        local detection = DETECTION_AREAS:New(det_set, DETECTION_GROUPING_M)

        local dispatcher = AI_A2A_DISPATCHER:New(detection)
        -- Spawn interceptors already airborne near the base. See header for the
        -- full method history: every ground spawn (cold/hot/runway) leaves F-16s
        -- stuck on congested ramps like Tiyas; only in-air escapes it. In-air is
        -- viable here because the BASE.CreateEventTakeoff monkeypatch above fixes
        -- the Moose air-spawn crash that previously killed it. Altitude is metres.
        dispatcher:SetDefaultTakeoffInAir()
        dispatcher:SetDefaultTakeoffInAirAltitude(QRA_SPAWN_ALTITUDE_M)
        dispatcher:SetDefaultLandingAtEngineShutdown()
        dispatcher:SetIntercept(0)
        dispatcher:SetEngageRadius(engagement_range_nm * NM)
        dispatcher:SetTacticalDisplay(false)
        dispatcher:SetGciRadius(scramble_radius_nm * NM)
        dispatcher:SetSendMessages(false)
        local base_resource_activate = dispatcher.ResourceActivate

        function dispatcher:ResourceActivate(DefenderSquadron, DefendersNeeded)
            local defender, grouping = base_resource_activate(
                self, DefenderSquadron, DefendersNeeded
            )
            if comms_enabled and defender then
                local defender_name = defender:GetName()
                if defender_name and not qra_announced_groups[coalition_name][defender_name] then
                    qra_announced_groups[coalition_name][defender_name] = true
                    env.info("DCSRetribution|Intercept: "..coalition_name
                             .." QRA group launched: "..defender_name)
                    trigger.action.outText(
                        "GCI: "..coalition_name.." interceptors launched.", 10
                    )
                end
            end
            return defender, grouping
        end

        for _, rec in ipairs(records) do
            -- Moose keys squadrons by name; the squadron display name is not
            -- unique across bases (dr-wz6p), so append a short slice of the
            -- unique squadron id to avoid one base's QRA overwriting another's.
            local sq = rec.squadronName .. " #" .. string.sub(tostring(rec.squadronId), 1, 8)
            dispatcher:SetSquadron(sq, rec.airbaseName, { rec.templatePrefix }, tonumber(rec.resourceCount))
            dispatcher:SetSquadronGci2(
                sq, 900, 1200, QRA_ENGAGE_FLOOR_M, QRA_ENGAGE_CEILING_M, "BARO"
            )
            dispatcher:SetSquadronGrouping(sq, 2)
            -- NOTE: deliberately NOT SetSquadronVisible — see header. Visible mode
            -- forces a cold pre-park (F-16 never taxis), clamps reserve to parking
            -- spots, and forces Grouping=1. Non-visible = in-air fresh-spawn on scramble.
            intercept_survivors[rec.squadronId] = tonumber(rec.resourceCount)

            intercept_registry[rec.squadronId] = {
                dispatcher    = dispatcher,
                squadronName  = sq,
            }
        end
    end, {}, timer.getTime() + BUILD_DELAY)
end

-- ---------------------------------------------------------------------------
-- Survivor refresh
-- Formula: survivors(squadron) = parked ResourceCount
--                              + sum of GetSize() for each airborne Defender
--                                whose SquadronName matches.
--
-- GetSquadron throws on unknown name — we pcall it.
-- GetSize() returns nil when the GROUP has no DCS object; treat nil as 0.
-- DefenderTasks is keyed by Defender GROUP object; we iterate pairs() and
-- call GetDefenderTaskSquadronName(Defender) to match the squadron.
-- ---------------------------------------------------------------------------
local REFRESH_INTERVAL = 30  -- seconds between polls

local function refresh_survivors()
    for squadron_id, entry in pairs(intercept_registry) do
        local ok, err = pcall(function()
            local disp = entry.dispatcher
            local sq_name = entry.squadronName

            -- Parked count
            local parked = 0
            local sq_ok, sq_obj = pcall(function()
                return disp:GetSquadron(sq_name)
            end)
            if sq_ok and sq_obj and sq_obj.ResourceCount then
                parked = sq_obj.ResourceCount
            else
                -- GetSquadron threw or ResourceCount nil: keep last known value
                return
            end

            -- Airborne count: sum GetSize() for alive Defender groups in this squadron
            local airborne = 0
            local tasks = disp:GetDefenderTasks()
            for defender, _ in pairs(tasks) do
                local task_sq_name = disp:GetDefenderTaskSquadronName(defender)
                if task_sq_name == sq_name then
                    local sz = defender:GetSize()
                    if sz then
                        airborne = airborne + sz
                    end
                end
            end

            local survivors = math.max(0, parked + airborne)
            intercept_survivors[squadron_id] = survivors
        end)
        if not ok then
            env.info("DCSRetribution|Intercept: survivor refresh error for squadron "
                     ..tostring(squadron_id)..": "..tostring(err))
            -- keep last known value; do not write nil
        end
    end

    -- Self-reschedule (one-shot mist pattern, same as write_state_error_handling)
    mist.scheduleFunction(refresh_survivors, {}, timer.getTime() + REFRESH_INTERVAL)
end

if dcsRetribution.Intercept then
    local blue = dcsRetribution.Intercept.BLUE or {}
    local red = dcsRetribution.Intercept.RED or {}
    build_dispatcher("BLUE", blue)
    build_dispatcher("RED", red)

    -- The registry is populated by the deferred build (BUILD_DELAY in); start the
    -- survivor poll well after that and after the dispatcher FSM auto-start.
    if #blue > 0 or #red > 0 then
        mist.scheduleFunction(refresh_survivors, {}, timer.getTime() + 15)
    end
end
