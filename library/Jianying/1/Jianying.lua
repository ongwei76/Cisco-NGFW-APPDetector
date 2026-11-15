-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: Jianying
-- Source process: Android com.lemon.lv
-- Samples: 23
-- Generated: 2026-11-15T05:04:01+00:00
-- Generator: ngfw-appdetector v1.1.1

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "Jianying",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "lv-api.ulikecam.com",
    "commerce-api.faceu.mobi",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("Jianying")

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
