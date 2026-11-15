-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: Zuoyebang
-- Source process: Android com.baidu.homework
-- Samples: 87
-- Generated: 2026-11-15T08:37:34+00:00
-- Generator: ngfw-appdetector v1.1.1

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "Zuoyebang",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "app-search.cdnjtzy.com",
    "pharos.zuoyebang.com",
    "zyb-na-static.cdnjtzy.com",
    "sanxia-platform.cdnjtzy.com",
    "zyb-vip.cdnjtzy.com",
    "nlogtf.zuoyebang.com",
    "zyb-na-static-1.cdnjtzy.com",
    "zyb-stats.zuoyebang.cc",
    "napi.zybang.com",
    "fmp-notice.zybang.com",
    "cns.zuoyebang.com",
    "zpm-platform.cdnjtzy.com",
    "homeworkai.zuoyebang.com",
    "zyb.zuoyebang.com",
    "nlogtj.zuoyebang.cc",
    "apivip.zuoyebang.com",
    "zpm.zuoyebang.com",
    "pluto.zuoyebang.com",
    "yujie.zuoyebang.com",
    "stats.cdnjtzy.com",
    "syh-cube.cdnjtzy.com",
    "sanxia.zybang.com",
    "asr.cdnjtzy.com",
    "vip.cdnjtzy.com",
    "zuoyebang.com",
    "zybang.com",
    "cdnjtzy.com",
    "zuoyebang.cc",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("Zuoyebang")

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
