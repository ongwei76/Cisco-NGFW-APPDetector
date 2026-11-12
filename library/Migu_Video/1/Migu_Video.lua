-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: Migu_Video
-- Source process: MiGuApp.exe
-- Samples: 22
-- Generated: 2026-11-12T04:00:27+00:00
-- Generator: ngfw-appdetector v1.1.0

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "Migu_Video",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "webapi.miguvideo.com",
    "pc.miguvideo.com",
    "miguvideo.com",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("Migu_Video")

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
