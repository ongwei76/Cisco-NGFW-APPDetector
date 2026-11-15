-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: Huya
-- Source process: Android com.duowan.kiwi
-- Samples: 26
-- Generated: 2026-11-15T08:17:48+00:00
-- Generator: ngfw-appdetector v1.1.1

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "Huya",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "cdn.wup.huya.com",
    "cdnws.api.huya.com",
    "business.msstatic.com",
    "diy-front.cdn.huya.com",
    "wsapi.huya.com",
    "ylog.huya.com",
    "wup.huya.com",
    "wswup.cdn.huya.com",
    "huya.com",
    "msstatic.com",
    "statwup.huya.com",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("Huya")

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
