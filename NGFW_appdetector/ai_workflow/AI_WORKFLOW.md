# AI × NGFW App Detector 工作流（已验证）

> 公开版说明：本仓库只包含文档和 PPT。文中提到的 `pipeline/`、`apk_tools/`、`config/`、`runs/`、`history/`（脚本、清单、证据和交接记录）保存在维护者的内部副本中；IP 等环境信息已替换为占位符。

[English version](./AI_WORKFLOW_EN.md)

> 用 AI 助手（Copilot、Claude Code、Codex、Cursor 等）驱动 **NGFW App Detector**：自动跑 App、抓流量、生成 Cisco Secure Firewall 自定义 Lua 应用识别器（OpenAppID Detector），在真实 FMC/FTD 上实测命中，产出证据 PPT，并发布到共享库。
>
> 这份文档是**给下一个 AI（也给人）照着做**的。所有步骤都已在 2026-10 ~ 2026-11 的 7 轮实测中跑通（约 76 个新 Lua 在 FTD 上命中，共享库现有 78 个）。
>
> 维护：每轮结束后把新的坑、新的工具更新到本文（及英文版）和 `runs/`。

---

## 0. 给 AI 的开场说明（先读这一节）

如果你是接手这项工作的 AI：

1. 先读完本文第 1–8 节，再读 `runs/` 里最近一轮的交接（例如 `runs/2026-11_hk/`）。
2. **不要直接开始。** 先按第 7 节和用户确认：市场/清单、是否全部上 FMC 验证、是否发布。
3. 动 lab 之前先**认领**（第 8 节），结束后**释放**。
4. 遵守第 8 节的硬规则：不提交密码、不上传 PCAP、未经要求不 git commit、只按 PID kill 进程。
5. 结论只以 **FMC Connection Event 实测命中** 为准。跑不起来的 App 如实记为失败，写清原因，**绝不伪造证据**。

建议的开场提示词（用户可直接复制给任何 AI）：

```text
读 NGFW_appdetector/ai_workflow/AI_WORKFLOW.md 和 runs/ 下最近一轮的交接。
这次要做：<市场/App 范围>。先给我清单和需要确认的事项，不要动 lab。
```

---

## 1. 核心思路

**AI 当操作员，App Detector 当翻译，FMC/FTD 当裁判。**

```
 选清单 ─► 查 FMC 内置库 ─► 跑 App + 抓包 ─► 提取 App 自有域名 ─► 生成 Lua
    ▲                                                           │
    │                                                           ▼
 发布共享库 ◄─ 证据 PPT ◄─ 截图/JSON ◄─ 二次运行验证命中 ◄─ 导入/激活/部署 FMC
```

| 原则 | 说明 |
|---|---|
| 先查缺口，再补 | 先确认 FMC 内置 OpenAppID 是否已识别；只给没识别的 App 生成 Lua。内置的也要实测（内置名不等于真能识别移动端流量，例：Spotify、KKBOX、Google Maps）。 |
| 只用 App 自有域名 | Lua 规则只用该 App 独有的 SNI/Host 根域名；排除 CDN、广告/统计 SDK、母公司/集团共享域名，否则会误识别其他 App。 |
| 二次运行验证 | 导入并激活后，**重新跑一次 App**，在 FMC Connection Events 里看到 `Web App = <Lua 名>` 才算通过。 |
| 证据齐全 | 每个 App：客户端截图 + FMC Detector 列表截图 + FMC 事件截图 + 事件 JSON。 |
| 人只做决策 | 清单、范围、发布、冲突由人拍板；重复操作全部交给 AI 和脚本。 |
| 失败也是结果 | 反模拟器、root 检测、存根 APK 等如实记录原因，进 PPT 的“未识别”页。 |

---

## 2. 组件与 lab 拓扑

