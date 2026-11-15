-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: BOSS_Zhipin
-- Source process: Android com.hpbr.bosszhipin
-- Samples: 43
-- Generated: 2026-11-15T07:26:46+00:00
-- Generator: ngfw-appdetector v1.1.1

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "BOSS_Zhipin",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "z.zhipin.com",
    "apm-fe.zhipin.com",
    "apm-and.zhipin.com",
    "shink.zhipin.com",
    "api5.zhipin.com",
    "m.zhipin.com",
    "static.zhipin.com",
    "logapi-and.zhipin.com",
    "uni-shumeng.zhipin.com",
    "zhipin.com",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("BOSS_Zhipin")

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
