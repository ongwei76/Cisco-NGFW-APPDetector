-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: Arknights
-- Source process: Android com.hypergryph.arknights
-- Samples: 22
-- Generated: 2026-11-15T14:45:01+00:00
-- Generator: ngfw-appdetector v1.1.1

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "Arknights",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "event-log-api-data-lake-prod-cn.hypergryph.com",
    "web.hycdn.cn",
    "game-config.hypergryph.com",
    "ak.hycdn.cn",
    "eventlog-service.hypergryph.com",
    "launcher.hypergryph.com",
    "as.hypergryph.com",
    "ak-conf.hypergryph.com",
    "hypergryph.com",
    "hycdn.cn",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("Arknights")

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
