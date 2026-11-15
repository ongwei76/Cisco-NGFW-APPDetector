-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: JJ_Doudizhu
-- Source process: Android cn.jj
-- Samples: 11
-- Generated: 2026-11-15T14:15:00+00:00
-- Generator: ngfw-appdetector v1.1.1

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "JJ_Doudizhu",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "pdc-api.m.jj.cn",
    "aetcontrol.srv.jj.cn",
    "aetcollector.srv.jjmatch.cn",
    "feed.srv.jj.cn",
    "pdc-confcenter.m.jj.cn",
    "jj.cn",
    "jjmatch.cn",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("JJ_Doudizhu")

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
