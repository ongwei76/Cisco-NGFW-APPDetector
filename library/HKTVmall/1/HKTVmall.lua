-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: HKTVmall
-- Source process: Android com.hktv.android.hktvmall
-- Samples: 45
-- Generated: 2026-11-17T16:00:47+00:00
-- Generator: ngfw-appdetector v1.2.0

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "HKTVmall",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "www.hktvmall.com",
    "cdn-media.hktvmall.com",
    "api.takeaway.hktvmall.com",
    "images.hktvmall.com",
    "hss.hktvmall.com",
    "push-api-v2.hktvmall.com",
    "live-api.hktvmall.com",
    "apps.hktvmall.com",
    "ads.hktvmall.com",
    "ad-splash.hktvmall.com",
    "hktvmall.com",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("HKTVmall")

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
