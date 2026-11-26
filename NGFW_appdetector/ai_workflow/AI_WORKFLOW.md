# AI × NGFW App Detector Workflow (verified)

**English** | [简体中文](./AI_WORKFLOW.zh-CN.md)

> Public copy: this repository contains the docs and decks only. The `pipeline/`, `apk_tools/`, `config/`, `runs/` and `history/` folders mentioned here (scripts, lists, evidence, handoffs) are kept in the maintainer's internal copy; IPs and other environment details are replaced with placeholders.

> Use an AI assistant (Copilot, Claude Code, Codex, Cursor, …) to drive **NGFW App Detector**: run apps automatically, capture their traffic, generate Cisco Secure Firewall custom Lua application detectors (OpenAppID detectors), verify live hits on a real FMC/FTD, produce an evidence deck, and publish to the shared library.
>
> This document is written **for the next AI (and for people) to follow**. Every step has been run end to end in 7 rounds between 2026-10 and 2026-11 (about 76 new Lua detectors hit live on FTD; the shared library now holds 78).
>
> Maintenance: after each round, add new pitfalls and tools to this document (and the Chinese version) and to `runs/`.

---

## 0. Read this first (for AI assistants)

If you are the AI taking over this work:

1. Read sections 1–8 below, then the latest handoff in `runs/` (for example `runs/2026-11_hk/`).
2. **Do not start right away.** Confirm with the user per section 7: market / app list, whether every app is verified on FMC, and whether to publish.
3. **Claim** the lab before touching it and **release** it afterwards (section 8).
4. Follow the hard rules in section 8: never commit passwords, never upload PCAPs, no git commit unless asked, kill processes by PID only.
5. The only accepted result is a **live hit in FMC Connection Events**. Apps that cannot run are recorded as failed with a reason. **Never fabricate evidence.**

Suggested opening prompt (users can paste this into any AI):

```text
Read NGFW_appdetector/ai_workflow/AI_WORKFLOW.md and the latest handoff under runs/.
This time we will do: <market / app scope>. First give me the app list and the items
I need to confirm. Do not touch the lab yet.
```

---

## 1. Core idea

**The AI is the operator, App Detector is the translator, FMC/FTD is the referee.**

```
 Pick list ─► Check FMC built-ins ─► Run app + capture ─► Extract app-owned domains ─► Generate Lua
    ▲                                                                                     │
    │                                                                                     ▼
 Publish library ◄─ Evidence deck ◄─ Screenshots/JSON ◄─ Re-run & verify hit ◄─ Import/activate/deploy on FMC
```

| Principle | Meaning |
|---|---|
| Find the gap first | Check whether a built-in OpenAppID detector already identifies the app; only generate Lua for apps that are not identified. Built-ins are tested too: a built-in name does not guarantee mobile traffic is identified (e.g. Spotify, KKBOX, Google Maps). |
| App-owned domains only | Lua rules use only SNI/Host root domains owned by the app. Exclude CDNs, ad/analytics SDKs and parent-company/group domains, otherwise other apps get misidentified. |
| Verify by re-running | After import and activation, **run the app again**; it passes only when FMC Connection Events show `Web App = <Lua name>`. |
| Complete evidence | Per app: client screenshot + FMC detector list screenshot + FMC event screenshot + event JSON. |
| Humans decide | People decide the list, scope, publishing and conflicts; all repetitive work goes to the AI and scripts. |
| Failures are results | Anti-emulator, root detection, stub APKs etc. are recorded with the reason and shown on the "not identified" slide. |

---

## 2. Components and lab topology

| Component | Where | Role |
|---|---|---|
| **Mac (where the AI runs)** | local | Runs the AI, the scripts in this folder, tshark analysis, Lua generation, screenshots (Playwright), decks |
| **Windows test VM** | `<VM_IP>` (on ESXi `<ESXI_IP>`, moid 5; lab ID `win-test-host`) | Runs Windows clients; runs the Android emulator (`E:\android\sdk`, AVD `Modern34`); runs the App Detector web server (`:8765`, scheduled task `ngfwweb`). Internet via proxy `<PROXY_IP>:80` |
| **FMC** | `<FMC_IP>`, 10.0.1 (lab ID `fmc`) | Imports/activates detectors, provides Connection Events |
| **FTD** | Snort 3, routed (lab ID `ftd`) | VM traffic passes through it and gets identified |
| **App Detector** | VM `:8765` | `POST /api/fmc/search` queries events; `/api/share/submission` submits to the library; web UI for Windows process capture and Lua generation |
| **Lua Maintainer** | `NGFW_lua_maintainer` (Mac `127.0.0.1:8780`) | Reviews and publishes to the GitHub library (holds the token; maintainer only) |
| **Lua Importer (Go)** | `NGFW_lua_importer` (`:8790`) | Lets users import library Lua into FMC in one click. **The AI must not touch the user's running Importer** |
| **Shared library** | GitHub `ongwei76/Cisco-NGFW-APPDetector` → `library/` | Verified Lua files + metadata |

