-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: Ximalaya
-- Source process: Android com.ximalaya.ting.android
-- Samples: 87
-- Generated: 2026-11-15T05:04:01+00:00
-- Generator: ngfw-appdetector v1.1.1

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "Ximalaya",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "mobile.ximalaya.com",
    "adse.ximalaya.com",
    "mobwsa.ximalaya.com",
    "adse.wsa.ximalaya.com",
    "xuid-server.ximalaya.com",
    "xmadsdk.cos.tx.xmcdn.com",
    "passportws.ximalaya.com",
    "ximalaya.com",
    "xmcdn.com",
    "mermaid.ximalaya.com",
    "xdcs-collector.ximalaya.com",
    "gslbali.ximalaya.com",
    "mres.ximalaya.com",
    "m.ximalaya.com",
    "search.test.ximalaya.com",
    "nativedl.pcdn.xmcdn.com",
    "gslbtx.ximalaya.com",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("Ximalaya")

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
