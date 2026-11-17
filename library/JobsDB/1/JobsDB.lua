-- Auto-generated Cisco Secure Firewall custom application detector.
-- App: JobsDB
-- Source process: Android com.jobsdb
-- Samples: 5
-- Generated: 2026-11-17T16:35:19+00:00
-- Generator: ngfw-appdetector v1.2.0

require "DetectorCommon"

local DC = DetectorCommon

DetectorPackageInfo = {
    name = "JobsDB",
    proto = DC.ipproto.tcp,
    client = {
        init = "DetectorInit",
        clean = "DetectorClean",
        minimum_matches = 1
    }
}

gHostPatternList = {
    "au.seek.com",
    "login.seek.com",
    "seekcdn.com",
    "seek.com",
}

function DetectorInit(detectorInstance)
    gDetector = detectorInstance
    gAppId = gDetector:open_createApp("JobsDB")

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
