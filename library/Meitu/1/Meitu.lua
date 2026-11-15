-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: Meitu
-- Source process: Android com.mt.mtxx.mtxx
-- Samples: 67
-- Generated: 2026-11-15T04:42:55+00:00
-- Generator: ngfw-appdetector v1.1.1

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "Meitu",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "xxtool-release.zone1.meitudata.com",
    "api.account.meitu.com",
    "adui.tg.meitu.com",
    "vesdk.meitu.com",
    "mfa.meitudata.com",
    "api.data.meitu.com",
    "tool.xiuxiu.meitu.com",
    "push.meitu.com",
    "xiuxiu-im-route.meitu.com",
    "strategy.app.meitudata.com",
    "api.xiuxiu.meitu.com",
    "account.meitu.com",
    "mea.meitudata.com",
    "api-remote.meitu.com",
    "mtpush.meitu.com",
    "canvas.houyi.meitu.com",
    "api-sub.meitu.com",
    "openapi.mtlab.meitu.com",
    "public.zone1.meitudata.com",
    "rabbit.tg.meitu.com",
    "stat.meitudata.com",
    "api.posters.meitu.com",
    "captain.meitu.com",
    "font-tool.meitu.com",
    "meitu.com",
    "meitudata.com",
    "maavatar1.meitudata.com",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("Meitu")

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
