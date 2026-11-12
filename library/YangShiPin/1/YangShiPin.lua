-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: YangShiPin
-- Source process: firefox.exe
-- Samples: 200
-- Generated: 2026-11-12T04:18:58+00:00
-- Generator: ngfw-appdetector v1.1.0

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "YangShiPin",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "m.yangshipin.cn",
    "sapi.yangshipin.cn",
    "s.yangshipin.cn",
    "www.yangshipin.cn",
    "btrace.yangshipin.cn",
    "resources.yangshipin.cn",
    "cover.yangshipin.cn",
    "img.yangshipin.cn",
    "capi.yangshipin.cn",
    "csapi.yangshipin.cn",
    "h5access.yangshipin.cn",
    "wimg.yangshipin.cn",
    "player-api.yangshipin.cn",
    "aatc-api.yangshipin.cn",
    "pic.yangshipin.cn",
    "ucenter-api.yangshipin.cn",
    "jietufengmian.yangshipin.cn",
    "mpuser.ysp.cctv.cn",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("YangShiPin")

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
