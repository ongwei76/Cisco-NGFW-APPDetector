# Verification decks

**English** | [简体中文](README.zh-CN.md)

Evidence decks from every AI-driven verification round (one deck per round). Each deck shows, per app, the client screenshot, the detector in FMC and the FMC connection events with the new `Web App` name, plus the apps that could not be verified and why. PDFs are for viewing online; PPTX for editing.

Decks are kept in the language they were made in; no other language versions exist yet. In the copies published on GitHub, IP addresses in slide text, speaker notes and screenshots are redacted.

| Round | Date | Language | Slides | Result | Files |
|---|---|---|---|---|---|
| Broker PC clients top 5 | 2026-11-11 | Chinese | 8 | CITIC, GTHT, HTSC, GF, China Galaxy: 5 new Lua, all hit | [PDF](券商App验证证据.pdf) · [PPTX](券商App验证证据.pptx) |
| China video apps top 10 | 2026-11-12 | Chinese | 8 | 6 built-in; Douyin, Xigua, Migu, YangShiPin: 4 new Lua hit | [PDF](视频App验证证据.pdf) · [PPTX](视频App验证证据.pptx) |
| China Android top 20 | 2026-11-13 | Chinese | 8 | 14 built-in; Pinduoduo, Amap, DiDi, Ele.me: 4 new Lua | [PDF](安卓App验证证据.pdf) · [PPTX](安卓App验证证据.pptx) |
| China Android top 50 | 2026-11-15 | Chinese | 19 | 26 built-in, 6 already in library, 15 new (14 detectors), 3 anti-emulator | [PDF](安卓Top50App验证证据.pdf) · [PPTX](安卓Top50App验证证据.pptx) |
| China Android 51–100 | 2026-11-15 | Chinese | 23 | 14 built-in, 1 already in library, 18 new Lua, 17 failed | [PDF](安卓Top100App验证证据.pdf) · [PPTX](安卓Top100App验证证据.pptx) |
| Android games top 30 | 2026-11-16 | Chinese | 18 | 13 new Lua, 17 failed | [PDF](安卓Top30手游验证证据.pdf) · [PPTX](安卓Top30手游验证证据.pptx) |
| Hong Kong market top 50 | 2026-11-17 | English | 36 | 18 new Lua, 15 built-in, 2 identified as parent, 1 no Lua, 14 failed | [PDF](HK_Top50_Android_Verification_EN.pdf) · [PPTX](HK_Top50_Android_Verification_EN.pptx) |

New rounds: put the deck (and its PDF) here, named `<Market>_Top<N>_<Platform>_Verification_<LANG>.pptx`, and add a row to this table and to the Chinese index.

Source copies and generator scripts are in the project's `presentation/` folder (`generate_*_ppt.py`) and in `runs/<yyyy-mm>_<market>/`.
