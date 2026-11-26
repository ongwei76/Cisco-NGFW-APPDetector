# Upload method

**English** | [简体中文](upload-method.zh-CN.md)

The public FMC REST API has no endpoint for uploading custom Lua application detectors, so this tool reproduces the calls the FMC Web UI makes on **Policies → Application Detectors**. The sequence below was verified on **FMC 10.0.1 (build 1)**.

All requests are HTTPS requests to the FMC management address, not through a proxy, sharing one `CGISESSID` session cookie.

## 1. Login

| Step | Request | Notes |
|------|------|------|
| 1 | `GET /ui/login` | Open the login page |
| 2 | `POST /login.cgi` (form `username`, `password`) | Returns the `CGISESSID` cookie on success |
| 3 | `GET /ddd/` | Read `sf_action_id` (the per-session CSRF token) and the FMC version (`"fmcBuild":"10.0.1-1"`) from the page |

> The FMC version is read from the web page and the REST API `generatetoken` is **not** called: requesting a REST token with the same account was found to invalidate the current Web session, so later calls return empty data.

## 2. pjb.cgi call format

`POST /pjb.cgi`, form fields:

```
function       = SF::Cache::RNADetector::<function name>
parameters     = <JSON array>
get_all_errors = 1
sf_action_id   = <token from step 3 of login>
ss             = DetectorList or DetectorEditor
```

Response JSON: `{"data": ..., "error": ...}`. Empty `data` means the session was logged out (e.g. the same account logged in elsewhere); the tool logs in again once automatically for read-only calls.

## 3. Uploading one Lua

| Step | Function / request | Main parameters |
|------|-------------|----------|
| 1 | `getFilterList` `[]` | Existing app names (to detect duplicates) and categories (category name → tagId) |
| 2 | `saveApp` | `appName`, `appId:-1`, `risk_index`, `productivity_index`, `appDescription`, `categories:[{tagId, tagType:"category", tagName}]`; returns the new `appId` |
| 3 | `setDetector` `["new", null, {...}]` | `name`, `appId`, `protocol:"custom"`, `active:0`, `lua:0`; returns the detector `uuid` |
| 4 | `initDetectorEditorForAllApps` `[uuid]` | Opens the detector editor (`ss=DetectorEditor`) |
| 5 | `POST /RNADetector/detectors.cgi` (multipart) | `sf_action_id`, `detector_uuid`, file field `lua_upload`; returns `FILENAME=...!!SUCCESS=...` or `!!ERROR=<reason>` |
| 6 | `setDetector` `["save", uuid, {...}]` | `lua:1`, `subtype:5`, `active:0`; returns the saved Lua, which the tool compares with the upload (ignoring line-ending and non-ASCII differences) |

If any of steps 3–6 fails, `deleteDetectors [[uuid]]` rolls back; FMC also deletes the app created in step 2.

## 4. Activation (optional)

| Step | Function | Notes |
|------|------|------|
| 1 | `activateDetectors` `[[uuid, ...]]` | FMC often takes 1–3 minutes to return; the tool waits up to 3 minutes, then switches to polling |
| 2 | `getDetectorList` `[[], {"column":null,"ascending":0}, offset, 2000]` | Pages through all detectors (about 10,000) and checks `data.active == 1`; every 15 s, for up to 6 minutes |

Only custom detectors with `data.editable == 1` are activated; Cisco built-in detectors are never changed.

FMC pushes activation to all managed devices directly — **no deploy is needed** (tested on FMC 10.0.1: no pending deployment after activation, and the detector takes effect immediately). Per FMC's own notice, Snort 2 devices restart Snort immediately on activation/deactivation; Snort 3 devices do not restart and traffic is not interrupted, though application detection may pause briefly. The tool never deploys automatically.

## 5. Reading the shared library

- First read the branch's latest commit via `https://github.com/<owner>/<repo>.git/info/refs?service=git-upload-pack`, then read `library/index.json` and the Lua files from that commit, so the index and Lua come from the same version;
- Primary source `raw.githubusercontent.com`, falling back to the `cdn.jsdelivr.net` mirror;
- Each Lua is uploaded only if its SHA256 matches the index.
