-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: Tongcheng
-- Source process: Android com.tongcheng.android
-- Samples: 82
-- Generated: 2026-11-15T07:46:42+00:00
-- Generator: ngfw-appdetector v1.1.1

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "Tongcheng",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "tcmobileapi.17usoft.com",
    "vstlog.17usoft.com",
    "mobile-api2011.elong.com",
    "wx.17u.cn",
    "dune.17usoft.com",
    "xapitxy.elong.com",
    "wxakamai.17u.cn",
    "savior.elong.com",
    "vstlog-ipv4.17usoft.com",
    "quic-hotel.17u.cn",
    "xapiidc1.elong.com",
    "quic-hotelhuo.17u.cn",
    "xapiidc2.elong.com",
    "wxeu.17u.cn",
    "xapi.elong.com",
    "hotelap.17u.cn",
    "xapiali.elong.com",
    "pic5.40017.cn",
    "wxap.17u.cn",
    "wxws.17u.cn",
    "cvg.17usoft.com",
    "oauth.elong.com",
    "dtgw.ly.com",
    "app.ly.com",
    "17u.cn",
    "17usoft.com",
    "40017.cn",
    "elong.com",
    "ly.com",
    "file.40017.cn",
    "privacy-policy-w.elong.com",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("Tongcheng")

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
