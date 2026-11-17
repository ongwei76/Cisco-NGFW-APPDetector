-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: Futu_NiuNiu
-- Source process: Android cn.futu.trader
-- Samples: 38
-- Generated: 2026-11-17T15:20:18+00:00
-- Generator: ngfw-appdetector v1.2.0

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "Futu_NiuNiu",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "api.futunn.com",
    "collect.futunn.com",
    "conf.futunn.com",
    "event-config.futunn.com",
    "auth.futunn.com",
    "connscheduler.futunn.com",
    "futunn.com",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("Futu_NiuNiu")

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
