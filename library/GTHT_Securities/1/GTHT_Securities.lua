-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: GTHT_Securities
-- Source process: AutoDown.exe
-- Samples: 6
-- Generated: 2026-11-10T14:25:10+00:00
-- Generator: ngfw-appdetector v1.1.0

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "GTHT_Securities",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "newdsj.gtjadev.com",
    "fqlapi.gtja.com",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("GTHT_Securities")

    if gDetector.addSSLCertPattern then
        for _, host in ipairs(gHostPatternList) do
            gDetector:addSSLCertPattern(0, gAppId, host)
        end
    end

    if gDetector.addSSLCnamePattern then
        for _, host in ipairs(gHostPatternList) do
            gDetector:addSSLCnamePattern(0, gAppId, host)
        end
    end

    if gDetector.addAppUrl then
        for _, host in ipairs(gHostPatternList) do
            gDetector:addAppUrl(0, 0, 0, gAppId, 0, host, "/", "http:", "", gAppId)
        end
    end

    return gDetector
end

function DetectorClean()
end
