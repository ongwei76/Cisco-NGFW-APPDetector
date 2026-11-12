-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: Eleme
-- Source process: Android me.ele
-- Samples: 12
-- Generated: 2026-11-12T19:01:21+00:00
-- Generator: ngfw-appdetector v1.1.1

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "Eleme",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "zconfig.elemecdn.com",
    "h-adashx.ut.ele.me",
    "cube.elemecdn.com",
    "tb.ele.me",
    "nr-op.elemecdn.com",
    "restapi.ele.me",
    "highway-tb.ele.me",
    "mtop.ele.me",
    "ele.me",
    "elemecdn.com",
    "amdc.m.ele.me",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("Eleme")

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