The Mac controls the VM over **WinRM** (`pipeline/droid.py`), and the emulator through `adb` on the VM. Detectors are imported and activated through FMC's private UI endpoints (`FmcUiClient` / `FmcDetectorImporter`, see the project's `src/ngfw_appdetector/ngfw_collector/`); deployment uses the FMC REST API.

---

## 3. Three capture modes

| Mode | For | How | Verified in |
|---|---|---|---|
| **A. Windows process** | PC clients (brokers, video) | Install the client on the VM → in App Detector web, pick the process and start capture (socket table + FMC events correlated by 5-tuple/time) → review Host/SNI, exclude CDNs → generate Lua (`/api/lua/<NAME>.lua`) | Broker top 5, video top 10 |
| **B. Android emulator (main)** | Mobile apps, games, overseas markets | Android 14 (API 34) emulator in the VM, `adb root` + `tcpdump` (earlier: Android 11 + PCAPdroid per-UID capture) → extract SNI with tshark on the Mac → `android_pcap_to_lua.py` generates the Lua | China top 20/50/100, games top 30, Hong Kong top 50 |
| **C. Web fallback** | Client cannot run in the VM | Use the browser on the official site / web version to produce traffic on the same domains | YangShiPin |

---

## 4. Standard flow (Android market top N, the main flow)

All commands run from this folder, `ai_workflow/`. Python environment:

```bash
/usr/bin/python3 -m venv --system-site-packages .venv-lab && .venv-lab/bin/pip install -r requirements-lab.txt
cp config/lab.example.env config/lab.env   # fill in FMC/VM/ESXi credentials; gitignored
# Convention: PY=$PWD/.venv-lab/bin/python; pipeline scripts run from pipeline/ with PYTHONPATH=.
# Lua generation and fmc50.py use the project's own ../.venv (gen.sh does this automatically)
```

### 4.1 Scoping and confirmation (human checkpoint)
1. Pick a market; build a 50-app list from Similarweb / Google Play regional charts.
2. Confirm with the user: the list, whether all 50 are verified on FMC (built-ins included), whether to publish, the publish note, deck language(s).
3. Create the round's working folder:
   ```bash
   bash pipeline/new_market.sh sg        # creates pipeline/sg/ from the hk template
   ```
   Edit `pipeline/sg/market.json` (name, date, VM folder, publish note, evidence folder `runs/<yyyy-mm>_sg/evidence`) and `pipeline/sg/apps.py` (`(App, display name, package, category, FMC built-in name or "")`).
   **App names must match `^[A-Za-z_]{1,15}$`** (no digits; they become Lua names).
4. Fetch FMC built-in app names and generate the list JSON files:
   ```bash
   cd apk_tools
   MARKET=sg $PY fmcapps.py            # → work/sg/fmc_apps.json (claim fmc first)
   MARKET=sg $PY mkjson.py             # → pipeline/sg/pkgs.json builtin.json meta.json, checks names
   ```

### 4.2 Download APKs (on the Mac, no lab)
Downloading from APKPure through the VM proxy stalls at 0 bytes, so download on the Mac:
```bash
MARKET=sg $PY dlall.py        # APKPure API (apkp.py), parallel → work/sg/www/
MARKET=sg $PY prep.py         # pack → work/sg/pkg/<App>.zip, writes splits.json
MARKET=sg $PY arm64alt.py     # for armeabi-v7a-only apps, find arm64/x86_64 variants → alt.json
MARKET=sg $PY redl.py         # re-download and repack those apps
```
Packing rule: keep every non-ABI split plus the x86_64 split (or arm64_v8a if there is none). A missing ABI split gives `INSTALL_FAILED_MISSING_SPLIT`. The emulator abilist is `x86_64,arm64-v8a`.

