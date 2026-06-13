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
    if not _excl[name] and ab:getCoalition() == coalition.side.NEUTRAL then
        _neutral_pool[#_neutral_pool + 1] = name
    end
end

local r = RAT:New("RAT_CIVILIAN")
r:SetDeparture(_neutral_pool)
r:SetDestination(_neutral_pool)
r:SetMinDistance(280)
r:SetMaxDistance(370)
r:SetTakeoff("hot")
r:SetTerminalType(AIRBASE.TerminalType.OpenBig)
r:SetROE("hold")
r:SetROT("evade")
r:Invisible()
r:RespawnAfterLanding(90)

local mgr = RATMANAGER:New(10)
mgr:Add(r, 3)
mgr:Start(30)
