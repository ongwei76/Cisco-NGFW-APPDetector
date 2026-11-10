--[[
  Auto-generated Cisco NGFW OpenAppID detector
  App:            CMS_Securities
  Source process: TdxW.exe
  Samples:        18
  Generated:      2026-10-29T11:10:42+00:00
  Generator:      ngfw-appdetector v1.0.0

  REVIEW BEFORE IMPORT. This file is a starting template; check for false
  positives, especially against shared CDNs and OS-wide services.
  Reference: https://www.cisco.com/c/en/us/td/docs/security/firepower/openappid/
]]--

require "DetectorCommon"

local DC    = DetectorCommon
local proto = DC.ipproto.tcp

DetectorPackageInfo = {
    name      = "CMS_Securities",
    proto     = proto,
    client = {
        init            = 'DetectorInit',
        clean           = 'DetectorClean',
        validate        = 'DetectorValidator',
        minimum_matches = 1,
    }
}

-- Application IDs ¡ª replace with real IDs assigned by FMC after first import.
local gAppId        = 9000
local gAppIdService = 9001

-- ©¤©¤©¤ Match tables ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤
local gTlsExactHosts = {
    "xg.cmschina.com",
    "appstatic.cmschina.com",
    "zszx.cmschina.com",
    "apprzfx.cmschina.com",
}

local gTlsCertCNs = {
}

local gTlsHostSuffixes = {     -- matched as ".example.com"-style suffix
    ".cmschina.com",
}

local gHttpHosts = {
    "xg.cmschina.com",
    "appstatic.cmschina.com",
    "zszx.cmschina.com",
    "apprzfx.cmschina.com",
}

local gHttpUriPrefixes = {
}

local gPayloadHex = {           -- first-N client bytes (hex, lowercase)
}

-- Negative list: never claim ownership for these hostnames (shared infra etc.)
local gExcludedHosts = {
}

-- ©¤©¤©¤ Helpers ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤
local function hexToBytes(hex)
    local out = {}
    for i = 1, #hex, 2 do
        out[#out+1] = string.char(tonumber(hex:sub(i, i+1), 16))
    end
    return table.concat(out)
end

-- ©¤©¤©¤ Init ©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤©¤
function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gDetector:setDetectorPackageInfo(DetectorPackageInfo)

    -- TLS: exact SNI / cert CN
    for _, h in ipairs(gTlsExactHosts) do
        gDetector:addSSLCertPattern(0, h, gAppId)
        gDetector:addSSLCnamePattern(0, h, gAppId)
    end
    for _, h in ipairs(gTlsCertCNs) do
        gDetector:addSSLCertPattern(0, h, gAppId)
    end

    -- TLS: suffix patterns ("." + base domain)
    for _, suffix in ipairs(gTlsHostSuffixes) do
        gDetector:addSSLCnamePattern(0, suffix, gAppId)
    end

    -- HTTP host only. User-Agent and URI-only rules are intentionally ignored:
    -- both are too noisy to identify an application reliably.
    for _, h in ipairs(gHttpHosts) do
        gDetector:addHostPortApp(h, 0, gAppId)
    end

    -- Payload byte signatures (TCP)
    for _, hex in ipairs(gPayloadHex) do
        local bytes = hexToBytes(hex)
        gDetector:addPattern(0, bytes, #bytes, DC.dpdContext.SOURCE, gAppId)
    end

    return gDetector
end

function DetectorValidator()
    -- Hook point for additional in-flow validation; return DC.GS.NOMATCH to
    -- abort if the matched host happens to be in gExcludedHosts.
    if gDetector and gDetector.getHttpHost then
        local h = gDetector:getHttpHost()
        if h then
            for _, bad in ipairs(gExcludedHosts) do
                if h == bad then return DC.GS.NOMATCH end
            end
        end
    end
    return 0
end

function DetectorClean()
end
