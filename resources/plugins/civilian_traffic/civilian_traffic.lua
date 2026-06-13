-- Civilian background air traffic injected by the 414Ret civilian_traffic plugin.
-- Do not edit in the Mission Editor. Edit the plugin source in 414Ret instead.
--
-- _CIVILIAN_TRAFFIC_EXCL is a Lua array of DCS airbase names baked in by the
-- Python preamble before this file loads. It contains every airbase Retribution
-- has assigned to combat operations this turn. The script enumerates all remaining
-- airbases on the map at runtime so it works on any terrain without modification.

local _excl = {}
for _, b in ipairs(_CIVILIAN_TRAFFIC_EXCL) do
    _excl[b] = true
end

local _red_pool, _blue_pool = {}, {}
for _, ab in pairs(world.getAirbases()) do
    local name = ab:getName()
    if not _excl[name] then
        local side = ab:getCoalition()
        if side == coalition.side.RED then
            _red_pool[#_red_pool + 1] = name
        elseif side == coalition.side.BLUE then
            _blue_pool[#_blue_pool + 1] = name
        end
    end
end

local function setupRAT(templateName, pool)
    if #pool < 2 then return nil end
    local r = RAT:New(templateName)
    r:SetDeparture(pool)
    r:SetDestination(pool)
    r:SetMinDistance(280)
    r:SetMaxDistance(370)
    r:SetTakeoff("hot")
    r:SetTerminalType(AIRBASE.TerminalType.OpenBig)
    r:SetROE("hold")
    r:SetROT("evade")
    r:Invisible()
    r:RespawnAfterLanding(90)
    return r
end

local ratRed  = setupRAT("RAT_CIVILIAN_RED",  _red_pool)
local ratBlue = setupRAT("RAT_CIVILIAN_BLUE", _blue_pool)

local mgr = RATMANAGER:New(10)
if ratRed  then mgr:Add(ratRed,  3) end
if ratBlue then mgr:Add(ratBlue, 3) end
mgr:Start(30)