Apps that cannot be downloaded (removed from APKPure, e.g. Meta AI, Poe, Taobao, Temu) go into `UNAVAILABLE` in `apps.py`; agree replacements with the user.

### 4.3 Transfer to the VM (claim win-test-host)
```bash
cd work/sg/pkg && python3 -m http.server 8899          # on the Mac (background)
cd apk_tools && PYTHONPATH=../pipeline MARKET=sg $PY vmfetch.py <Mac VPN IP>
```
The Mac VPN IP can change between sessions (check the utun address with `ifconfig`).

### 4.4 Emulator
`ensure()` in `pipeline/<m>/emu.py` is a watchdog: if the emulator is down it starts it with `run_emu.ps1` (Modern34, 6 GB, 4 cores, `-http-proxy`), waits for boot and runs `adb root`. `cap.py`/`gverify.py` call it before every app.

### 4.5 Verify built-in detectors
```bash
cd pipeline
NOCAP=1 PYTHONPATH=. $PY sg/cap.py WhatsApp Facebook ...        # install only
PYTHONPATH=. $PY sg/gverify.py sg/verify WhatsApp Facebook ...  # drive app 120 s, wait 60 s, query FMC
```
`gverify` queries `web_app` using the FMC name from `builtin.json`. With 0 rows it falls back to "all events from the VM source IP" and records `seen_apps`, which tells you whether the app was identified as a parent app or not identified at all. Built-ins with 0 hits move on to 4.6.

### 4.6 Capture → generate Lua → import to FMC → verify
```bash
PYTHONPATH=. $PY sg/cap.py AppA AppB ...        # install + capture 150 s → sg/<app>.pcap
python3 sg/sni.py sg/appa.pcap                  # SNI root domains and host names
bash sg/gen.sh AppA appa.com,appa-cdn.net        # → ../../generated_detectors/AppA.lua
cd sg && ../../../.venv/bin/python fmc50.py import AppA AppB
../../../.venv/bin/python fmc50.py activate AppA AppB
../../../.venv/bin/python fmc50.py forcedeploy
cd .. && CUSTOM=1 SECS=150 PYTHONPATH=. $PY sg/gverify.py sg/verify AppA AppB
```
- 0 hits: check whether the SNIs in the pcap are taken by another rule; adjust the roots and run `fmc50.py reimport`.
- If the Lua name clashes with an FMC built-in name, add a `_Mobile` suffix (e.g. `Spotify_Mobile`), add the alias to `pkgs.json`/`meta.json`, and record it in `NEW` in `results.py`.
- Record `labctl change fmc ...` before each import/activate/deploy.

### 4.7 Screenshots
```bash
cd apk_tools && MARKET=sg $PY fmcshot.py ../work/sg/shots AppA=AppA WhatsApp=WhatsApp ...
```
Two per app: the FMC detector list (`<Tag>_detector_full.png`) and App Detector's FMC event search (`<Tag>_fmc_full.png`).

### 4.8 Evidence
Fill in `pipeline/sg/results.py` (`CUSTOM`, `NEW`, `PARENT`, `SHARED_INFRA`, `FAIL` reasons, `NOTE`), then:
```bash
MARKET=sg $PY build_ev.py      # → runs/<yyyy-mm>_sg/evidence/apps.json + client/ fmc_detector/ fmc_events/ fmc_json/
```
Status values: `builtin_hit`, `identified_as_parent`, `new_lua_verified`, `no_lua_shared_infra`, `failed`.

### 4.9 Deck
Delegate to the **deck generator** agent (style source `~/.copilot/deck-kit/`). Data source is `evidence/apps.json`; structure follows `runs/2026-11_hk/generate_hk_top50_ppt.py`: cover → coverage → method → full table (2 slides) → one evidence slide per new Lua → built-in hits two per slide → reasons for not identified → caveats → shared library.

Copy the deck and its PDF into [presentation/verification_decks/](./presentation/verification_decks/) and add a row to its index (both languages).
Before a deck goes public, make a redacted copy — screenshots of FMC events show lab IPs:
```bash
cd apk_tools
$PY redact_deck.py <deck>.pptx <public>/<deck>.pptx      # IPs in text/notes -> placeholders; IP columns and IP text in images erased
$PY redact_deck.py --verify <public>/<deck>.pptx         # independent OCR check, must report 0 problems
python3 contact_sheets.py <deck>.pptx <public>/<deck>.pptx /tmp/sheets tag   # then LOOK at every changed image
```

