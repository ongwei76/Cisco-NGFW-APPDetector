-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: KKBOX_Mobile
-- Source process: Android com.skysoft.kkbox.android
-- Samples: 14
-- Generated: 2026-11-17T14:11:09+00:00
-- Generator: ngfw-appdetector v1.2.0

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "KKBOX_Mobile",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "a.kfs.io",
    "kkid.kkbox.com",
    "api-login-relay.kkbox.com.tw",
    "api-login.kkbox.com.tw",
    "kkbox.com",
    "kfs.io",
    "kkbox.com.tw",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("KKBOX_Mobile")

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
