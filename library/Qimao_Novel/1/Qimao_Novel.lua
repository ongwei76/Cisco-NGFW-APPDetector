-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: Qimao_Novel
-- Source process: Android com.kmxs.reader
-- Samples: 45
-- Generated: 2026-11-15T05:25:04+00:00
-- Generator: ngfw-appdetector v1.1.1

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "Qimao_Novel",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "api-cfg.wtzw.com",
    "api-gw.wtzw.com",
    "update.wtzw.com",
    "drs.wtzw.com",
    "cgcr.wtzw.com",
    "xiaoshuo.wtzw.com",
    "inf-cdn.wtzw.com",
    "abtest.wtzw.com",
    "mkt.wtzw.com",
    "api-ks.wtzw.com",
    "api-cmnt.wtzw.com",
    "api-bc.wtzw.com",
    "cdn-new-ad.wtzw.com",
    "t-cfg.wtzw.com",
    "api.wtzw.com",
    "api-nps.wtzw.com",
    "drs-ipv6.wtzw.com",
    "wtzw.com",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("Qimao_Novel")

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