### 4.10 Publish (after the user confirms)
```bash
cd apk_tools && PYTHONPATH=../pipeline $PY putlua.py AppA AppB ...     # Lua → VM C:\ngfw\generated_detectors
cd ../../../NGFW_lua_maintainer && .venv/bin/python -m lua_maintainer --no-browser   # :8780, background
cd ../NGFW_appdetector/ai_workflow/pipeline/sg && $PY publish50.py AppA AppB ...
```
`publish50.py` needs `info.json` (`App: [package, "API 34", "rule summary"]`). After publishing, check that the count in GitHub `library/` went up.

### 4.11 Wrap-up
Stop 8899 and the maintainer; `MARKET=sg PYTHONPATH=../pipeline $PY clean.py` (uninstall apps, stop the emulator); delete `E:\android\apk<m>` on the VM if needed; empty `work/<m>/`; `labctl release`; write a handoff in `runs/<yyyy-mm>_<m>/` (results, pitfalls, what to change next time).

---

## 5. Lua generation rules

| Rule | Details |
|---|---|
| Use app-owned roots only | e.g. OpenRice → `openrice.com`; Keeta → `mykeeta.com, mykeeta.net`. |
| Exclude shared infrastructure | CDNs (akamai, cloudfront, fastly…), ad/analytics/crash SDKs (Firebase, Crashlytics, AppsFlyer…), parent-company/group domains. e.g. Threads only shows Instagram/fbcdn → recorded as "identified as Instagram", no Lua; foodpanda only shows `deliveryhero.net` → no Lua. |
| Watch sibling brands | Xianyu and UC Browser share `px.ucweb.com` → drop the shared host; JobsDB uses `seek.com`, which also matches the SEEK app → note it in the deck. |
| Overlaps like Douyin/TikTok | Narrow to hosts unique to the China app to avoid false positives. |
| Name | `^[A-Za-z_]{1,15}$`, must not clash with FMC built-in or existing custom detectors (add `_Mobile` on clash). |
| Category | Use existing FMC category names (`mkjson.py` has a mapping table); unknown categories fall back to `others` on FMC, so watch the import message. |
| Signals | HTTPS: SNI (exact + suffix); cleartext: HTTP Host. Rules are rendered by the project's `LuaRenderer` template. |

---

## 6. Verification and evidence standard

An app counts as "new Lua verified" only when all of these hold:

1. The Lua is imported on FMC and **active**, and the deploy SUCCEEDED (on Snort 3, activation takes effect in about 100 s without restarting Snort);
2. The app is **run again** after import (`gverify`, 120–150 s of interaction by default);
3. FMC Connection Events show at least one `web_app = <Lua name>` with the test VM as source;
4. Saved: client screenshot, FMC detector screenshot, FMC event screenshot, event JSON (`fmc_json/<App>-fmc.json`).

Other statuses:
- `builtin_hit`: an FMC built-in name hit;
- `identified_as_parent`: identified as the parent app (Messenger → Facebook);
- `no_lua_shared_infra`: only group-shared domains, deliberately no Lua;
- `failed`: could not run or produced no app traffic — **a reason is required**.

---

## 7. Human checkpoints

| When | What to confirm |
|---|---|
| Before starting | Market, app list, whether all apps are verified on FMC (built-ins included), whether to publish, publish note, deck language(s) |
| Replacements needed | Which app replaces one that cannot be downloaded |
| Lab conflict | If a resource is held by another task: wait / take over / share / use another resource — the user decides |
| Impactful lab changes | Growing VM disk/memory, deleting large folders on the VM, wiping emulator data |
| Before publishing | Which Lua files to publish, the note text |
| Questionable rules | Root domains that might match other brands (e.g. seek.com) |

---

## 8. Hard rules

