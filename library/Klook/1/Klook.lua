-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: Klook
-- Source process: Android com.klook
-- Samples: 50
-- Generated: 2026-11-17T14:39:45+00:00
-- Generator: ngfw-appdetector v1.2.0

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "Klook",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "appapi.klook.com",
    "res.klook.com",
    "sentry.klook.com",
    "log.klook.com",
    "klook.com",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("Klook")

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
