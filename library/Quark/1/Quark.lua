-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: Quark
-- Source process: Android com.quark.browser
-- Samples: 46
-- Generated: 2026-11-14T14:33:11+00:00
-- Generator: ngfw-appdetector v1.1.1

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "Quark",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "px.wpk.quark.cn",
    "adtrack.quark.cn",
    "track.lc.quark.cn",
    "applog.lc.quark.cn",
    "quark.cn",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("Quark")

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
