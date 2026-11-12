-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: Pinduoduo
-- Source process: Android com.xunmeng.pinduoduo
-- Samples: 119
-- Generated: 2026-11-12T19:01:21+00:00
-- Generator: ngfw-appdetector v1.1.1

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "Pinduoduo",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "apm-a.pinduoduo.com",
    "meta.pinduoduo.com",
    "commimg-2.pddpic.com",
    "cdl.pddpic.com",
    "api.pinduoduo.com",
    "img-3.pddpic.com",
    "promotion-2.pddpic.com",
    "funimg-2.pddpic.com",
    "th-a.pinduoduo.com",
    "funimg-1.pddpic.com",
    "img-2.pddpic.com",
    "cd.pddpic.com",
    "mcdn.yangkeduo.com",
    "cfg-2.pddpic.com",
    "funimg.pddpic.com",
    "promotion-1.pddpic.com",
    "cdl-1.pddpic.com",
    "pinduoduo.com",
    "pddpic.com",
    "yangkeduo.com",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("Pinduoduo")

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
