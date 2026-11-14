-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: Fanqie_Hongguo
-- Source process: Android com.phoenix.read
-- Samples: 8
-- Generated: 2026-11-14T17:12:10+00:00
-- Generator: ngfw-appdetector v1.1.1

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "Fanqie_Hongguo",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "lf3-reading.fqnovelpic.com",
    "mon11-misc.fqnovel.com",
    "api5-normal.fqnovel.com",
    "lf3-reading.fqnovelstatic.com",
    "log5-applog.fqnovel.com",
    "fqnovel.com",
    "fqnovelpic.com",
    "fqnovelstatic.com",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("Fanqie_Hongguo")

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