| 组件 | 位置 | 作用 |
|---|---|---|
| **Mac（AI 所在）** | 本机 | 运行 AI、本目录的脚本、tshark 分析、Lua 生成、截图（Playwright）、PPT |
| **Windows 测试 VM** | `<VM_IP>`（ESXi `<ESXI_IP>` 上，moid 5；lab ID `win-test-host`） | 跑 Windows 客户端；跑 Android 模拟器（`E:\android\sdk`，AVD `Modern34`）；运行 App Detector Web（`:8765`，计划任务 `ngfwweb`）。出网代理 `<PROXY_IP>:80` |
| **FMC** | `<FMC_IP>`，10.0.1（lab ID `fmc`） | 导入/激活 Detector，提供 Connection Events |
| **FTD** | Snort 3，routed（lab ID `ftd`） | VM 流量经过它，产生识别结果 |
| **App Detector** | VM `:8765` | `POST /api/fmc/search` 查事件；`/api/share/submission` 提交共享库；Windows 进程采集和 Lua 生成 UI |
| **Lua Maintainer** | `NGFW_lua_maintainer`（Mac `127.0.0.1:8780`） | 审核并发布到 GitHub 共享库（持有 token，仅维护者用） |
| **Lua Importer（Go）** | `NGFW_lua_importer`（`:8790`） | 给用户从共享库一键导入 FMC。**AI 不要动用户正在运行的 Importer** |
| **共享库** | GitHub `ongwei76/Cisco-NGFW-APPDetector` → `library/` | 已验证的 Lua + 元数据 |

Mac 通过 **WinRM**（`pipeline/droid.py`）控制 VM，再通过 VM 上的 `adb` 控制模拟器；通过 FMC 的 UI 私有接口（`FmcUiClient` / `FmcDetectorImporter`，见项目 `src/ngfw_appdetector/ngfw_collector/`）导入和激活 Detector；用 FMC REST 做部署。

---

## 3. 三种采集模式

| 模式 | 适用 | 做法 | 已验证轮次 |
|---|---|---|---|
| **A. Windows 进程** | PC 客户端（券商、视频） | 在 VM 装客户端 → App Detector Web 选进程、开始采集（Socket 表 + FMC 事件按五元组/时间关联）→ 检查 Host/SNI、排除 CDN → 生成 Lua（`/api/lua/<NAME>.lua`） | 券商 Top5、视频 Top10 |
| **B. Android 模拟器（主力）** | 手机 App、手游、海外市场 | VM 内 Android 14（API 34）模拟器，`adb root` + `tcpdump` 抓包（早期是 Android 11 + PCAPdroid 按 UID 抓包）→ Mac 上 tshark 提 SNI → `android_pcap_to_lua.py` 生成 Lua | 中国 Top20/50/100、手游 Top30、香港 Top50 |
| **C. 网页兜底** | 客户端无法在 VM 运行 | 用浏览器访问官网/网页版产生同域流量验证 | 央视频 |

---

## 4. 标准流程（Android 市场 Top N，主力流程）

所有命令都在本目录 `ai_workflow/` 下。Python 环境：

```bash
/usr/bin/python3 -m venv --system-site-packages .venv-lab && .venv-lab/bin/pip install -r requirements-lab.txt
cp config/lab.example.env config/lab.env   # 填 FMC/VM/ESXi 凭据；已 gitignore
# 约定：PY=$PWD/.venv-lab/bin/python；pipeline 脚本在 pipeline/ 下用 PYTHONPATH=. 运行
# Lua 生成和 fmc50.py 用项目自己的 ../.venv（gen.sh 已自动使用）
```

### 4.1 立项与确认（人工节点）
1. 选市场；参考 Similarweb / Google Play 地区榜单整理 50 个 App。
2. 和用户确认：清单、是否全部 50 个都上 FMC 验证（含内置）、是否发布、发布备注、PPT 语言。
3. 新建一轮的工作目录：
   ```bash
   bash pipeline/new_market.sh sg        # 以 hk 为模板生成 pipeline/sg/
   ```
   编辑 `pipeline/sg/market.json`（名称、日期、VM 目录、发布备注、证据目录 `runs/<yyyy-mm>_sg/evidence`）和 `pipeline/sg/apps.py`（`(App, 显示名, 包名, 类别, FMC 内置名或 "")`）。
   **App 名必须匹配 `^[A-Za-z_]{1,15}$`**（不能有数字，会成为 Lua 名）。
4. 拉取 FMC 内置应用名并生成清单 json：
   ```bash
   cd apk_tools
   MARKET=sg $PY fmcapps.py            # → work/sg/fmc_apps.json（需认领 fmc）
   MARKET=sg $PY mkjson.py             # → pipeline/sg/pkgs.json builtin.json meta.json，并检查名字冲突
   ```

