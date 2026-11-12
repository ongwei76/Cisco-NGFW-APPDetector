-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: DiDi
-- Source process: Android com.sdu.didi.psnger
-- Samples: 72
-- Generated: 2026-11-12T19:01:20+00:00
-- Generator: ngfw-appdetector v1.1.1

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "DiDi",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "as.xiaojukeji.com",
    "poi.map.xiaojukeji.com",
    "conf.diditaxi.com.cn",
    "hd.xiaojukeji.com",
    "star.xiaojukeji.com",
    "dpubstatic.udache.com",
    "omgup.xiaojukeji.com",
    "api.didi.cn",
    "img-hxy021.didistatic.com",
    "s3-gz01.didistatic.com",
    "res.xiaojukeji.com",
    "api.udache.com",
    "security.xiaojukeji.com",
    "catchdata.xiaojukeji.com",
    "thanos.xiaojukeji.com",
    "smart-engine.xiaojukeji.com",
    "epassport.diditaxi.com.cn",
    "ct.xiaojukeji.com",
    "s3-hnapuhdd-cdn.didistatic.com",
    "guard.sec.xiaojukeji.com",
    "img-ys011.didistatic.com",
    "apm.xiaojukeji.com",
    "common.diditaxi.com.cn",
    "trafficrenderapi.map.xiaojukeji.com",
    "didi.cn",
    "xiaojukeji.com",
    "diditaxi.com.cn",
    "didistatic.com",
    "udache.com",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("DiDi")

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
