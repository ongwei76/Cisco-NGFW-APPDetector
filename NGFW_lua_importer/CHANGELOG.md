# Changelog

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