### 4.2 下载 APK（在 Mac 上，不碰 lab）
VM 经代理下载 APKPure 会卡在 0 字节，所以都在 Mac 下载：
```bash
MARKET=sg $PY dlall.py        # APKPure API（apkp.py）并发下载 → work/sg/www/
MARKET=sg $PY prep.py         # 打包 → work/sg/pkg/<App>.zip，记录 splits.json
MARKET=sg $PY arm64alt.py     # 找出只有 armeabi-v7a 的，查 arm64/x86_64 版本 → alt.json
MARKET=sg $PY redl.py         # 重新下载并打包这些 App
```
打包规则：保留全部非 ABI split，加上 x86_64 split（没有则 arm64_v8a）。缺 ABI split 会 `INSTALL_FAILED_MISSING_SPLIT`。模拟器 abilist 是 `x86_64,arm64-v8a`。

下载不到的 App（APKPure 下架，如 Meta AI、Poe、Taobao、Temu）写进 `apps.py` 的 `UNAVAILABLE`，并和用户确认替补。

### 4.3 传到 VM（需认领 win-test-host）
```bash
cd work/sg/pkg && python3 -m http.server 8899          # Mac 上（后台运行）
cd apk_tools && PYTHONPATH=../pipeline MARKET=sg $PY vmfetch.py <Mac VPN IP>
```
Mac 的 VPN IP 每次可能不同（`ifconfig` 查 utun 地址）。

### 4.4 模拟器
`pipeline/<m>/emu.py` 的 `ensure()` 是看门狗：没起来就用 `run_emu.ps1` 启动（Modern34，6 GB，4 核，`-http-proxy`），等开机完成并 `adb root`。`cap.py`/`gverify.py` 每个 App 前都会调用它。

### 4.5 内置检测器验证
```bash
cd pipeline
NOCAP=1 PYTHONPATH=. $PY sg/cap.py WhatsApp Facebook ...     # 只安装
PYTHONPATH=. $PY sg/gverify.py sg/verify WhatsApp Facebook ...  # 跑 App 120s，等 60s，查 FMC
```
`gverify` 按 `builtin.json` 的 FMC 名查 `web_app`；0 条时回退为“查 VM 源 IP 的全部事件”，记录 `seen_apps`，用来判断是“识别为母应用”还是“完全没识别”。0 命中的内置 App 转入 4.6。

### 4.6 抓包 → 生成 Lua → 导入 FMC → 验证
```bash
PYTHONPATH=. $PY sg/cap.py AppA AppB ...        # 安装 + 抓包 150s → sg/<app>.pcap
python3 sg/sni.py sg/appa.pcap                  # 看 SNI 根域名和主机名
bash sg/gen.sh AppA appa.com,appa-cdn.net        # → ../../generated_detectors/AppA.lua
cd sg && ../../../.venv/bin/python fmc50.py import AppA AppB
../../../.venv/bin/python fmc50.py activate AppA AppB
../../../.venv/bin/python fmc50.py forcedeploy
cd .. && CUSTOM=1 SECS=150 PYTHONPATH=. $PY sg/gverify.py sg/verify AppA AppB
```
- 0 命中：看 pcap 里的 SNI 是否被别的规则吃掉，调整根域名后 `fmc50.py reimport`。
- 和 FMC 内置名冲突的 Lua 加 `_Mobile` 后缀（例：`Spotify_Mobile`），并在 `pkgs.json`/`meta.json` 补别名、在 `results.py` 的 `NEW` 里登记。
- 每次导入/激活/部署前记录 `labctl change fmc ...`。

### 4.7 截图
```bash
cd apk_tools && MARKET=sg $PY fmcshot.py ../work/sg/shots AppA=AppA WhatsApp=WhatsApp ...
```
每个 App 两张：FMC Detector 列表（`<Tag>_detector_full.png`）和 App Detector 的 FMC 事件查询（`<Tag>_fmc_full.png`）。

### 4.8 证据整理
把结果填进 `pipeline/sg/results.py`（`CUSTOM`、`NEW`、`PARENT`、`SHARED_INFRA`、`FAIL` 原因、`NOTE`），然后：
```bash
MARKET=sg $PY build_ev.py      # → runs/<yyyy-mm>_sg/evidence/apps.json + client/ fmc_detector/ fmc_events/ fmc_json/
```
状态枚举：`builtin_hit`、`identified_as_parent`、`new_lua_verified`、`no_lua_shared_infra`、`failed`。