- **Lab claim**: before touching VM/FMC/FTD run `python3 ~/.copilot/lab/labctl.py claim fmc ftd win-test-host --holder "<task>" --session "<session link>" --purpose "<one line>"`; before config changes `labctl change <id> ...`; when done `labctl release --holder "<task>"`. On conflict (exit code 2) stop and ask the user. After changing ESXi networking / VM hardware / FTD policy run `labctl refresh`.
- **Credentials** live only in `config/lab.env` (gitignored) and are read by scripts via `pipeline/labcfg.py`. Docs, handoffs, decks and the shared library always say `<redacted>`.
- **Never upload PCAPs**; PCAPs, APKs, `work/` and `verify/` are gitignored.
- **No git commit unless asked**; publishing to the GitHub library needs the user's authorization.
- **Kill by PID only**, never `pkill`/`killall`.
- Do not touch the user's Importer (`:8790`).
- Decks/posters go to the **deck generator** agent.

---

## 9. Known pitfalls (by frequency)

| Pitfall | Fix |
|---|---|
| Banking/payment/government apps (HSBC, Hang Seng, BOCHK, Mox, PayMe, Octopus, iAM Smart, HA Go) crash or stay on the splash screen on a rooted emulator | Record the failure reason; warn the user when scoping that they may want replacements |
| WeChat stuck on splash; Netflix anti-tamper crash; Gemini is a stub APK; many games are hardened/anti-emulator | Record as failed |
| After an emulator restart adbd is not root, tcpdump is missing → pcap pull fails with a base64 error | `emu.ensure()` runs `adb root`; confirm `which tcpdump` before capture |
| VM blue screen (0x1A), qemu crashes | `emu.py` watchdog + `droid.ps` timeout (300 s default) + per-app try/except |
| Running `adb start-server`/`kill-server` synchronously over WinRM hangs | Start it with `Win32_Process Create` |
| `-wipe-data` needs about 78 GB free on E:; wiping removes installed apps | Clear `E:\android\apk*` first |
| App Detector (:8765) not up after a VM reboot | `Start-ScheduledTask ngfwweb` (user must be logged in); `gverify` tries it automatically on the 3rd failed query |
| APKPure's first variant is often armeabi-v7a only | `arm64alt.py` + `redl.py` |
| Downloading APKPure through the VM proxy stalls | Download on the Mac, serve to the VM with http.server |
| `activateDetectors` call times out | Keep polling `getDetectorList` (handled in `fmc50.py activate`) |
| Deploy progress spinner stuck in the browser | Trust REST `deployment/jobhistories` (`fmc50.py forcedeploy`) |
| FMC built-in name exists but does not identify mobile traffic | If live test gives 0 hits, build a `_Mobile` Lua |
| Clock skew between Windows and FMC | Calibrate with FMC's HTTP `Date` header (built into App Detector) |
| PowerShell paths inside `python -c` strings get escaped | Write a script file with raw strings |
| `stop_bash` may not kill child Python processes | Find the PID with `ps` and kill it |
| macOS Vision OCR (pyobjc) silently returned empty results after heavy use (`e5rtError`), so redaction missed images | Use `redact_deck.py` (RapidOCR, deterministic), always run `--verify`, and look at the contact sheets |

---

## 10. Tools

