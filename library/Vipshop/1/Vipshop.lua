-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: Vipshop
-- Source process: Android com.achievo.vipshop
-- Samples: 32
-- Generated: 2026-11-14T17:41:57+00:00
-- Generator: ngfw-appdetector v1.1.1

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "Vipshop",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "h2.appsimg.com",
    "h2.vipstatic.com",
    "mapi.appvipshop.com",
    "h2bak.appsimg.com",
    "app.vipstatic.com",
    "b.appsimg.com",
    "sc.appvipshop.com",
    "vcsp-api.vip.com",
    "sc-thor.vip.com",
    "member.vpal.com",
    "mp.appvipshop.com",
    "tfs-fp.vip.com",
    "mst.vip.com",
    "pkg.vipstatic.com",
    "appsimg.com",
    "vipstatic.com",
    "appvipshop.com",
    "vip.com",
    "vpal.com",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("Vipshop")

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