### 4.9 PPT
交给 **deck generator** agent（风格源 `~/.copilot/deck-kit/`）。数据源是 `evidence/apps.json`；结构参考 `runs/2026-11_hk/generate_hk_top50_ppt.py`：封面 → 覆盖率 → 方法 → 全量表（2 页）→ 每个新 Lua 一页证据 → 内置命中两两一页 → 未识别原因 → 注意事项 → 共享库。

### 4.10 发布（人工确认后）
```bash
cd apk_tools && PYTHONPATH=../pipeline $PY putlua.py AppA AppB ...     # Lua → VM C:\ngfw\generated_detectors
cd ../../../NGFW_lua_maintainer && .venv/bin/python -m lua_maintainer --no-browser   # :8780，后台
cd ../NGFW_appdetector/ai_workflow/pipeline/sg && $PY publish50.py AppA AppB ...
```
`publish50.py` 需要 `info.json`（`App: [包名, "API 34", "规则摘要"]`）。发布后到 GitHub `library/` 确认数量增加。

### 4.11 收尾
停 8899 和 maintainer；`MARKET=sg PYTHONPATH=../pipeline $PY clean.py`（卸载 App、停模拟器）；需要时删 VM 上的 `E:\android\apk<m>`；清空 `work/<m>/`；`labctl release`；在 `runs/<yyyy-mm>_<m>/` 写交接（结果、坑、下次要改的）。

---

## 5. Lua 生成规则

| 规则 | 说明 |
|---|---|
| 根域名只取 App 自有的 | 例：OpenRice → `openrice.com`；Keeta → `mykeeta.com, mykeeta.net`。 |
| 排除共享基础设施 | CDN（akamai、cloudfront、fastly…）、广告/统计/崩溃 SDK（Firebase、Crashlytics、AppsFlyer…）、母公司/集团域名。例：Threads 只有 Instagram/fbcdn → 记为“识别为 Instagram”，不做 Lua；foodpanda 只有 `deliveryhero.net` → 不做。 |
| 小心同集团品牌 | Xianyu 和 UC 浏览器共用 `px.ucweb.com`，要删掉共享 host；JobsDB 用 `seek.com` 会同时命中 SEEK App，要在 PPT 注明。 |
| Douyin/TikTok 一类重叠 | 缩小到中国区独有 host，避免误报。 |
| 名字 | `^[A-Za-z_]{1,15}$`，不能和 FMC 内置/已有自定义 Detector 重名（冲突加 `_Mobile`）。 |
| 类别 | 用 FMC 已有类别名（`mkjson.py` 有映射表）；不存在的类别 FMC 会回退为 `others`，导入时注意提示。 |
| 信号 | HTTPS 用 SNI（精确 + 后缀）；明文用 HTTP Host。规则由项目的 `LuaRenderer` 模板生成。 |

---

## 6. 验证与证据标准

一个 App 判为“新 Lua 已验证”必须同时满足：

1. Lua 已在 FMC 导入并 **active**，部署 SUCCEEDED（Snort 3 激活约 100 秒生效，不重启 Snort）；
2. 导入后**重新运行** App（`gverify`，默认 120–150 秒操作）；
3. FMC Connection Events 中 `web_app = <Lua 名>` 至少 1 条，源 IP 为测试 VM；
4. 保存：客户端截图、FMC Detector 截图、FMC 事件截图、事件 JSON（`fmc_json/<App>-fmc.json`）。

其他状态：
- `builtin_hit`：FMC 内置名命中；
- `identified_as_parent`：被识别为母应用（Messenger→Facebook）；
- `no_lua_shared_infra`：只有集团共享域名，故意不做；
- `failed`：跑不起来或无 App 流量，**必须写原因**。

---

## 7. 人工确认节点

| 时机 | 要确认的 |
|---|---|
| 开始前 | 市场、App 清单、是否全部上 FMC 验证（含内置）、是否发布、发布备注、PPT 语言 |
| 清单有替补 | 下载不到的 App 用谁替补 |
| lab 冲突 | 资源被别的任务占用时：等待 / 接管 / 共享 / 换资源，由用户决定 |
| 影响较大的 lab 变更 | 扩 VM 磁盘/内存、删除 VM 上的大目录、wipe 模拟器数据 |
| 发布前 | 发布哪些 Lua、备注文字 |
| 有疑问的规则 | 可能误识别其他品牌的根域名（如 seek.com） |

---

## 8. 硬规则

