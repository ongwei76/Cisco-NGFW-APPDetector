-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: Anipop
-- Source process: Android com.happyelements.AndroidAnimal.qq
-- Samples: 17
-- Generated: 2026-11-15T14:00:50+00:00
-- Generator: ngfw-appdetector v1.1.1

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "Anipop",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "animalcdnstatic.happyelements.com",
    "logdc.happyelements.cn",
    "kxxxl.leyuansu.com",
    "m.happyelements.cn",
    "happyelements.com",
    "happyelements.cn",
    "mobile.app100718846.twsapp.com",
    "log.dc.cn.happyelements.com",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("Anipop")

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
