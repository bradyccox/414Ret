-- Civilian background air traffic injected by the 414Ret civilian_traffic plugin.
-- Do not edit in the Mission Editor. Edit the plugin source in 414Ret instead.
--
-- _CIVILIAN_TRAFFIC_EXCL is a Lua array of DCS airbase names baked in by the
-- Python preamble before this file loads. It contains every airbase Retribution
-- has assigned to combat operations this turn. The script enumerates all remaining
-- airbases on the map at runtime so it works on any terrain without modification.
--
-- Only NEUTRAL-coalition airbases are used as the civilian pool. RED/BLUE airbases
-- are military (even if Retribution doesn't use them this turn) and are excluded.

local _excl = {}
for _, b in ipairs(_CIVILIAN_TRAFFIC_EXCL) do
    _excl[b] = true
end

local _neutral_pool = {}
for _, ab in pairs(world.getAirbases()) do
    local name = ab:getName()
    local desc = ab:getDesc()
    if not _excl[name]
        and ab:getCoalition() == coalition.side.NEUTRAL
        and desc and desc.category == Airbase.Category.AIRDROME
    then
        _neutral_pool[#_neutral_pool + 1] = name
    end
end

local _blue_pool = {}
for _, ab in pairs(world.getAirbases()) do
    local desc = ab:getDesc()
    if ab:getCoalition() == coalition.side.BLUE
        and desc and desc.category == Airbase.Category.AIRDROME
    then
        _blue_pool[#_blue_pool + 1] = ab:getName()
    end
end

local mgr = RATMANAGER:New(10)
local _rats_added = 0

-- Civilian traffic only routes through NEUTRAL airdromes. With an empty (or
-- single-airport) neutral pool, MOOSE RAT silently falls back to spawning at
-- ALL map airbases -- including heliports/FARPs, where fixed-wing jets cannot
-- taxi and so sit motionless. Require at least two airdromes before fielding
-- the civilian flight, mirroring the blue-pool guard below.
if #_neutral_pool >= 2 then
    local r = RAT:New("RAT_CIVILIAN")
    r:SetDeparture(_neutral_pool)
    r:SetDestination(_neutral_pool)
    r:SetMinDistance(80)
    r:SetMaxDistance(350)
    r:SetTakeoff("hot")
    r:SetROE("hold")
    r:SetROT("evade")
    r:Invisible()
    r:RespawnAfterLanding(90)
    mgr:Add(r, 6)
    _rats_added = _rats_added + 1
end

if #_blue_pool >= 2 then
    local rb = RAT:New("RAT_BLUE")
    rb:SetDeparture(_blue_pool)
    rb:SetDestination(_blue_pool)
    rb:SetMinDistance(50)
    rb:SetMaxDistance(350)
    rb:SetTakeoff("hot")
    rb:SetROE("hold")
    rb:SetROT("evade")
    rb:Invisible()
    rb:RespawnAfterLanding(90)
    mgr:Add(rb, 4)
    _rats_added = _rats_added + 1
end

-- Only start the manager if at least one valid airdrome pool produced a flight;
-- starting an empty RATMANAGER is pointless and can error.
if _rats_added > 0 then
    mgr:Start(30)
end