- **Lab 认领**：动 VM/FMC/FTD 前 `python3 ~/.copilot/lab/labctl.py claim fmc ftd win-test-host --holder "<任务名>" --session "<会话链接>" --purpose "<一句话>"`；改配置前 `labctl change <id> ...`；结束 `labctl release --holder "<任务名>"`。冲突（退出码 2）时停下，问用户。改了 ESXi 网络/VM 硬件/FTD 策略后 `labctl refresh`。
- **凭据**只放 `config/lab.env`（已 gitignore），脚本通过 `pipeline/labcfg.py` 读取。文档、交接、PPT、共享库里一律写 `<redacted>`。
- **不上传 PCAP**；PCAP、APK、`work/`、`verify/` 都已 gitignore。
- **未经要求不 git commit**；发布到 GitHub 共享库需要用户授权。
- **只按 PID kill**，不用 `pkill`/`killall`。
- 不动用户的 Importer（`:8790`）。
- PPT/海报交给 **deck generator** agent。

---

## 9. 已知坑（按出现频率）

| 坑 | 处理 |
|---|---|
| 银行/支付/政府 App（HSBC、恒生、中银、Mox、PayMe、八达通、iAM Smart、HA Go）在 root 模拟器上闪退或卡启动页 | 直接记失败原因；立项时提醒用户可能换掉 |
| WeChat 卡启动页；Netflix 反篡改崩溃；Gemini 是存根 APK；不少手游加固/反模拟器 | 记失败 |
| 模拟器重启后 adbd 不是 root，tcpdump 不在 → pcap 拉取报 base64 错 | `emu.ensure()` 会 `adb root`；抓包前确认 `which tcpdump` |
| VM 蓝屏（0x1A）、qemu 崩溃 | `emu.py` 看门狗 + `droid.ps` 超时（默认 300 秒）+ 每个 App 单独 try/except |
| WinRM 同步执行 `adb start-server`/`kill-server` 会卡死 | 用 `Win32_Process Create` 启动 |
| `-wipe-data` 需要 E: 盘约 78 GB 空闲；wipe 会清掉已装 App | 先清 `E:\android\apk*` |
| VM 重启后 App Detector（:8765）没起来 | `Start-ScheduledTask ngfwweb`（需要用户已登录）；`gverify` 查询失败第 3 次会自动尝试 |
| APKPure 首个版本常是 armeabi-v7a only | `arm64alt.py` + `redl.py` |
| VM 经代理下载 APKPure 卡住 | 在 Mac 下载，用 http.server 传到 VM |
| `activateDetectors` 调用超时 | 继续轮询 `getDetectorList`（`fmc50.py activate` 已处理） |
| 浏览器里的 Deploy 进度卡住 | 以 REST `deployment/jobhistories` 为准（`fmc50.py forcedeploy`） |
| FMC 内置名存在但不识别移动端流量 | 实测 0 命中就做 `_Mobile` Lua |
| Windows 与 FMC 时钟偏差 | 用 FMC HTTP `Date` 头校准（App Detector 内置） |
| PowerShell 路径写在 `python -c` 字符串里被转义 | 写成脚本文件，用 raw string |
| `stop_bash` 不一定杀掉子 Python 进程 | `ps` 查 PID 后 kill |

---

## 10. 工具清单

### pipeline/（Mac 侧，驱动 VM/模拟器/FMC）
| 文件 | 作用 |
|---|---|
| `labcfg.py` | 统一读取 `config/lab.env` 的地址和凭据、项目路径 |
| `droid.py` | WinRM：`ps()`（带超时）、`adb()`、`shell()`、`screenshot()`、`pull()` |
| `econsole.py` | 模拟器控制台（5554）命令，例如关机 |
| `android_pcap_to_lua.py` | pcap + 根域名 → Lua（调用项目 `LuaRenderer`），输出 summary JSON |
| `pcapdroid-v2.0.2.lua` | tshark 插件，解析 PCAPdroid 扩展 |
| `vm_smb.py` / `android_smb.py` | SMB 传文件到 VM |
| `android_winrm.py` | 执行一个 PowerShell 脚本文件 |
| `android_esxi_probe.py` / `android_esxi_reconfig.py` | 只读查看 / 调整 VM 资源（调整需用户同意并 `labctl change esxi`） |
| `fmc_odp_grep.py` | SSH 到 FMC 查 ODP 内置规则里是否已有某域名 |
| `new_market.sh` | 以 `hk/` 为模板新建一轮目录 |
| `hk/` | **完整的一轮模板**：`cap.py` `gverify.py` `app_ncap.py` `emu.py` `run_emu.ps1` `fmc50.py` `gen.sh` `sni.py` `publish50.py` + `market.json` `apps.py` `results.py` `pkgs/meta/builtin/info.json` |
| `games/` | 手游轮次的抓包脚本和模拟器启动脚本 |
| `android_*.ps1`、`android_pilot_*`、`verify50.py`、`find_apk_urls.py`、`yyb_urls.py` | 早期轮次（VM 环境搭建、PCAPdroid pilot、中国 Top50/100、应用宝下载）的脚本，保留备查 |

