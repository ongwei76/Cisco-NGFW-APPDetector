-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: Keeta
-- Source process: Android com.sankuai.sailor.afooddelivery
-- Samples: 70
-- Generated: 2026-11-17T15:40:33+00:00
-- Generator: ngfw-appdetector v1.2.0

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "Keeta",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "catdot-eu.mykeeta.com",
    "i18n-eu.mykeeta.com",
    "h-eu.mykeeta.com",
    "sailfish-eu.mykeeta.com",
    "lbshark-eu.mykeeta.com",
    "mtpush.mykeeta.com",
    "s3-ap-hongkong.mykeeta.net",
    "p13-hk.d1.mykeeta.com",
    "pikachu.mykeeta.com",
    "fooddelivery-eu-1.mykeeta.com",
    "uuid-eu.mykeeta.com",
    "nwshark-eu.mykeeta.com",
    "fooddelivery-eu.mykeeta.com",
    "lx0-eu.mykeeta.com",
    "p2-hk.d1.mykeeta.com",
    "o3-hk.d1.mykeeta.com",
    "bd0-hk.d.mykeeta.com",
    "push-eu.mykeeta.com",
    "sailfish.mykeeta.com",
    "dd-eu.mykeeta.com",
    "p14-hk.d1.mykeeta.com",
    "s3-fra01-eu.mykeeta.net",
    "ddplus-eu.mykeeta.net",
    "imsailor-eu.mykeeta.com",
    "mykeeta.com",
    "mykeeta.net",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("Keeta")

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
