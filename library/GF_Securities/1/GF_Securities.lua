-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: GF_Securities
-- Source process: GF-Trader.exe
-- Samples: 78
-- Generated: 2026-11-10T15:36:34+00:00
-- Generator: ngfw-appdetector v1.1.0

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "GF_Securities",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "bayberry.gf.com.cn",
    "hippo.gf.com.cn",
    "cdn.gfzq.cn",
    "report.gf.com.cn",
    "behavior.gf.com.cn",
    "pnsclient.gf.com.cn",
    "info.gf.com.cn",
    "zphippo3.gfzq.cn",
    "mchippo3v6.gf.com.cn",
    "zphippo3.gf.com.cn",
    "mchippo3.gf.com.cn",
    "bjhippo3.gf.com.cn",
    "bjhippo3.gfzq.cn",
    "mchippo3.gfzq.cn",
    "kxchippo3v6.gf.com.cn",
    "kxchippo3.gf.com.cn",
    "kxchippo3.gfzq.cn",
    "gf.com.cn",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("GF_Securities")

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
