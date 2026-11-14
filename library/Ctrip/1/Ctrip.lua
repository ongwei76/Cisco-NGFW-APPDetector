-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: Ctrip
-- Source process: Android ctrip.android.view
-- Samples: 54
-- Generated: 2026-11-14T14:59:09+00:00
-- Generator: ngfw-appdetector v1.1.1

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "Ctrip",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "ak-d.tripcdn.cn",
    "download2.ctrip.com",
    "pages.c-ctrip.com",
    "m.ctrip.com",
    "s.c-ctrip.com",
    "dimg04.c-ctrip.com",
    "docs.c-ctrip.com",
    "video.c-ctrip.com",
    "ubtlog.ctrip.com",
    "aw-p.tripcdn.cn",
    "ctrip.com",
    "c-ctrip.com",
    "tripcdn.cn",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("Ctrip")

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
