-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: UC_Browser
-- Source process: Android com.UCMobile
-- Samples: 11
-- Generated: 2026-11-14T16:07:23+00:00
-- Generator: ngfw-appdetector v1.1.1

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "UC_Browser",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "adtrack.ucweb.com",
    "ucdc2-upaas.uc.cn",
    "track.uc.cn",
    "uc-ai-applet.uc.cn",
    "cms.uc.cn",
    "unpm-upaas.uc.cn",
    "up4.ucweb.com",
    "hp-cms-uc.uc.cn",
    "ucus.ucweb.com",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("UC_Browser")

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
