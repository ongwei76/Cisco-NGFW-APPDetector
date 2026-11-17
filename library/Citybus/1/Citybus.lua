-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: Citybus
-- Source process: Android com.nwfb
-- Samples: 26
-- Generated: 2026-11-17T15:20:19+00:00
-- Generator: ngfw-appdetector v1.2.0

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "Citybus",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "mobile08.citybus.com.hk",
    "mobile09.citybus.com.hk",
    "mobilelb.citybus.com.hk",
    "mobileadmin.citybus.com.hk",
    "mobile07.citybus.com.hk",
    "mobile.citybus.com.hk",
    "mobilea.citybus.com.hk",
    "www.citybus.com.hk",
    "citybus.com.hk",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("Citybus")

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
