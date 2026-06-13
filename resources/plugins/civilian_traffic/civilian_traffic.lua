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

local mgr = RATMANAGER:New(10)
mgr:Add(r, 6)

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
end

mgr:Start(30)
