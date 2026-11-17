# Changelog

## 1.0.1 — 2026-11-17

- macOS: one universal app (Apple silicon + Intel) shipped as `ngfw-lua-importer-1.0.1-macos-universal.zip` with an icon, replacing the two extension-less `darwin-arm64` / `darwin-amd64` binaries that macOS could not open by double-click. The app runs in the background without a Dock icon and opens the page in the browser.
- New **Quit** button in the page header (refused while an FMC upload is running).
- Opening the program again while it is running reopens the existing page instead of failing on the busy port.
- Fatal start-up errors are shown in a dialog when running as the macOS app.
- Release file names: `windows-x64.exe`, `macos-universal.zip`, `linux-x64`.

## 1.0.0 — 2026-11-16

First release.

- Local web UI (Chinese / English) that lists the shared Lua library with search, select-all, refresh, 6-per-page paging and Lua preview.
- FMC connection test that shows the FMC version; a Save button (left of Test connection) stores FMC address, username and TLS option (never the password).
- Dark UI matching NGFW App Detector; the upload controls sit at the top-right of the shared-library card.
- Upload selected detectors to FMC Local App Detectors with category, risk and business relevance from the library; optional activation.
- Upload confirmation dialog: a short "upload only, no traffic impact" note without activation; with activation, an impact warning (Snort 3 vs Snort 2, identification changes, multidomain) that must be acknowledged, based on FMC's own warning and measurements on FMC 10.0.1 / FTD 10.0.0.
- SHA256 verification of every Lua before upload; existing applications are skipped, never overwritten; failed uploads are rolled back.
- Shows the upload method, program version, tested FMC version and a compatibility-report email link (yongwli@cisco.com).
- Verified on FMC 10.0.1 (build 1); binaries for Windows x64, macOS arm64/x64 and Linux x64.
