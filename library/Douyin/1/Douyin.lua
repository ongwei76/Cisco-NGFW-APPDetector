-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: Douyin
-- Source process: douyin.exe
-- Samples: 166
-- Generated: 2026-11-12T04:05:08+00:00
-- Generator: ngfw-appdetector v1.1.0

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "Douyin",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "lf-douyin-pc-web.douyinstatic.com",
    "api.amemv.com",
    "live.douyin.com",
    "p3-pc.douyinpic.com",
    "www.douyin.com",
    "sf1-cdn-tos.douyinstatic.com",
    "p3-pc-sign.douyinpic.com",
    "p26-sign.douyinpic.com",
    "lf-zt.douyin.com",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("Douyin")

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
