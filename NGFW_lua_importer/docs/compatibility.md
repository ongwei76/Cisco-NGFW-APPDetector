# Compatibility

**English** | [简体中文](compatibility.zh-CN.md)

## Tested environment

| Item | Version |
|------|------|
| FMC | Cisco Secure Firewall Management Center for VMware **10.0.1 (build 1)** |
| This tool | 1.0.1 |
| Client platforms | macOS 27 (Apple silicon), Windows 10 Enterprise x64 (tested) |

Flows verified on 10.0.1: login → read version → upload (Inactive) → upload and activate → skip existing apps → activate an existing Inactive custom detector → automatic rollback on upload failure (tested against a mock FMC).

Other FMC versions (e.g. 7.x) **should** use the same Web UI endpoints but have not been tested. Because the tool uses FMC Web UI internal endpoints rather than the public REST API, they may change when Cisco upgrades FMC.

## Common messages

| Message | Likely cause / what to do |
|------|----------------|
| `cannot reach FMC` | Wrong address, no network path, or *Verify HTTPS certificate* is ticked but FMC has a self-signed certificate |
| `FMC login failed ... check the username and password` | Wrong username/password, or the account is locked |
| `FMC Web UI session could not be established ... may not be compatible` | Login worked but no session token was found on the `/ddd/` page, possibly an FMC version difference → **please report** |
| `FMC returned no data; the FMC Web UI session was logged out` | The same account logged in to FMC elsewhere (browser or another tool). FMC keeps one Web session per account; use a dedicated account and retry |
| `getFilterList: unexpected FMC response` / `getDetectorList: unexpected FMC response` | FMC returned a different format → **please report** |
| `Lua upload rejected by FMC: <reason>` | FMC rejected the Lua (syntax or unsupported API). If the same Lua works on 10.0.1, it is a version difference → **please report** |
| `FMC saved the detector without the uploaded Lua` | The Lua saved by FMC differs from the upload; rolled back automatically → **please report** |
| `FMC did not report all detectors as active within 6 minutes` | FMC is busy; check in the FMC UI later, or run again with *Activate* ticked |
| `SHA256 mismatch with the library index; refused` | The download does not match the library index (interception or stale mirror cache); click *Refresh* and retry later |
| `category "xxx" not found on this FMC, used "others"` | This FMC has no category with that name; `others` was used and can be changed in FMC manually |

## How to report

Email **[yongwli@cisco.com](mailto:yongwli@cisco.com)** with:

1. The tool version and OS (`ngfw-lua-importer -version` or *Program version* in the UI);
2. The FMC version (*Connected FMC version* in the UI, or Help → About in FMC);
3. The app name and version that failed;
4. The error shown in the UI and the full *Run log*.

The email link in the UI pre-fills items 1 and 2 and the last error. Never send your FMC password by email.