### pipeline/ (Mac side: drives the VM, emulator and FMC)
| File | Purpose |
|---|---|
| `labcfg.py` | Reads addresses and credentials from `config/lab.env`, plus project paths |
| `droid.py` | WinRM: `ps()` (with timeout), `adb()`, `shell()`, `screenshot()`, `pull()` |
| `econsole.py` | Emulator console (5554) commands, e.g. shutdown |
| `android_pcap_to_lua.py` | pcap + root domains → Lua (uses the project's `LuaRenderer`), writes a summary JSON |
| `pcapdroid-v2.0.2.lua` | tshark plugin for PCAPdroid extensions |
| `vm_smb.py` / `android_smb.py` | Transfer files to the VM over SMB |
| `android_winrm.py` | Run a PowerShell script file on the VM |
| `android_esxi_probe.py` / `android_esxi_reconfig.py` | Read-only view / change VM resources (changes need the user's OK and `labctl change esxi`) |
| `fmc_odp_grep.py` | SSH to FMC and check whether a domain already appears in built-in ODP rules |
| `new_market.sh` | Create a new round folder from the `hk/` template |
| `hk/` | **A complete round template**: `cap.py` `gverify.py` `app_ncap.py` `emu.py` `run_emu.ps1` `fmc50.py` `gen.sh` `sni.py` `publish50.py` + `market.json` `apps.py` `results.py` `pkgs/meta/builtin/info.json` |
| `games/` | Capture script and emulator launcher from the games round |
| `android_*.ps1`, `android_pilot_*`, `verify50.py`, `find_apk_urls.py`, `yyb_urls.py` | Scripts from earlier rounds (VM setup, PCAPdroid pilot, China top 50/100, Tencent MyApp downloads), kept for reference |

### apk_tools/ (Mac side: downloads, screenshots, evidence, publishing; all need `MARKET=<m>`)
| File | Purpose |
|---|---|
| `mkt.py` | Context of the current round (`MARKET`, folders, `apps.py`) |
| `mkjson.py` | Generate/merge `pkgs.json`, `builtin.json`, `meta.json` from `apps.py`; checks names |
| `fmcapps.py` | Fetch all FMC application names → `work/<m>/fmc_apps.json` |
| `apkp.py` / `dlall.py` | APKPure API downloads |
| `prep.py` | Pack `<App>.zip` following the ABI rule |
| `rz.py` / `arm64alt.py` / `redl.py` | List XAPK contents (HTTP Range), find 64-bit variants, re-download |
| `vmfetch.py` | VM pulls the zips from the Mac http.server |
| `fmcshot.py` / `detrow.py` | Playwright screenshots of the FMC detector list and event search |
| `build_ev.py` | Builds `evidence/apps.json` and cropped screenshots |
| `putlua.py` | Copy Lua to the VM for publishing |
| `clean.py` | Uninstall apps, stop the emulator |
| `redact_deck.py` / `contact_sheets.py` | Redacted public copy of a deck (RapidOCR) and contact sheets of the changed images for review |

> `mkjson.py`, `arm64alt.py`, `vmfetch.py`, `new_market.sh` and the parameterization were added on 2026-11-26. The first two were tested offline; `vmfetch.py` has not run on the lab yet, so watch it on first use.

---

## 11. Rounds so far

| Round | Date | Mode | Result | Evidence |
|---|---|---|---|---|
| China Merchants Securities baseline | 2026-10 | A | TdxW / CMS hits | `presentation/NGFW_App_Detector_技术介绍.pptx` |
| Broker PC clients top 5 | 2026-11-11 | A | CITIC, GTHT, HTSC, GF, China Galaxy: 5 new Lua, all hit | [券商App验证证据](./presentation/verification_decks/券商App验证证据.pdf) |
| China video apps top 10 | 2026-11-12 | A + C | 6 built-in; Douyin, Xigua, Migu, YangShiPin: 4 new Lua hit | [视频App验证证据](./presentation/verification_decks/视频App验证证据.pdf) |
| China Android top 20 | 2026-11-13 | B (PCAPdroid) | 14 built-in; Pinduoduo, Amap, DiDi, Ele.me: 4 new Lua | [安卓App验证证据](./presentation/verification_decks/安卓App验证证据.pdf) |
| China Android top 50 | 2026-11-15 | B | 26 built-in, 6 already in library, 15 new (14 detectors), 3 anti-emulator | [安卓Top50App验证证据](./presentation/verification_decks/安卓Top50App验证证据.pdf) |
| China Android 51–100 | 2026-11-15 | B | 14 built-in, 1 already in library, 18 new Lua, 17 failed | [安卓Top100App验证证据](./presentation/verification_decks/安卓Top100App验证证据.pdf) |
| Android games top 30 | 2026-11-16 | B | 13 new Lua, 17 failed | [安卓Top30手游验证证据](./presentation/verification_decks/安卓Top30手游验证证据.pdf) |
| Go Lua Importer | 2026-11 | — | Import + activation effective in about 100 s, Snort 3 not restarted | `NGFW_lua_importer/` |
| **Hong Kong top 50** | 2026-11-17 | B | 18 new Lua, 15 built-in, 2 identified as parent, 1 no Lua, 14 failed | [HK_Top50_Android_Verification_EN](./presentation/verification_decks/HK_Top50_Android_Verification_EN.pdf) · `runs/2026-11_hk/` |

Detailed lessons from earlier phases: `history/checkpoints_001-046_digest.md` (Chinese).

---

## 12. Next improvements

- Validate `vmfetch.py` on the lab for the first time.
- `info.json` (rule summaries for publishing) is still hand-written; it could be generated from `*.summary.json`.
- Windows process mode (A) still relies on the App Detector web UI; it has no batch script like Android.
- Banking/government apps need a non-root or physical-device approach to be covered.
