-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: Kuwo_Music
-- Source process: Android cn.kuwo.player
-- Samples: 162
-- Generated: 2026-11-14T17:51:53+00:00
-- Generator: ngfw-appdetector v1.1.1

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "Kuwo_Music",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "wapi.kuwo.cn",
    "mobilead.kuwo.cn",
    "integralapi.kuwo.cn",
    "g.kuwo.cn",
    "homepages.kuwo.cn",
    "vip1.kuwo.cn",
    "ipdomainserver.kuwo.cn",
    "star.kuwo.cn",
    "rich.kuwo.cn",
    "abt-kuwo.tencentmusic.com",
    "searchrecterm.kuwo.cn",
    "abapi.kuwo.cn",
    "musicpay.kuwo.cn",
    "tingshu.kuwo.cn",
    "kwpush.kuwo.cn",
    "appi.kuwo.cn",
    "webapi.kuwo.cn",
    "img-zb.kuwo.cn",
    "kuwo.cn",
    "log.kuwo.cn",
    "ar.i.kuwo.cn",
    "mobi.kuwo.cn",
    "down.shouji.kuwo.cn",
    "kweex.kuwo.cn",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("Kuwo_Music")

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
