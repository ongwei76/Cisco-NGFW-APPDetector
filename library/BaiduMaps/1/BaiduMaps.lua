-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: BaiduMaps
-- Source process: Android com.baidu.BaiduMap
-- Samples: 33
-- Generated: 2026-11-14T14:33:11+00:00
-- Generator: ngfw-appdetector v1.1.1

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "BaiduMaps",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "newclient.map.baidu.com",
    "cnloc.map.baidu.com",
    "ofloc.map.baidu.com",
    "daup.map.baidu.com",
    "websocket.map.baidu.com",
    "map-mobile-resource.cdn.bcebos.com",
    "ecom.map.baidu.com",
    "map-growth.bj.bcebos.com",
    "client.map.baidu.com",
    "map-component.cdn.bcebos.com",
    "map-mobile-opnimg.cdn.bcebos.com",
    "blg.map.baidu.com",
    "map.baidu.com",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("BaiduMaps")

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