### apk_tools/（Mac 侧，下载、截图、证据、发布；都需要 `MARKET=<m>`）
| 文件 | 作用 |
|---|---|
| `mkt.py` | 当前一轮的上下文（`MARKET`、目录、`apps.py`） |
| `mkjson.py` | 由 `apps.py` 生成/合并 `pkgs.json`、`builtin.json`、`meta.json`，检查名字 |
| `fmcapps.py` | 拉取 FMC 全部应用名 → `work/<m>/fmc_apps.json` |
| `apkp.py` / `dlall.py` | APKPure API 下载 |
| `prep.py` | 按 ABI 规则打包 `<App>.zip` |
| `rz.py` / `arm64alt.py` / `redl.py` | 列出 XAPK 内容（HTTP Range）、找 64 位版本、重新下载 |
| `vmfetch.py` | VM 从 Mac http.server 拉取 zip |
| `fmcshot.py` / `detrow.py` | Playwright 截 FMC Detector 列表和事件查询页 |
| `build_ev.py` | 生成 `evidence/apps.json` 和裁剪后的截图 |
| `putlua.py` | Lua 传到 VM 供发布 |
| `clean.py` | 卸载 App、停模拟器 |

> `mkjson.py`、`arm64alt.py`、`vmfetch.py`、`new_market.sh` 和参数化改动是 2026-11-26 整理时新增的：前两者已离线测试，`vmfetch.py` 尚未在 lab 上跑过，首次使用请留意。

---

## 11. 历次验证记录

| 轮次 | 时间 | 模式 | 结果 | 证据 |
|---|---|---|---|---|
| 招商证券基线 | 2026-10 | A | TdxW / CMS 命中 | `presentation/NGFW_App_Detector_技术介绍.pptx` |
| 券商 PC 客户端 Top5 | 2026-11-11 | A | 中信、国泰海通、华泰、广发、银河 5 个新 Lua 全部命中 | `presentation/券商App验证证据.pptx` |
| 中国视频 App Top10 | 2026-11-12 | A + C | 6 个内置；抖音、西瓜、咪咕、央视频 4 个新 Lua 命中 | `presentation/视频App验证证据.pptx` |
| 中国安卓 Top20 | 2026-11-13 | B（PCAPdroid） | 14 内置；拼多多、高德、滴滴、饿了么 4 个新 Lua | `presentation/安卓App验证证据.pptx` |
| 中国安卓 Top50 | 2026-11-15 | B | 26 内置、6 库中已有、15 个新生成（14 个 Detector）、3 个反模拟器 | `presentation/安卓Top50App验证证据.pptx` |
| 中国安卓 51–100 | 2026-11-15 | B | 14 内置、1 库中已有、18 个新 Lua、17 个失败 | `presentation/安卓Top100App验证证据.pptx` |
| 安卓手游 Top30 | 2026-11-16 | B | 13 个新 Lua、17 个失败 | `presentation/安卓Top30手游验证证据.pptx` |
| Go Lua Importer | 2026-11 | — | 导入+激活约 100 秒生效，Snort 3 不重启 | `NGFW_lua_importer/` |
| **香港 Top50** | 2026-11-17 | B | 18 新 Lua、15 内置、2 识别为母应用、1 不做、14 失败 | `runs/2026-11_hk/` |

更早阶段的详细经验见 `history/checkpoints_001-046_digest.md`。

---

## 12. 待改进

- `vmfetch.py` 首次在 lab 上验证。
- `info.json`（发布用规则摘要）仍是手填，可以从 `*.summary.json` 自动生成。
- Windows 进程模式（A）目前靠 App Detector Web UI 操作，还没有像 Android 一样的批量脚本。
- 银行/政府类 App 需要非 root 或真机方案才能覆盖。
