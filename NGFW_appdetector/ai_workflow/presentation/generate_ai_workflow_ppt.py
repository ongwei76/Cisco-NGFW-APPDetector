"""AI × NGFW App Detector — verified workflow training deck (zh + en, page-aligned).

Run:
    python generate_ai_workflow_ppt.py
Outputs (same folder):
    AI_NGFW_AppDetector_Workflow_中文.pptx
    AI_NGFW_AppDetector_Workflow_EN.pptx
Then export/lint:
    python ~/.copilot/deck-kit/export_check.py AI_NGFW_AppDetector_Workflow_EN.pptx --pdf-out AI_NGFW_AppDetector_Workflow_EN.pdf

Source of truth: ../AI_WORKFLOW.md (+ ../README.md, ../runs/2026-11_hk/, ../history/checkpoints_001-046_digest.md).
Mode: training (audience: Cisco SEs / engineers). No IPs, hostnames, passwords or tokens on any slide.
Screenshots: assets/ holds redacted copies (source/destination IP columns removed from the FMC event crop).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".copilot/deck-kit"))
from deck_kit import *  # noqa: E402,F403

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
FOOTER = ("Cisco Secure Firewall · NGFW App Detector · AI 工作流", "Cisco Secure Firewall · NGFW App Detector · AI workflow")


# ── 01 cover ────────────────────────────────────────────────────────────────
def s_cover(d):
    s = d.title_slide(
        d.T("SE 培训 · 已验证", "SE TRAINING · VERIFIED"), "AI × NGFW App Detector",
        d.T("用 AI 批量补齐防火墙应用识别", "Using AI to close firewall app-ID gaps at scale"),
        d.T("已验证的工作流与工具包 · 7 轮实测 · 适用于任何 AI 助手",
            "A verified workflow & toolkit · 7 lab rounds · works with any AI assistant"),
        notes=d.T(
            "开场：今天这节培训讲的是一套已经跑通的方法——让 AI 助手驱动 NGFW App Detector，端到端地补齐 Cisco Secure Firewall 的应用识别缺口。"
            "整个链路是：AI 跑 App、抓流量、生成自定义 Lua（OpenAppID Detector）、在 FMC 上导入激活、二次运行在 FTD 上确认真实命中、生成证据 PPT，最后发布到共享 GitHub Lua 库。"
            "这套方法在 2026 年 10 月到 11 月的 7 轮实测中跑通，大约 76 个新 Lua 在 FTD 上实测命中，共享库现在有 78 个 Lua。"
            "要强调的是：方法不绑定某一个 AI，Copilot、Claude Code、Codex、Cursor 都可以，因为所有知识都写在 AI_WORKFLOW.md 里，AI 读完就能接手。"
            "今天的结构：先讲缺口和思路，再讲组件和三种采集模式，然后用三页把标准流程和命令过一遍，接着是 Lua 规则、验证标准、人工节点和硬规则，最后看结果、香港 Top50 案例和怎么把它交给你自己的 AI。"
            "听完之后，大家应该能拿着这个目录和开场提示词，在自己的 lab 里跑一轮新市场。",
            "Opening: this training covers a method that already works end to end — an AI assistant drives NGFW App Detector to close "
            "application-identification gaps on Cisco Secure Firewall. The chain: the AI runs apps, captures traffic, generates custom Lua "
            "(OpenAppID detectors), imports and activates them on FMC, re-runs the apps to confirm live hits on FTD, builds an evidence deck "
            "and publishes to a shared GitHub Lua library. It was verified across 7 lab rounds in Oct–Nov 2026: about 76 new Lua detectors "
            "hit live on FTD, and the shared library now holds 78. The method is not tied to one AI — Copilot, Claude Code, Codex or Cursor all "
            "work, because everything is written down in AI_WORKFLOW.md. Agenda: the gap and the idea, components and capture modes, three "
            "pages of the standard flow with commands, Lua rules, verification, human checkpoints, guardrails, pitfalls, results, the Hong Kong "
            "case and how to hand this to your own AI."))
    d.step_row(s, [("smartphone", BLUE, d.T("跑 App", "Run apps"), None),
                   ("scan-search", BLUE, d.T("抓包", "Capture"), None),
                   ("file-code", BLUE, d.T("生成 Lua", "Generate Lua"), None),
                   ("upload", BLUE, d.T("导入 FMC", "Import to FMC"), None),
                   ("badge-check", GREEN, d.T("实测命中", "Verify hits"), None),
                   ("share-2", GREEN, d.T("发布共享库", "Publish"), None)],
               x0=1.75, gap=1.95, cy=4.75, d=0.8, label_w=1.8, title_size=13)


# ── 02 the gap ─────────────────────────────────────────────────────────────
def s_gap(d):
    s = d.new_slide(d.T("缺口：内置识别覆盖不全，手工补很慢", "The gap: built-in coverage is incomplete, manual fixes are slow"),
                    d.T("本地、区域和移动 App 常常没有被 OpenAppID 内置库识别",
                        "Local, regional and mobile apps are often missing from built-in OpenAppID"),
                    notes=d.T(
                        "这一页讲为什么要做这件事。Cisco Secure Firewall 的 OpenAppID 内置库对全球主流应用覆盖很好，但对本地、区域性的 App 和很多移动 App 覆盖不足。"
                        "还有一种更隐蔽的情况：FMC 里有这个内置名，但它并不识别移动端 App 的流量。香港这一轮里 Spotify、KKBOX、Google Maps 就是这样，实测 0 命中，最后做了 _Mobile 版本的 Lua。"
                        "右边是手工补一个 Detector 要做的事情：抓包、在一堆域名里找出 App 自有的根域名、排除 CDN 和广告统计 SDK、在 FMC 导入激活部署、再重跑 App 去确认命中、最后截图留证据。"
                        "每一步都不难，但每个 App 都要重复一遍，一个市场 50 个 App 就是体力活，而且容易出错，比如把 CDN 写进规则导致误识别。"
                        "右下两个数字来自香港 Top50：50 个 App 里只有 15 个被内置名实测命中，18 个需要新做 Lua。"
                        "过渡：所以思路是把重复劳动交给 AI 和脚本，人只做决策。",
                        "Why we do this. Built-in OpenAppID covers global mainstream apps well, but many local, regional and mobile apps are not "
                        "identified. A subtler case: FMC has a built-in name, yet it does not label the mobile app's traffic — in the Hong Kong round, "
                        "Spotify, KKBOX and Google Maps had zero hits and got _Mobile Lua detectors. On the right is what one manual detector takes: "
                        "capture, find the app-owned root domains, exclude CDN and ad/analytics SDKs, import/activate/deploy on FMC, re-run the app to "
                        "confirm a hit, and save screenshots. None of it is hard, but it repeats for every app, and mistakes such as a CDN domain in a "
                        "rule cause false matches. The numbers come from Hong Kong Top 50: only 15 of 50 apps hit on a built-in name, 18 needed a new "
                        "Lua. Transition: hand the repetition to AI and scripts, keep humans on decisions."))
    d.bullet_card(s, 0.6, 1.75, 4.55, 4.25, "book-x", RED, d.T("内置库的缺口", "Gaps in the built-in library"), [
        (d.T("本地、区域、移动 App 常不在内置库", "Local, regional and mobile apps often missing"),
         d.T("券商、视频、外卖、交通、手游…", "Brokers, video, delivery, transit, games…")),
        (d.T("内置名存在，也不一定识别移动端流量", "A built-in name may still miss mobile traffic"),
         d.T("例：Spotify、KKBOX、Google Maps", "e.g. Spotify, KKBOX, Google Maps")),
        (d.T("识别不到 → 访问控制策略无法精确管控", "Not identified → no precise access policy"), None),
    ], size=13.5, gap=0.28)
    d.bullet_card(s, 5.4, 1.75, 4.25, 4.25, "clock", ORANGE, d.T("手工补一个 Detector", "One detector by hand"), [
        d.T("抓包，找出 App 自有的 SNI / Host", "Capture, find app-owned SNI / Host"),
        d.T("排除 CDN、广告统计 SDK、集团域名", "Exclude CDN, SDK and group domains"),
        d.T("FMC 导入、激活、部署", "Import, activate, deploy on FMC"),
        d.T("重跑 App，确认连接事件命中", "Re-run the app, confirm a live event"),
        d.T("截图留证据，每个 App 重复一遍", "Screenshot evidence — repeat per app"),
    ], size=13.5, gap=0.28)
    d.stat_card(s, 9.9, 1.75, 2.83, 2.0, "15 / 50", d.T("香港 Top50 内置名实测命中", "HK Top 50 hit on a built-in name"), BLUE)
    d.stat_card(s, 9.9, 4.0, 2.83, 2.0, "18 / 50", d.T("香港 Top50 需要新 Lua", "HK Top 50 needed a new Lua"), ORANGE)
    d.banner(s, "target", d.T("缺口真实存在，且每个 App 都要重复同样的步骤 → 适合交给 AI",
                              "The gap is real and every app repeats the same steps → a job for AI"), accent=ORANGE)


# ── 03 core idea ───────────────────────────────────────────────────────────
def s_idea(d):
    s = d.new_slide(d.T("核心思路：三个角色，六条原则", "Core idea: three roles, six principles"),
                    d.T("AI 当操作员，App Detector 当翻译，FMC/FTD 当裁判",
                        "AI is the operator, App Detector the translator, FMC/FTD the referee"),
                    notes=d.T(
                        "这一页是整套方法的灵魂。上面三个角色：AI 当操作员，负责跑 App、抓包、调用脚本、整理证据；App Detector 当翻译，把流量里的 SNI、Host 翻译成 Lua 规则；FMC/FTD 当裁判，只有 FMC 连接事件里出现 Web App 等于 Lua 名，才算通过。"
                        "下面六条原则逐条讲：第一，先查缺口再补，内置名也要实测，因为内置名不等于真能识别移动端；第二，规则只用 App 自有域名，CDN、广告统计 SDK、母公司共享域名一律排除，否则会误识别别的 App；"
                        "第三，导入激活后必须重新跑一次 App 验证；第四，证据齐全，每个 App 都有客户端截图、Detector 截图、事件截图和事件 JSON；"
                        "第五，人只做决策，清单、范围、发布、冲突由人拍板，重复操作交给 AI；第六，失败也是结果，反模拟器、root 检测、存根 APK 都如实记录，绝不伪造证据。"
                        "过渡：下一页把这些串成一个闭环。",
                        "This is the heart of the method. Three roles: the AI is the operator — it runs apps, captures, calls scripts and assembles "
                        "evidence; App Detector is the translator — it turns SNI and Host names into Lua rules; FMC/FTD is the referee — a detector "
                        "passes only when an FMC Connection Event shows Web App equal to the Lua name. Six principles: fill gaps only, but test "
                        "built-ins too, since a built-in name does not guarantee mobile coverage; use app-owned domains only and exclude CDN, "
                        "ad/analytics SDKs and parent-group domains; verify by re-running the app after activation; keep full evidence — client, "
                        "detector and event screenshots plus event JSON; humans decide scope, publishing and conflicts while AI executes; and failures "
                        "are results — anti-emulator, root detection or stub APKs are recorded, never faked. Next: the closed loop."))
    roles = [("bot", BLUE, d.T("AI = 操作员", "AI = operator"), d.T("跑 App、抓包、调脚本、整理证据", "Runs apps, captures, calls scripts")),
             ("file-code", BLUE, d.T("App Detector = 翻译", "App Detector = translator"), d.T("SNI / Host → Lua 规则", "SNI / Host → Lua rules")),
             (None, GREEN, d.T("FMC / FTD = 裁判", "FMC / FTD = referee"), d.T("连接事件 Web App = Lua 名才算过", "Pass = event Web App equals Lua"))]
    w = 3.85
    for i, (ic, col, t, sub) in enumerate(roles):
        x = 0.6 + i * (w + 0.29)
        d.card(s, x, 1.75, w, 1.35)
        if ic:
            d.badge(s, ic, x + 0.6, 2.42, 0.75, fill=col)
        else:
            d.product_badge(s, "cisco-firewall", x + 0.6, 2.42, 0.8, ring=GREEN)
        d.text(s, t, x + 1.15, 1.95, w - 1.3, 0.4, size=17, color=WHITE)
        d.text(s, sub, x + 1.15, 2.4, w - 1.3, 0.55, size=12, color=MUTED)
        if i < 2:
            d.arrow(s, x + w + 0.03, 2.42, x + w + 0.26, 2.42)
    pr = [("search", d.T("先查缺口，再补", "Fill gaps only"), d.T("内置名也实测，只给没识别的生成", "Test built-ins too; Lua only for misses")),
          ("fingerprint", d.T("只用 App 自有域名", "App-owned domains only"), d.T("排除 CDN、SDK、集团共享域名", "No CDN, SDK or parent-group domains")),
          ("refresh-cw", d.T("二次运行验证", "Verify by re-run"), d.T("导入激活后重跑 App 看命中", "Re-run the app after activation")),
          ("file-check", d.T("证据齐全", "Full evidence"), d.T("3 张截图 + 事件 JSON", "3 screenshots + event JSON")),
          ("user-check", d.T("人做决策，AI 执行", "Humans decide, AI executes"), d.T("清单、范围、发布、冲突由人拍板", "List, scope, publish, conflicts")),
          ("circle-x", d.T("失败也是结果", "Failures are results"), d.T("如实记录原因，绝不伪造证据", "Record the reason, never fake it"))]
    cw, ch = 3.85, 1.3
    for k, (ic, t, sub) in enumerate(pr):
        r, c = divmod(k, 3)
        x, y = 0.6 + c * (cw + 0.29), 3.3 + r * (ch + 0.12)
        d.card(s, x, y, cw, ch)
        d.badge(s, ic, x + 0.5, y + ch / 2, 0.6, fill=ORANGE if ic == "circle-x" else CARD_2, color="cyan" if ic != "circle-x" else "white")
        d.text(s, t, x + 0.95, y + 0.2, cw - 1.05, 0.4, size=15, color=WHITE)
        d.text(s, sub, x + 0.95, y + 0.62, cw - 1.05, 0.55, size=12, color=MUTED)
    d.banner(s, "scale", d.T("只以 FMC 连接事件实测命中为准 —— 跑不起来就如实记为失败",
                             "Only a live FMC Connection Event counts — if an app won't run, record it as failed"), accent=GREEN)


# ── 04 closed loop ─────────────────────────────────────────────────────────
def s_loop(d):
    s = d.new_slide(d.T("闭环：从清单到共享库的 10 步", "The closed loop: 10 steps from list to library"),
                    d.T("每一步都有对应脚本；人工只在清单和发布两处拍板",
                        "Every step has a script; humans sign off on the list and on publishing"),
                    notes=d.T(
                        "这是整个闭环。上排从左到右：第 1 步选清单，市场 Top N，由人确认；第 2 步查 FMC 内置库，用 fmcapps.py 拉内置名，再用 gverify 实测内置名是否命中；"
                        "第 3 步跑 App 加抓包，cap.py 在模拟器里用 tcpdump 抓 150 秒；第 4 步提取 App 自有的 SNI 和 Host，用 sni.py 看根域名，同时排除 CDN；第 5 步 gen.sh 生成 Lua。"
                        "下排从右到左：第 6 步 fmc50.py 导入、激活、强制部署；第 7 步二次运行验证，CUSTOM=1 的 gverify 去 FMC 查 web_app 等于 Lua 名的事件；"
                        "第 8 步 fmcshot 截图、build_ev 生成 apps.json；第 9 步交给 deck generator 出证据 PPT；第 10 步人工确认后用 publish50 发布到共享库。"
                        "发布之后共享库里多了新 Lua，下一轮选清单时就要把它们当作已有，这就是左边那条回路。"
                        "后面三页会逐段展开这些命令。",
                        "The whole loop. Top row, left to right: 1 pick the list — market Top N, confirmed by a human; 2 check FMC built-ins — fmcapps.py "
                        "pulls built-in names and gverify tests whether they hit; 3 run the app and capture — cap.py runs tcpdump on the emulator for 150 s; "
                        "4 extract app-owned SNI/Host with sni.py, excluding CDNs; 5 gen.sh generates the Lua. Bottom row, right to left: 6 fmc50.py imports, "
                        "activates and force-deploys; 7 re-run and verify — gverify with CUSTOM=1 looks for FMC events where web_app equals the Lua name; "
                        "8 fmcshot screenshots and build_ev writes apps.json; 9 the deck generator builds the evidence deck; 10 after human approval, "
                        "publish50 publishes to the shared library. The next round starts from a bigger library — that is the loop on the left. "
                        "The next three slides walk through the commands."))
    d.card(s, 0.6, 1.75, 12.13, 4.3)
    top = [("list-ordered", BLUE, d.T("选清单", "Pick list"), d.T("Top N · 人确认", "Top N · human OK")),
           ("search", BLUE, d.T("查内置库", "Check built-ins"), "fmcapps · gverify"),
           ("smartphone", BLUE, d.T("跑 App + 抓包", "Run + capture"), "cap.py · tcpdump"),
           ("scan-search", BLUE, d.T("提取自有域名", "App-owned SNI"), "sni.py"),
           ("file-code", BLUE, d.T("生成 Lua", "Generate Lua"), "gen.sh")]
    bot = [("upload", BLUE, d.T("导入·激活·部署", "Import & deploy"), "fmc50.py"),
           ("badge-check", GREEN, d.T("二次运行验证", "Re-run & verify"), "CUSTOM=1 gverify"),
           ("image", BLUE, d.T("截图 + JSON", "Shots + JSON"), "fmcshot · build_ev"),
           ("presentation", BLUE, d.T("证据 PPT", "Evidence deck"), "deck generator"),
           ("share-2", GREEN, d.T("发布共享库", "Publish library"), "publish50.py")]
    xs = [1.65 + i * 2.4 for i in range(5)]
    dd, cy1, cy2, lw = 0.72, 2.6, 4.85, 2.0

    def node(n, item, cx, cy):
        ic, col, t, sub = item
        d.text(s, f"{n:02d}", cx - 0.4, cy - dd / 2 - 0.4, 0.8, 0.3, size=11, color=CYAN, align=PP_ALIGN.CENTER)
        d.badge(s, ic, cx, cy, dd, fill=col)
        d.text(s, t, cx - lw / 2, cy + dd / 2 + 0.06, lw, 0.32, size=13, color=WHITE, align=PP_ALIGN.CENTER)
        d.text(s, sub, cx - lw / 2, cy + dd / 2 + 0.38, lw, 0.3, size=10.5, color=MUTED, align=PP_ALIGN.CENTER, font=MONO)

    for i, it in enumerate(top):
        node(i + 1, it, xs[i], cy1)
        if i < 4:
            d.arrow(s, xs[i] + dd / 2 + 0.08, cy1, xs[i + 1] - dd / 2 - 0.08, cy1)
    for i, it in enumerate(bot):
        cx = xs[4 - i]
        node(i + 6, it, cx, cy2)
        if i < 4:
            d.arrow(s, cx - dd / 2 - 0.08, cy2, xs[3 - i] + dd / 2 + 0.08, cy2)
    # right elbow 05 → 06
    rx = 12.4
    d.line(s, xs[4] + dd / 2 + 0.06, cy1, rx, cy1, color=CYAN, width=2.25)
    d.line(s, rx, cy1, rx, cy2, color=CYAN, width=2.25)
    d.arrow(s, rx, cy2, xs[4] + dd / 2 + 0.08, cy2)
    # left loop-back 10 → 01 (next round, dashed)
    lx = 0.85
    d.line(s, xs[0] - dd / 2 - 0.06, cy2, lx, cy2, color=CYAN, width=1.5)
    d.line(s, lx, cy2, lx, cy1, color=CYAN, width=1.5)
    d.arrow(s, lx, cy1, xs[0] - dd / 2 - 0.08, cy1, width=1.5, dash=True)
    d.banner(s, "refresh-cw", d.T("发布后共享库变大，下一轮从更大的库出发 —— 这就是闭环",
                                  "Each round grows the shared library; the next round starts from it — that is the loop"), accent=CYAN)


# ── 05 components & topology ───────────────────────────────────────────────
def s_topo(d):
    s = d.new_slide(d.T("组件与 lab 拓扑", "Components & lab topology"),
                    d.T("Mac 上的 AI 通过 WinRM、adb 和 FMC 接口驱动整个 lab",
                        "The AI on the Mac drives the lab through WinRM, adb and FMC interfaces"),
                    notes=d.T(
                        "组件和拓扑。左上是 Mac，AI 和本目录的脚本都跑在这里，tshark 分析、Lua 生成、Playwright 截图和 PPT 也在 Mac 上。"
                        "Mac 通过 WinRM 控制 Windows 测试 VM，脚本是 pipeline/droid.py；VM 上跑 Windows 客户端、Android 14 模拟器（AVD Modern34），以及 App Detector Web，端口 8765，以计划任务 ngfwweb 运行。"
                        "VM 再通过 adb 控制模拟器。VM 的流量经过 FTD，FTD 是 Snort 3 routed 模式，产生识别结果；FMC 10.0.1 负责导入激活 Detector，并提供连接事件。"
                        "Mac 对 FMC 有两条路：用 FMC UI 私有接口导入和激活 Detector，用 FMC REST 做部署，部署状态以 deployment/jobhistories 为准。"
                        "右下是共享库：Lua Maintainer 跑在 Mac 的 8780，持有 GitHub token，只给维护者用；Go Lua Importer 在 8790，给用户从共享库一键导入 FMC，AI 不要动用户正在运行的 Importer。"
                        "注意：页面上故意不放任何 IP 和凭据，地址和凭据都在 config/lab.env，由 labcfg.py 读取。",
                        "Components. The Mac runs the AI and the scripts in this folder, plus tshark analysis, Lua generation, Playwright screenshots and "
                        "decks. It drives the Windows test VM over WinRM via pipeline/droid.py. The VM runs Windows clients, an Android 14 emulator (AVD "
                        "Modern34) and App Detector Web on port 8765 as the scheduled task ngfwweb; adb on the VM drives the emulator. VM traffic passes "
                        "through FTD (Snort 3, routed), which produces the identification; FMC 10.0.1 imports and activates detectors and provides "
                        "Connection Events. The Mac talks to FMC two ways: FMC UI private calls to import and activate, and FMC REST to deploy, trusting "
                        "deployment/jobhistories. Sharing: the Lua Maintainer on :8780 holds the GitHub token and is maintainer-only; the Go Lua Importer "
                        "on :8790 lets users import from the library — the AI must not touch a user's running Importer. No IPs or credentials on the "
                        "slide; they live in config/lab.env, read by labcfg.py."))
    d.card(s, 0.6, 1.75, 7.85, 4.3)
    X = [1.7, 4.5, 7.3]
    y1, y2, bd = 2.5, 4.55, 0.78
    nodes = [("laptop", BLUE, X[0], y1, d.T("Mac · AI + 脚本", "Mac · AI + scripts"), "tshark · Playwright"),
             ("monitor", BLUE, X[1], y1, d.T("Windows 测试 VM", "Windows test VM"), "App Detector :8765"),
             ("smartphone", BLUE, X[2], y1, d.T("Android 14 模拟器", "Android 14 emulator"), "adb root · tcpdump"),
             ("server-cog", BLUE, X[0], y2, "FMC 10.0.1", d.T("导入·激活·事件", "import · events")),
             (None, None, X[1], y2, "FTD · Snort 3", "routed"),
             ("library", GREEN, X[2], y2, d.T("GitHub 共享库", "GitHub library"), "Maintainer :8780")]
    for ic, col, cx, cy, t, sub in nodes:
        if ic:
            d.badge(s, ic, cx, cy, bd, fill=col)
        else:
            d.product_badge(s, "cisco-firewall", cx, cy, 0.85)
        d.text(s, t, cx - 1.2, cy + 0.5, 2.4, 0.32, size=13, color=WHITE, align=PP_ALIGN.CENTER)
        d.text(s, sub, cx - 1.2, cy + 0.82, 2.4, 0.3, size=10.5, color=MUTED, align=PP_ALIGN.CENTER, font=MONO)
    r = bd / 2 + 0.1
    d.arrow(s, X[0] + r, y1, X[1] - r, y1)
    d.text(s, "WinRM", X[0] + r, y1 - 0.42, X[1] - X[0] - 2 * r, 0.3, size=10.5, color=CYAN, align=PP_ALIGN.CENTER, font=MONO)
    d.arrow(s, X[1] + r, y1, X[2] - r, y1)
    d.text(s, "adb", X[1] + r, y1 - 0.42, X[2] - X[1] - 2 * r, 0.3, size=10.5, color=CYAN, align=PP_ALIGN.CENTER, font=MONO)
    vy1, vy2 = y1 + 1.2, y2 - 0.55
    d.arrow(s, X[1], vy1, X[1], vy2)
    d.text(s, d.T("App 流量", "app traffic"), X[1] + 0.12, vy1 + 0.02, 1.3, 0.3, size=10.5, color=CYAN)
    d.arrow(s, X[0], vy1, X[0], vy2)
    d.text(s, d.T("导入/激活/部署", "import/activate/deploy"), X[0] + 0.12, vy1 + 0.02, 2.0, 0.3, size=10.5, color=CYAN)
    d.arrow(s, X[1] - 0.55, y2, X[0] + r, y2)
    d.text(s, d.T("事件", "events"), X[0] + r, y2 - 0.4, X[1] - 0.55 - X[0] - r, 0.3, size=10.5, color=CYAN, align=PP_ALIGN.CENTER)
    d.bullet_card(s, 8.7, 1.75, 4.03, 4.3, "cable", BLUE, d.T("怎么连起来", "How it is wired"), [
        (d.T("WinRM 控制 VM，VM 上 adb 控制模拟器", "WinRM drives the VM; adb on the VM drives the emulator"), "pipeline/droid.py"),
        (d.T("FMC UI 私有接口导入、激活 Detector", "FMC UI private calls import & activate"), "FmcUiClient / FmcDetectorImporter"),
        (d.T("FMC REST 部署，以 jobhistories 为准", "FMC REST deploys; trust jobhistories"), None),
        (d.T("App Detector 查 FMC 连接事件", "App Detector queries FMC events"), "POST /api/fmc/search"),
    ], size=12, gap=0.14)
    d.banner(s, "key-round", d.T("地址和凭据只在 config/lab.env（gitignored），幻灯片和文档里一律不出现",
                                 "Addresses and credentials live only in config/lab.env (gitignored) — never on slides or docs"),
             accent=BLUE)


# ── 06 capture modes ───────────────────────────────────────────────────────
def s_modes(d):
    s = d.new_slide(d.T("三种采集模式", "Three capture modes"),
                    d.T("按客户端类型选择；Android 模拟器是主力", "Pick by client type; the Android emulator is the workhorse"),
                    notes=d.T(
                        "三种采集模式。A 是 Windows 进程模式，适合 PC 客户端，比如券商和视频客户端：在 VM 上装客户端，在 App Detector Web 里选进程、开始采集，它用 Socket 表加 FMC 事件按五元组和时间关联，"
                        "检查 Host 和 SNI、排除 CDN 后生成 Lua，可以从 /api/lua/<NAME>.lua 下载。券商 Top5 和视频 Top10 用的是这个模式。"
                        "B 是主力：VM 里的 Android 14（API 34）模拟器，adb root 之后直接 tcpdump 抓包，Mac 上用 tshark 提取 SNI，再用 android_pcap_to_lua.py 生成 Lua。早期用的是 Android 11 加 PCAPdroid 按 UID 抓包。"
                        "中国 Top20、Top50、Top100、手游 Top30、香港 Top50 都是这个模式。"
                        "C 是兜底：客户端在 VM 里跑不起来时，用浏览器访问官网或网页版，产生同域流量来验证，央视频就是这么做的。"
                        "要提醒：模式 A 目前还靠 Web UI 操作，没有像 Android 一样的批量脚本，这是待改进项。",
                        "Three capture modes. A, Windows process: for PC clients such as brokers and video apps. Install the client on the VM, pick the "
                        "process in App Detector Web and start capture; it correlates the socket table with FMC events by 5-tuple and time, you check "
                        "Host/SNI, exclude CDNs and generate the Lua, downloadable from /api/lua/<NAME>.lua. Used for the broker Top 5 and video Top 10. "
                        "B is the workhorse: an Android 14 (API 34) emulator inside the VM, adb root plus tcpdump, tshark on the Mac to extract SNI, then "
                        "android_pcap_to_lua.py. Earlier rounds used Android 11 with PCAPdroid per-UID capture. Used for China Top 20/50/100, games "
                        "Top 30 and Hong Kong Top 50. C is the fallback: when a client can't run in the VM, browse the official site or web version to "
                        "produce same-domain traffic — that is how YangShiPin was verified. Note: mode A is still driven through the web UI; there is "
                        "no batch script yet."))
    w, gap = 3.9, 0.215
    cards = [
        ("monitor", BLUE, d.T("A · Windows 进程", "A · Windows process"), [
            (d.T("PC 客户端：券商、视频", "PC clients: brokers, video"), None),
            (d.T("App Detector Web 选进程、开始采集", "Pick the process in App Detector Web"), None),
            (d.T("Socket 表 + FMC 事件按五元组/时间关联", "Socket table + FMC events by 5-tuple/time"), None),
            (d.T("已验证：券商 Top5、视频 Top10", "Verified: brokers Top 5, video Top 10"), "/api/lua/<NAME>.lua"),
        ]),
        ("smartphone", GREEN, d.T("B · Android 模拟器（主力）", "B · Android emulator (main)"), [
            (d.T("VM 内 Android 14（API 34）", "Android 14 (API 34) inside the VM"), d.T("早期：Android 11 + PCAPdroid", "Earlier: Android 11 + PCAPdroid")),
            (d.T("adb root + tcpdump 抓包", "adb root + tcpdump capture"), None),
            (d.T("Mac 上 tshark 提 SNI → 生成 Lua", "tshark on Mac → SNI → Lua"), "android_pcap_to_lua.py"),
            (d.T("已验证：中国 Top20–100、手游、香港", "Verified: China Top 20–100, games, HK"), None),
        ]),
        ("globe", BLUE, d.T("C · 网页兜底", "C · Web fallback"), [
            (d.T("客户端无法在 VM 运行时使用", "When the client can't run in the VM"), None),
            (d.T("浏览器访问官网或网页版", "Browse the official site / web version"), None),
            (d.T("产生同域流量来验证 Lua", "Same-domain traffic verifies the Lua"), None),
            (d.T("已验证：央视频", "Verified: YangShiPin"), None),
        ]),
    ]
    for i, (ic, col, t, bl) in enumerate(cards):
        x = 0.6 + i * (w + gap)
        d.bullet_card(s, x, 1.75, w, 4.3, ic, col, t, bl, size=13, gap=0.24, title_size=16)
        if col == GREEN:
            d.card(s, x, 1.75, w, 4.3, fill=None, line=GREEN, line_width=1.5)
    d.banner(s, "smartphone", d.T("手机 App 用模式 B；PC 客户端用 A；都跑不起来再用 C 兜底",
                                  "Mobile apps → B; PC clients → A; if neither runs, fall back to C"), accent=GREEN)


# ── 07 flow part 1 ─────────────────────────────────────────────────────────
def s_flow1(d):
    s = d.new_slide(d.T("标准流程 ①：立项、清单、APK", "Standard flow ①: scope, list, APKs"),
                    d.T("第 4.1–4.3 节 · 只有拉 FMC 内置名和传 VM 需要认领 lab",
                        "Sections 4.1–4.3 · only FMC lookup and VM transfer need a lab claim"),
                    notes=d.T(
                        "标准流程第一段：立项、清单和 APK。第一步是人工节点：选市场，参考 Similarweb 或 Google Play 地区榜单整理 50 个 App，然后和用户确认清单、是否全部上 FMC 验证（包括内置）、是否发布、发布备注、PPT 语言。"
                        "确认后用 new_market.sh 以 hk 为模板新建一轮，编辑 market.json 和 apps.py。注意 App 名必须匹配 ^[A-Za-z_]{1,15}$，不能有数字，因为它会直接成为 Lua 名。"
                        "然后 fmcapps.py 拉取 FMC 全部内置应用名，这一步要认领 fmc；mkjson.py 生成 pkgs、builtin、meta 三个 json 并检查名字冲突。"
                        "APK 全部在 Mac 上下载，因为 VM 经代理下载 APKPure 会卡在 0 字节。打包规则：保留全部非 ABI split，再加 x86_64 split，没有就用 arm64_v8a，缺 ABI split 会报 INSTALL_FAILED_MISSING_SPLIT。"
                        "arm64alt 和 redl 处理只有 armeabi-v7a 的情况。下载不到的写进 UNAVAILABLE，和用户确认替补。"
                        "最后 Mac 起 http.server，VM 用 vmfetch.py 拉取。注意 vmfetch.py 是 11 月 26 日整理时新增的，还没在 lab 上跑过，首次使用要留意。",
                        "Part one: scope, list and APKs. Step one is a human checkpoint: pick the market, build a list of 50 apps from Similarweb or "
                        "Google Play regional charts, and confirm with the user the list, whether all 50 are verified on FMC including built-ins, whether "
                        "to publish, the publish note and the deck language. Then new_market.sh clones the hk template; edit market.json and apps.py. "
                        "App names must match ^[A-Za-z_]{1,15}$ — no digits — because they become Lua names. fmcapps.py pulls every FMC app name (claim "
                        "fmc first); mkjson.py writes pkgs, builtin and meta json and checks name clashes. APKs are downloaded on the Mac because "
                        "APKPure downloads through the VM proxy stall at 0 bytes. Packing rule: keep all non-ABI splits plus x86_64, else arm64_v8a; a "
                        "missing ABI split gives INSTALL_FAILED_MISSING_SPLIT. arm64alt and redl handle armeabi-only first versions. Unavailable apps go "
                        "into UNAVAILABLE and the user picks replacements. Finally the VM pulls the zips from a Mac http.server with vmfetch.py — new on "
                        "Nov 26 and not yet run on the lab, so watch it the first time."))
    d.bullet_card(s, 0.6, 1.75, 5.75, 4.3, "clipboard-check", BLUE, d.T("步骤要点", "Key points"), [
        (d.T("人工确认：清单、是否全部上 FMC、是否发布", "Human OK: list, FMC scope, publish or not"),
         d.T("参考 Similarweb / Google Play 地区榜单", "From Similarweb / Google Play charts")),
        (d.T("new_market.sh 以 hk/ 为模板新建一轮", "new_market.sh clones the hk/ template"),
         d.T("App 名须匹配 ^[A-Za-z_]{1,15}$", "App names must match ^[A-Za-z_]{1,15}$")),
        (d.T("APK 在 Mac 下载：VM 经代理会卡 0 字节", "Download APKs on the Mac, not via VM proxy"),
         d.T("非 ABI split + x86_64（无则 arm64_v8a）", "Non-ABI splits + x86_64 (else arm64_v8a)")),
        (d.T("下载不到的写进 UNAVAILABLE，人选替补", "Unavailable → UNAVAILABLE, user picks swaps"),
         d.T("vmfetch.py 尚未在 lab 上跑过", "vmfetch.py not yet run on the lab")),
    ], size=13, gap=0.2)
    d.code_block(s, 6.6, 1.75, 6.13, 4.3,
                 "bash pipeline/new_market.sh sg\n"
                 "cd apk_tools\n"
                 "MARKET=sg $PY fmcapps.py    # claim fmc\n"
                 "MARKET=sg $PY mkjson.py     # pkgs/builtin/meta\n"
                 "MARKET=sg $PY dlall.py      # APKPure → www/\n"
                 "MARKET=sg $PY prep.py       # → pkg/<App>.zip\n"
                 "MARKET=sg $PY arm64alt.py   # armeabi-only?\n"
                 "MARKET=sg $PY redl.py\n"
                 "# Mac: cd work/sg/pkg && \\\n"
                 "#      python3 -m http.server 8899\n"
                 "PYTHONPATH=../pipeline MARKET=sg \\\n"
                 "  $PY vmfetch.py <Mac-VPN-IP>",
                 title=d.T("# 在 ai_workflow/ 下；PY=.venv-lab/bin/python", "# in ai_workflow/; PY=.venv-lab/bin/python"), size=12.5)
    d.banner(s, "circle-alert", d.T("注意：清单和范围先和用户确认，再动 lab；APK 一律在 Mac 下载",
                                    "Caveat: confirm list and scope before touching the lab; always download APKs on the Mac"),
             accent=ORANGE)


# ── 08 flow part 2 ─────────────────────────────────────────────────────────
def s_flow2(d):
    s = d.new_slide(d.T("标准流程 ②：抓包 → Lua → FMC → 验证", "Standard flow ②: capture → Lua → FMC → verify"),
                    d.T("第 4.4–4.6 节 · 需认领 fmc / ftd / win-test-host",
                        "Sections 4.4–4.6 · claim fmc / ftd / win-test-host first"),
                    notes=d.T(
                        "第二段是核心：抓包、生成 Lua、导入 FMC、验证。先说模拟器看门狗：emu.py 的 ensure() 在每个 App 前调用，模拟器没起来就用 run_emu.ps1 启动（Modern34，6 GB，4 核，带 http-proxy），等开机完成并 adb root。"
                        "第一步验内置：NOCAP=1 的 cap.py 只安装不抓包，gverify 跑 App 120 秒、等 60 秒，按 builtin.json 的 FMC 名查 web_app。0 条时回退为查 VM 源 IP 的全部事件，记录 seen_apps，用来判断是识别为母应用还是完全没识别；0 命中的内置 App 转入做 Lua。"
                        "第二步：cap.py 安装并抓包 150 秒，sni.py 看 SNI 根域名，gen.sh 用选定的根域名生成 Lua。"
                        "第三步：fmc50.py import、activate、forcedeploy。每次导入、激活、部署前都要 labctl change fmc 记录。"
                        "第四步：CUSTOM=1 的 gverify 二次运行验证。0 命中时，看 pcap 里的 SNI 是否被别的规则吃掉，调整根域名后 fmc50.py reimport。和内置名冲突的加 _Mobile 后缀，并在 pkgs、meta 补别名，在 results.py 的 NEW 里登记。",
                        "Part two is the core. The emulator watchdog: emu.py ensure() runs before every app; if the emulator is down it starts it with "
                        "run_emu.ps1 (Modern34, 6 GB, 4 cores, http-proxy), waits for boot and runs adb root. Step one tests built-ins: cap.py with "
                        "NOCAP=1 only installs; gverify runs each app 120 s, waits 60 s and queries FMC for the builtin.json name. With zero rows it "
                        "falls back to all events from the VM source and records seen_apps — parent app or nothing at all. Zero-hit built-ins move to "
                        "the Lua path. Step two: cap.py installs and captures 150 s, sni.py shows SNI roots, gen.sh builds the Lua from the chosen roots. "
                        "Step three: fmc50.py import, activate, forcedeploy — log each with labctl change fmc. Step four: gverify with CUSTOM=1 re-runs "
                        "and verifies. With zero hits, check whether another rule ate the SNI, adjust roots and reimport. Name clashes get a _Mobile "
                        "suffix plus aliases in pkgs/meta and an entry in NEW in results.py."))
    d.bullet_card(s, 0.6, 1.75, 5.55, 4.3, "workflow", BLUE, d.T("步骤要点", "Key points"), [
        (d.T("emu.ensure() 看门狗：没起来就启动并 adb root", "emu.ensure() watchdog: boot + adb root"),
         d.T("Modern34 · 6 GB · 4 核", "Modern34 · 6 GB · 4 cores")),
        (d.T("先验内置：跑 120 s、等 60 s、查 web_app", "Built-ins first: run 120 s, wait 60 s, query"),
         d.T("0 命中 → 转做 Lua", "Zero hits → make a Lua")),
        (d.T("抓包 150 s → sni.py 选根域名 → gen.sh", "Capture 150 s → sni.py roots → gen.sh"), None),
        (d.T("导入/激活/部署前先 labctl change fmc", "labctl change fmc before each FMC change"), None),
        (d.T("0 命中：查 SNI 是否被别的规则吃掉", "Zero hits: did another rule eat the SNI?"),
         d.T("调整根域名后 fmc50.py reimport", "Adjust roots, then fmc50.py reimport")),
    ], size=13, gap=0.14)
    d.code_block(s, 6.4, 1.75, 6.33, 4.3,
                 "cd pipeline\n"
                 "NOCAP=1 PYTHONPATH=. $PY sg/cap.py WhatsApp ...\n"
                 "PYTHONPATH=. $PY sg/gverify.py sg/verify WhatsApp ...\n"
                 "PYTHONPATH=. $PY sg/cap.py AppA AppB   # 150 s\n"
                 "python3 sg/sni.py sg/appa.pcap\n"
                 "bash sg/gen.sh AppA appa.com,appa-cdn.net\n"
                 "cd sg && V=../../../.venv/bin/python\n"
                 "$V fmc50.py import AppA AppB\n"
                 "$V fmc50.py activate AppA AppB\n"
                 "$V fmc50.py forcedeploy\n"
                 "cd .. && CUSTOM=1 SECS=150 PYTHONPATH=. \\\n"
                 "  $PY sg/gverify.py sg/verify AppA AppB",
                 title=d.T("# 示例市场 sg；fmc50.py 用项目自己的 ../.venv", "# example market sg; fmc50.py uses the project ../.venv"),
                 size=12)
    d.banner(s, "badge-check", d.T("只有 CUSTOM=1 二次运行后看到 web_app = Lua 名，才进入证据环节",
                                   "Only a CUSTOM=1 re-run showing web_app = Lua name moves an app on to evidence"),
             accent=GREEN)


# ── 09 flow part 3 ─────────────────────────────────────────────────────────
def s_flow3(d):
    s = d.new_slide(d.T("标准流程 ③：截图、证据、PPT、发布、收尾", "Standard flow ③: shots, evidence, deck, publish, wrap-up"),
                    d.T("第 4.7–4.11 节 · 发布前必须人工确认", "Sections 4.7–4.11 · publishing needs human sign-off"),
                    notes=d.T(
                        "第三段：截图、证据、PPT、发布和收尾。fmcshot.py 用 Playwright 给每个 App 截两张：FMC Detector 列表和 App Detector 里的 FMC 事件查询。"
                        "然后把结果填进 results.py，包括 CUSTOM、NEW、PARENT、SHARED_INFRA、FAIL 原因和 NOTE，运行 build_ev.py，生成 runs 下的 evidence/apps.json 以及 client、fmc_detector、fmc_events、fmc_json 四个目录。"
                        "PPT 交给 deck generator agent，数据源就是 apps.json，结构参考香港这轮的 generate_hk_top50_ppt.py：封面、覆盖率、方法、全量表、每个新 Lua 一页证据、内置命中、未识别原因、注意事项、共享库。"
                        "发布必须人工确认：putlua.py 把 Lua 传到 VM 的 generated_detectors，启动 Lua Maintainer，再用 publish50.py 发布，它需要 info.json 提供包名、API 版本和规则摘要。发布后到 GitHub library 目录确认数量增加。"
                        "收尾：停掉 8899 的 http.server 和 maintainer，clean.py 卸载 App、停模拟器，清空 work，labctl release，最后在 runs 下写交接：结果、坑、下次要改的。",
                        "Part three: screenshots, evidence, deck, publishing and wrap-up. fmcshot.py uses Playwright to take two shots per app: the FMC "
                        "detector list and the FMC event query in App Detector. Fill results.py — CUSTOM, NEW, PARENT, SHARED_INFRA, FAIL reasons, "
                        "NOTE — then build_ev.py writes evidence/apps.json under runs/ plus the client, fmc_detector, fmc_events and fmc_json folders. "
                        "The deck goes to the deck generator agent with apps.json as data; follow generate_hk_top50_ppt.py: cover, coverage, method, full "
                        "table, one evidence page per new Lua, built-in hits, unidentified reasons, caveats, library. Publishing needs the user's OK: "
                        "putlua.py copies Lua to the VM, start the Lua Maintainer, then publish50.py, which needs info.json with package, API level and "
                        "rule summary; confirm the count grew in GitHub library/. Wrap-up: stop the 8899 server and the maintainer, clean.py uninstalls "
                        "apps and stops the emulator, clear work/, labctl release, and write a handoff under runs/."))
    steps = [("image", BLUE, d.T("截图", "Screenshots"), "fmcshot.py"),
             ("file-json", BLUE, d.T("证据", "Evidence"), "build_ev.py"),
             ("presentation", BLUE, d.T("证据 PPT", "Deck"), "deck generator"),
             ("share-2", GREEN, d.T("发布", "Publish"), "publish50.py"),
             ("trash-2", BLUE, d.T("收尾交接", "Wrap-up"), "clean · release")]
    d.card(s, 0.6, 1.75, 5.55, 1.75)
    xs = [1.15 + i * 1.12 for i in range(5)]
    for i, (ic, col, t, sub) in enumerate(steps):
        d.badge(s, ic, xs[i], 2.3, 0.6, fill=col)
        d.text(s, t, xs[i] - 0.56, 2.66, 1.12, 0.3, size=12, color=WHITE, align=PP_ALIGN.CENTER)
        d.text(s, sub, xs[i] - 0.56, 2.96, 1.12, 0.45, size=10, color=MUTED, align=PP_ALIGN.CENTER, font=MONO)
        if i < 4:
            d.arrow(s, xs[i] + 0.35, 2.3, xs[i + 1] - 0.35, 2.3, width=1.75)
    d.bullet_card(s, 0.6, 3.65, 5.55, 2.4, "list-checks", BLUE, d.T("要点", "Key points"), [
        (d.T("每 App 两张图：Detector 列表 + FMC 事件", "Two shots per app: detector list + FMC events"), None),
        (d.T("results.py → apps.json（5 种状态）", "results.py → apps.json (5 statuses)"), None),
        (d.T("发布需 info.json；之后到 library/ 核对数量", "Publish needs info.json; then check library/ count"), None),
    ], size=12, gap=0.08, d=0.5, title_size=15)
    d.code_block(s, 6.4, 1.75, 6.33, 4.3,
                 "cd apk_tools\n"
                 "MARKET=sg $PY fmcshot.py ../work/sg/shots AppA=AppA\n"
                 "MARKET=sg $PY build_ev.py\n"
                 "#  → runs/<yyyy-mm>_sg/evidence/apps.json\n"
                 + d.T("# --- 用户确认发布后 ---\n", "# --- after the user approves publishing ---\n") +
                 "PYTHONPATH=../pipeline $PY putlua.py AppA AppB\n"
                 "# NGFW_lua_maintainer:\n"
                 "#   .venv/bin/python -m lua_maintainer --no-browser\n"
                 "cd ../pipeline/sg && $PY publish50.py AppA AppB\n" +
                 d.T("# --- 收尾 ---\n", "# --- wrap-up ---\n") +
                 "MARKET=sg PYTHONPATH=../pipeline $PY clean.py\n"
                 "labctl release --holder \"<task>\"",
                 title=d.T("# 截图 → 证据 → 发布 → 收尾", "# shots → evidence → publish → wrap-up"), size=11.5)
    d.banner(s, "file-check", d.T("每轮结束都在 runs/<yyyy-mm>_<市场>/ 写交接：结果、坑、下次要改的",
                                  "Every round ends with a handoff in runs/<yyyy-mm>_<market>/: results, pitfalls, fixes"),
             accent=BLUE)


# ── 10 Lua rules ───────────────────────────────────────────────────────────
def s_lua(d):
    s = d.new_slide(d.T("Lua 生成规则", "Lua generation rules"),
                    d.T("只用 App 自有根域名；名字和类别要符合 FMC 约束",
                        "App-owned root domains only; names and categories must fit FMC"),
                    notes=d.T(
                        "Lua 规则决定会不会误识别，这一页最重要。原则是根域名只取 App 自有的，比如 OpenRice 只用 openrice.com，Keeta 用 mykeeta.com 和 mykeeta.net。"
                        "要排除共享基础设施：CDN（akamai、cloudfront、fastly 等）、广告统计崩溃 SDK（Firebase、Crashlytics、AppsFlyer 等）、母公司或集团域名。"
                        "右边是真实案例：Threads 抓到的只有 Instagram 和 fbcdn 的域名，所以记为识别为 Instagram，不做 Lua；foodpanda 只有 deliveryhero.net 这个集团共享域名，故意不做；"
                        "闲鱼和 UC 浏览器共用 px.ucweb.com，必须删掉这个共享 host；JobsDB 用 seek.com，也会命中 SEEK App，所以要在 PPT 里注明；抖音和 TikTok 有重叠，缩小到中国区独有的 host。"
                        "名字必须匹配 ^[A-Za-z_]{1,15}$，不能和 FMC 内置或已有自定义 Detector 重名，冲突加 _Mobile 后缀，比如 Spotify_Mobile。"
                        "类别要用 FMC 已有的类别名，mkjson.py 里有映射表；不存在的类别 FMC 会回退为 others。信号方面，HTTPS 用 SNI 的精确和后缀匹配，明文用 HTTP Host，规则由项目的 LuaRenderer 模板生成。",
                        "Lua rules decide whether you get false matches. Use app-owned roots only — OpenRice uses openrice.com, Keeta uses mykeeta.com "
                        "and mykeeta.net. Exclude shared infrastructure: CDNs such as akamai, cloudfront, fastly; ad, analytics and crash SDKs such as "
                        "Firebase, Crashlytics, AppsFlyer; and parent-group domains. Real cases on the right: Threads only showed Instagram and fbcdn "
                        "domains, so it is recorded as identified as Instagram, with no Lua. foodpanda only had the Delivery Hero group domain, so no "
                        "Lua on purpose. Xianyu and UC Browser share px.ucweb.com, so that host is removed. JobsDB uses seek.com and may also match the "
                        "SEEK app — say so in the deck. Douyin and TikTok overlap, so Douyin is narrowed to China-only hosts. Names must match "
                        "^[A-Za-z_]{1,15}$ and must not clash with built-in or existing custom detectors; clashes get _Mobile, e.g. Spotify_Mobile. "
                        "Use existing FMC category names — mkjson.py maps them; unknown categories fall back to others. Signals: SNI exact and suffix "
                        "for HTTPS, HTTP Host for plaintext, rendered by the project's LuaRenderer template."))
    d.bullet_card(s, 0.6, 1.75, 5.1, 4.3, "fingerprint", BLUE, d.T("规则", "Rules"), [
        (d.T("根域名只取 App 自有的", "Roots must be app-owned"), d.T("OpenRice → openrice.com", "OpenRice → openrice.com")),
        (d.T("排除 CDN、广告/统计/崩溃 SDK、集团域名", "Exclude CDN, ad/analytics/crash SDK, group"),
         "akamai · cloudfront · Firebase · AppsFlyer"),
        (d.T("名字 ^[A-Za-z_]{1,15}$，冲突加 _Mobile", "Name ^[A-Za-z_]{1,15}$; clash → _Mobile"), "Spotify_Mobile"),
        (d.T("类别用 FMC 已有名称，否则回退 others", "Use existing FMC categories, else others"), None),
        (d.T("HTTPS 用 SNI（精确 + 后缀），明文用 Host", "HTTPS: SNI exact + suffix; HTTP: Host"), "LuaRenderer"),
    ], size=12, gap=0.1)
    rows = [[d.T("案例", "Case"), d.T("抓到的域名", "What we saw"), d.T("处理", "Decision")],
            ["Threads", "Instagram / fbcdn", d.T("识别为 Instagram，不做 Lua", "Parent Instagram, no Lua")],
            ["foodpanda", "deliveryhero.net", d.T("集团共享域名，不做", "Group-shared, no Lua")],
            [d.T("闲鱼 / UC", "Xianyu / UC"), "px.ucweb.com", d.T("删掉共享 host", "Remove the shared host")],
            ["JobsDB", "seek.com", d.T("可能命中 SEEK，PPT 注明", "May hit SEEK; flag in deck")],
            [d.T("抖音 / TikTok", "Douyin / TikTok"), d.T("域名重叠", "Overlapping hosts"), d.T("缩小到中国区独有 host", "Narrow to China-only hosts")],
            ["Keeta", "mykeeta.com / .net", d.T("自有根域名 → Lua", "App-owned → Lua")]]
    d.card(s, 5.95, 1.75, 6.78, 4.3)
    d.text(s, d.T("真实案例（香港 / 中国轮次）", "Real cases (HK / China rounds)"), 6.15, 1.87, 6.4, 0.35, size=14, color=CYAN)
    acc = {(1, 2): ORANGE, (2, 2): ORANGE, (3, 2): ORANGE, (4, 2): ORANGE, (5, 2): ORANGE, (6, 2): GREEN}
    d.table(s, 6.1, 2.32, 6.48, rows, col_w=[1.5, 2.0, 2.98], row_h=0.52, size=12, accents=acc)
    d.banner(s, "shield-check", d.T("宁可不做 Lua，也不要用共享域名 —— 误识别比漏识别更糟",
                                    "Better no Lua than a shared domain — a false match is worse than a miss"), accent=ORANGE)


# ── 11 verification & statuses ────────────────────────────────────────────
def s_verify(d):
    s = d.new_slide(d.T("验证与证据标准", "Verification & evidence standard"),
                    d.T("“新 Lua 已验证”必须同时满足 4 条；每个 App 落到 5 种状态之一",
                        "\"New Lua verified\" needs all 4 conditions; every app lands in one of 5 statuses"),
                    notes=d.T(
                        "验证标准。一个 App 判为新 Lua 已验证，必须同时满足四条：第一，Lua 已在 FMC 导入并且 active，部署 SUCCEEDED。Snort 3 激活大约 100 秒生效，不需要重启 Snort。"
                        "第二，导入后重新运行 App，gverify 默认操作 120 到 150 秒。第三，FMC 连接事件里 web_app 等于 Lua 名至少 1 条，而且源 IP 是测试 VM。"
                        "第四，证据保存齐全：客户端截图、FMC Detector 截图、FMC 事件截图和事件 JSON，JSON 放在 fmc_json/<App>-fmc.json。"
                        "右边是 5 种状态：builtin_hit 是 FMC 内置名命中；identified_as_parent 是被识别为母应用，比如 Messenger 被识别为 Facebook；new_lua_verified 是新 Lua 实测命中；"
                        "no_lua_shared_infra 是只有集团共享域名，故意不做；failed 是跑不起来或没有 App 流量，必须写原因。"
                        "最右一列是香港 Top50 的实际分布，加起来正好 50 个。",
                        "The verification standard. An app counts as new Lua verified only when all four hold: the Lua is imported and active on FMC "
                        "and the deployment SUCCEEDED — on Snort 3 activation takes about 100 s without restarting Snort; the app was re-run after "
                        "import, 120–150 s by default with gverify; FMC Connection Events show at least one event with web_app equal to the Lua name "
                        "from the test VM; and the evidence is saved — client screenshot, FMC detector screenshot, FMC event screenshot and event JSON "
                        "in fmc_json/<App>-fmc.json. The five statuses: builtin_hit — a built-in name hit; identified_as_parent — e.g. Messenger seen "
                        "as Facebook; new_lua_verified; no_lua_shared_infra — only group-shared domains, skipped on purpose; failed — won't run or no "
                        "app traffic, reason mandatory. The last column is the Hong Kong Top 50 split, adding up to 50."))
    d.card(s, 0.6, 1.75, 5.3, 4.3)
    d.text(s, d.T("4 个条件（同时满足）", "4 conditions (all required)"), 0.85, 1.9, 4.9, 0.35, size=15, color=CYAN)
    conds = [("toggle-right", d.T("Lua 已导入且 active，部署成功", "Lua imported, active, deploy SUCCEEDED"),
              d.T("Snort 3 约 100 s 生效，不重启", "Snort 3: ~100 s, no restart")),
             ("refresh-cw", d.T("导入后重新运行 App", "App re-run after import"), d.T("gverify 120–150 s", "gverify 120–150 s")),
             ("activity", d.T("事件 web_app = Lua 名 ≥ 1 条", "≥ 1 event with web_app = Lua name"), d.T("源为测试 VM", "Source = the test VM")),
             ("file-check", d.T("3 张截图 + 事件 JSON", "3 screenshots + event JSON"), "fmc_json/<App>-fmc.json")]
    for i, (ic, t, sub) in enumerate(conds):
        d.icon_row(s, ic, BLUE, t, sub, 0.85, 2.45 + i * 0.88, 4.9, d=0.52, title_size=13.5, body_size=11.5)
    rows = [[d.T("状态", "Status"), d.T("含义", "Meaning"), d.T("香港", "HK")],
            ["new_lua_verified", d.T("新 Lua 实测命中", "New Lua hit live"), "18"],
            ["builtin_hit", d.T("FMC 内置名命中", "Built-in name hit"), "15"],
            ["identified_as_parent", d.T("识别为母应用", "Seen as parent app"), "2"],
            ["no_lua_shared_infra", d.T("只有集团共享域名，不做", "Group-shared only, skipped"), "1"],
            ["failed", d.T("跑不起来 / 无流量，写原因", "Won't run / no traffic + reason"), "14"]]
    d.card(s, 6.15, 1.75, 6.58, 4.3)
    d.table(s, 6.3, 2.0, 6.28, rows, col_w=[2.55, 3.03, 0.7], row_h=0.6, size=12,
            accents={(1, 0): GREEN, (1, 2): GREEN, (5, 0): ORANGE, (5, 2): ORANGE})
    d.text(s, d.T("Messenger → Facebook，Threads → Instagram", "Messenger → Facebook, Threads → Instagram"),
           6.3, 5.65, 6.28, 0.3, size=11, color=MUTED)
    d.banner(s, "badge-check", d.T("上传成功 ≠ 已验证：必须在 FMC 连接事件里看到 Lua 名",
                                   "Upload success ≠ verified: the Lua name must appear in FMC Connection Events"), accent=GREEN)


# ── 12 human checkpoints ──────────────────────────────────────────────────
def s_human(d):
    s = d.new_slide(d.T("人工确认节点", "Human-in-the-loop checkpoints"),
                    d.T("重复操作交给 AI；这 6 个时刻必须由人拍板", "AI does the repetition; a human decides at these 6 moments"),
                    notes=d.T(
                        "人工确认节点。整套方法的分工是人只做决策，AI 负责重复操作。这 6 个时刻 AI 必须停下来问人。"
                        "开始前：市场、App 清单、是否全部上 FMC 验证（包括内置）、是否发布、发布备注、PPT 语言。"
                        "清单有替补时：下载不到的 App 用谁替补，比如香港这轮 Meta AI、Poe、Taobao、Temu 在 APKPure 下架，替补成 Klook、HK01、Lalamove、Agoda。"
                        "lab 冲突时：资源被别的任务占用，是等待、接管、共享还是换资源，由用户决定。"
                        "影响较大的 lab 变更：扩 VM 磁盘或内存、删除 VM 上的大目录、wipe 模拟器数据，都要先问。"
                        "发布前：发布哪些 Lua、备注文字。"
                        "有疑问的规则：可能误识别其他品牌的根域名，比如 seek.com。"
                        "过去几轮里，用户实际确认过的包括：是否做模拟器 pilot、是否扩 VM 磁盘、是否跳过内置、是否独立出 Maintainer 和 Importer、是否自动激活部署、是否发布到 GitHub，以及允许把失败如实记录而不是伪造。",
                        "Human checkpoints. Humans decide, the AI repeats — and at these six moments the AI must stop and ask. Before starting: market, "
                        "app list, whether every app is verified on FMC including built-ins, whether to publish, the publish note and the deck language. "
                        "When the list needs substitutes: in Hong Kong, Meta AI, Poe, Taobao and Temu were not on APKPure and were replaced by Klook, "
                        "HK01, Lalamove and Agoda. On a lab conflict: wait, take over, share or switch resource — the user decides. Before high-impact "
                        "lab changes: growing VM disk or memory, deleting large VM folders, wiping emulator data. Before publishing: which Lua and the "
                        "note. On doubtful rules: roots that may match another brand, such as seek.com. In past rounds users approved the emulator "
                        "pilot, the VM disk expansion, skipping built-ins, the separate Maintainer and Importer, auto-activation, publishing to GitHub, "
                        "and recording failures honestly instead of faking evidence."))
    rows = [[d.T("时机", "When"), d.T("要确认的事", "What the human confirms"), d.T("例子", "Example")],
            [d.T("开始前", "Before starting"), d.T("市场、清单、是否全部上 FMC、是否发布、PPT 语言", "Market, list, FMC scope, publish?, deck language"), d.T("香港 Top50 全部 50 个上 FMC", "All 50 HK apps on FMC")],
            [d.T("清单有替补", "List substitutes"), d.T("下载不到的 App 用谁替补", "Who replaces unavailable apps"), "Meta AI → Klook"],
            [d.T("lab 冲突", "Lab conflict"), d.T("等待 / 接管 / 共享 / 换资源", "Wait / take over / share / switch"), d.T("labctl 退出码 2", "labctl exit code 2")],
            [d.T("较大 lab 变更", "High-impact change"), d.T("扩磁盘/内存、删大目录、wipe 模拟器", "Grow disk/RAM, delete big dirs, wipe"), d.T("扩 VM 磁盘", "VM disk expansion")],
            [d.T("发布前", "Before publishing"), d.T("发布哪些 Lua、备注文字", "Which Lua, publish note"), "\"Hong Kong market top 50\""],
            [d.T("有疑问的规则", "Doubtful rule"), d.T("可能误识别其他品牌的根域名", "Roots that may match another brand"), "seek.com"]]
    d.badge(s, "user-check", 1.15, 2.35, 0.8, fill=BLUE, ring=CYAN)
    d.badge(s, "bot", 1.15, 4.65, 0.8, fill=CARD_2, color="cyan")
    d.text(s, d.T("人拍板", "Human decides"), 0.6, 2.95, 1.1, 0.3, size=11.5, color=WHITE, align=PP_ALIGN.CENTER)
    d.text(s, d.T("AI 停下问", "AI stops & asks"), 0.6, 5.25, 1.1, 0.3, size=11.5, color=WHITE, align=PP_ALIGN.CENTER)
    d.arrow(s, 1.15, 4.1, 1.15, 3.35)
    d.table(s, 1.95, 1.75, 10.78, rows, col_w=[2.0, 5.2, 3.58], row_h=0.6, size=12.5,
            accents={(r, 0): CYAN for r in range(1, 7)} | {(0, 0): CYAN})
    d.banner(s, "hand", d.T("AI 执行，人决策 —— 范围、发布和冲突永远不由 AI 自己决定",
                            "AI executes, humans decide — scope, publishing and conflicts are never the AI's call"), accent=BLUE)


# ── 13 guardrails ─────────────────────────────────────────────────────────
def s_rules(d):
    s = d.new_slide(d.T("硬规则：给 AI 的护栏", "Guardrails: hard rules for the AI"),
                    d.T("写在 AI_WORKFLOW.md 第 8 节和 AGENTS.md，AI 每次自动加载",
                        "Section 8 of AI_WORKFLOW.md and AGENTS.md — loaded by the AI every time"),
                    notes=d.T(
                        "硬规则，也就是给 AI 的护栏，写在 AI_WORKFLOW.md 第 8 节和 AGENTS.md 里，AGENTS.md 会被 AI 助手自动加载。"
                        "第一，lab 先认领再动：动 VM、FMC、FTD 之前用 labctl claim，改配置前 labctl change，结束 labctl release；冲突时 labctl 退出码是 2，AI 必须停下来问用户。改了 ESXi 网络、VM 硬件或 FTD 策略后要 labctl refresh。"
                        "第二，凭据只放 config/lab.env，已经 gitignore，脚本通过 pipeline/labcfg.py 读取；文档、交接、PPT、共享库里一律写 <redacted>。"
                        "第三，不上传 PCAP，PCAP、APK、work、verify 都已 gitignore。"
                        "第四，未经要求不 git commit，发布到 GitHub 共享库需要用户授权。"
                        "第五，只按 PID kill 进程，不用 pkill 或 killall；stop_bash 不一定能杀掉子 Python 进程，要用 ps 查 PID。"
                        "第六，不要动用户正在运行的 Importer（8790 端口）；PPT 和海报交给 deck generator agent。"
                        "下面的命令就是认领的标准写法，持有人、会话和目的都要写清楚。",
                        "Guardrails live in section 8 of AI_WORKFLOW.md and in AGENTS.md, which AI assistants load automatically. One: claim the lab "
                        "before touching it — labctl claim before using the VM, FMC or FTD, labctl change before config changes, labctl release at the "
                        "end; a conflict returns exit code 2 and the AI must stop and ask. Run labctl refresh after changing ESXi networking, VM hardware "
                        "or FTD policy. Two: credentials only in config/lab.env, gitignored and read through pipeline/labcfg.py; docs, handoffs, decks "
                        "and the library say <redacted>. Three: never upload PCAPs — PCAP, APK, work/ and verify/ are gitignored. Four: no git commit "
                        "unless asked; publishing to the GitHub library needs the user's OK. Five: kill by PID only, never pkill or killall; stop_bash "
                        "may leave child Python processes, so find the PID with ps. Six: don't touch the user's Importer on :8790, and hand decks and "
                        "posters to the deck generator agent. The command shows the standard claim."))
    items = [("lock", BLUE, d.T("Lab 先认领再动", "Claim the lab first"),
              d.T("claim → change → release；冲突退出码 2 → 停下问用户", "claim → change → release; exit 2 → stop and ask")),
             ("key-round", ORANGE, d.T("凭据只在 lab.env", "Credentials only in lab.env"),
              d.T("gitignored，经 labcfg.py 读取；其他地方写 <redacted>", "Gitignored, read via labcfg.py; elsewhere <redacted>")),
             ("ban", RED, d.T("不上传 PCAP", "Never upload PCAPs"),
              d.T("PCAP、APK、work/、verify/ 均已 gitignore", "PCAP, APK, work/, verify/ are gitignored")),
             ("git-branch", ORANGE, d.T("未经要求不 commit", "No commit unless asked"),
              d.T("发布到 GitHub 共享库需要用户授权", "Publishing to GitHub needs the user's OK")),
             ("crosshair", BLUE, d.T("只按 PID kill", "Kill by PID only"),
              d.T("不用 pkill / killall；ps 查子进程 PID", "No pkill / killall; find child PIDs with ps")),
             ("plug", BLUE, d.T("不动用户的 Importer", "Leave the user's Importer"),
              d.T(":8790 是用户的服务；PPT 交给 deck generator", ":8790 is the user's; decks → deck generator"))]
    cw, ch = 3.85, 1.32
    for k, (ic, col, t, body) in enumerate(items):
        r, c = divmod(k, 3)
        x, y = 0.6 + c * (cw + 0.29), 1.75 + r * (ch + 0.14)
        d.card(s, x, y, cw, ch)
        d.badge(s, ic, x + 0.5, y + 0.5, 0.6, fill=col)
        d.text(s, t, x + 0.95, y + 0.16, cw - 1.05, 0.38, size=15, color=WHITE)
        d.text(s, body, x + 0.95, y + 0.55, cw - 1.08, 0.72, size=12, color=MUTED)
    d.code_block(s, 0.6, 4.7, 12.13, 1.35,
                 "python3 ~/.copilot/lab/labctl.py claim fmc ftd win-test-host --holder \"<task>\" \\\n"
                 "    --session \"<session-link>\" --purpose \"<one line>\"      # exit 2 = conflict → ask the user\n"
                 "python3 ~/.copilot/lab/labctl.py release --holder \"<task>\"",
                 title=d.T("# 认领与释放（第 8 节）", "# claim & release (section 8)"), size=11.5)
    d.banner(s, "shield-check", d.T("护栏写进文档，任何 AI 接手都遵守同一套规则",
                                    "Guardrails are written down, so every AI that takes over follows the same rules"),
             accent=RED)


# ── 14 pitfalls ────────────────────────────────────────────────────────────
def s_pitfalls(d):
    s = d.new_slide(d.T("已知坑与对策（Top 8）", "Known pitfalls & fixes (top 8)"),
                    d.T("来自 7 轮实测；完整列表见 AI_WORKFLOW.md 第 9 节",
                        "From 7 lab rounds; the full list is in section 9 of AI_WORKFLOW.md"),
                    notes=d.T(
                        "已知坑，按出现频率挑了 8 个。第一，银行、支付、政府类 App，比如 HSBC、恒生、中银、Mox、PayMe、八达通、iAM Smart、HA Go，在 root 模拟器上会闪退或卡启动页，直接记失败原因，立项时就提醒用户可能要换掉。"
                        "第二，模拟器重启后 adbd 不是 root，tcpdump 也不在，pcap 拉取会报 base64 错误；emu.ensure() 会自动 adb root，抓包前确认 which tcpdump。"
                        "第三，VM 蓝屏 0x1A 和 qemu 崩溃：靠 emu.py 看门狗、droid.ps 默认 300 秒超时，加上每个 App 单独 try/except。"
                        "第四，WinRM 同步执行 adb start-server 或 kill-server 会卡死，改用 Win32_Process Create 启动。"
                        "第五，APKPure 首个版本经常只有 armeabi-v7a，用 arm64alt.py 加 redl.py。第六，VM 经代理下载 APKPure 卡住，改在 Mac 下载，用 http.server 传过去。"
                        "第七，activateDetectors 调用超时，其实还在执行，继续轮询 getDetectorList，fmc50.py activate 已经处理。"
                        "第八，FMC 有内置名但不识别移动端流量，实测 0 命中就做 _Mobile Lua。",
                        "Eight pitfalls, by frequency. One: banking, payment and government apps — HSBC, Hang Seng, BOCHK, Mox, PayMe, Octopus, iAM "
                        "Smart, HA Go — crash or hang on a rooted emulator; record the reason and warn the user at scoping. Two: after an emulator "
                        "restart adbd is not root and tcpdump is missing, so the pcap pull fails with a base64 error; emu.ensure() runs adb root, and "
                        "check which tcpdump. Three: VM blue screens (0x1A) and qemu crashes — the emu.py watchdog, droid.ps timeouts (300 s default) "
                        "and a try/except per app. Four: WinRM hangs when adb start-server or kill-server runs synchronously — start it with "
                        "Win32_Process Create. Five: the first APKPure version is often armeabi-v7a only — arm64alt.py plus redl.py. Six: APKPure "
                        "downloads through the VM proxy stall — download on the Mac and serve with http.server. Seven: activateDetectors times out — "
                        "keep polling getDetectorList, which fmc50.py activate does. Eight: a built-in name exists but misses mobile traffic — make a "
                        "_Mobile Lua."))
    rows = [[d.T("坑", "Pitfall"), d.T("对策", "Fix")],
            [d.T("银行/支付/政府 App 在 root 模拟器闪退或卡启动页", "Banking/payment/gov apps crash on a rooted emulator"),
             d.T("直接记失败原因；立项时提醒用户可能换掉", "Record as failed; warn the user at scoping")],
            [d.T("模拟器重启后 adbd 非 root、tcpdump 不在", "After restart adbd isn't root, tcpdump missing"),
             d.T("emu.ensure() 自动 adb root；抓包前 which tcpdump", "emu.ensure() runs adb root; check which tcpdump")],
            [d.T("VM 蓝屏（0x1A）、qemu 崩溃", "VM blue screen (0x1A), qemu crash"),
             d.T("看门狗 + droid.ps 超时 300 s + 每 App try/except", "Watchdog + droid.ps 300 s timeout + per-app try")],
            [d.T("WinRM 同步执行 adb start/kill-server 卡死", "WinRM hangs on adb start/kill-server"),
             d.T("用 Win32_Process Create 启动", "Launch via Win32_Process Create")],
            [d.T("APKPure 首个版本常是 armeabi-v7a only", "First APKPure build is often armeabi-v7a only"),
             "arm64alt.py + redl.py"],
            [d.T("VM 经代理下载 APKPure 卡在 0 字节", "VM proxy downloads from APKPure stall"),
             d.T("在 Mac 下载，用 http.server 传到 VM", "Download on the Mac, serve to the VM")],
            [d.T("activateDetectors 调用超时", "activateDetectors call times out"),
             d.T("继续轮询 getDetectorList（fmc50.py 已处理）", "Keep polling getDetectorList (fmc50.py does)")],
            [d.T("内置名存在但不识别移动端流量", "Built-in name misses mobile traffic"),
             d.T("实测 0 命中 → 做 _Mobile Lua", "Zero hits → build a _Mobile Lua")]]
    acc = {(r, 1): GREEN for r in range(1, 9)}
    d.badge(s, "triangle-alert", 1.0, 2.15, 0.7, fill=ORANGE)
    d.badge(s, "wrench", 1.0, 3.35, 0.7, fill=GREEN)
    d.table(s, 1.65, 1.75, 11.08, rows, col_w=[5.5, 5.58], row_h=0.47, size=12, accents=acc)
    d.banner(s, "wrench", d.T("坑都写进了脚本和文档：看门狗、超时、轮询 —— 下一个 AI 不用再踩",
                              "Fixes live in scripts and docs — watchdog, timeouts, polling — so the next AI won't repeat them"),
             accent=ORANGE)


# ── 15 results ─────────────────────────────────────────────────────────────
def s_results(d):
    s = d.new_slide(d.T("7 轮实测结果", "Results across 7 rounds"),
                    d.T("2026-10 ~ 2026-11，FMC 10.0.1 / FTD Snort 3", "Oct–Nov 2026, FMC 10.0.1 / FTD Snort 3"),
                    notes=d.T(
                        "历次验证记录，来自 AI_WORKFLOW.md 第 11 节。2026 年 10 月先用招商证券做基线，TdxW 和 CMS 命中。"
                        "11 月 11 日券商 PC 客户端 Top5：中信、国泰海通、华泰、广发、银河 5 个新 Lua 全部命中，用的是模式 A。"
                        "11 月 12 日中国视频 App Top10：6 个内置，抖音、西瓜、咪咕、央视频 4 个新 Lua 命中，模式 A 加 C。"
                        "11 月 13 日中国安卓 Top20：14 个内置，拼多多、高德、滴滴、饿了么 4 个新 Lua，这一轮还是 PCAPdroid。"
                        "11 月 15 日中国安卓 Top50：26 内置、6 个库中已有、15 个新生成（14 个 Detector）、3 个反模拟器；同一天 51 到 100：14 内置、1 已有、18 个新 Lua、17 个失败。"
                        "11 月 16 日安卓手游 Top30：13 个新 Lua、17 个失败。Go Lua Importer 测得导入加激活约 100 秒生效，Snort 3 不重启。"
                        "11 月 17 日香港 Top50：18 新 Lua、15 内置、2 识别为母应用、1 不做、14 失败。"
                        "右边三个数字：约 76 个新 Lua 在 FTD 上实测命中，共享库现有 78 个 Lua，Snort 3 激活约 100 秒、不重启。",
                        "The verification log from section 11. October 2026: China Merchants Securities baseline, TdxW and CMS hit. Nov 11, broker PC "
                        "clients Top 5: CITIC, Guotai Haitong, Huatai, GF and Galaxy — 5 new Lua, all hit, mode A. Nov 12, China video Top 10: 6 built-in, "
                        "4 new Lua hit — Douyin, Xigua, Migu, YangShiPin — modes A and C. Nov 13, China Android Top 20: 14 built-in, 4 new Lua, still "
                        "PCAPdroid. Nov 15, China Android Top 50: 26 built-in, 6 already in the library, 15 newly generated (14 detectors), 3 "
                        "anti-emulator; ranks 51–100: 14 built-in, 1 existing, 18 new Lua, 17 failed. Nov 16, Android games Top 30: 13 new Lua, 17 "
                        "failed. The Go Lua Importer measured about 100 s for import plus activation on Snort 3 without restart. Nov 17, Hong Kong "
                        "Top 50: 18 new, 15 built-in, 2 parent, 1 skipped, 14 failed. Headline: about 76 new Lua hit live on FTD, the library holds 78, "
                        "and Snort 3 activation takes about 100 s with no restart."))
    rows = [[d.T("轮次", "Round"), d.T("日期", "Date"), d.T("模式", "Mode"), d.T("结果", "Result")],
            [d.T("招商证券基线", "CMS Securities baseline"), "2026-10", "A", d.T("TdxW / CMS 命中", "TdxW / CMS hit")],
            [d.T("券商 PC 客户端 Top5", "Broker PC clients Top 5"), "11-11", "A", d.T("5 个新 Lua 全部命中", "5 new Lua, all hit")],
            [d.T("中国视频 App Top10", "China video Top 10"), "11-12", "A+C", d.T("6 内置；4 新 Lua 命中", "6 built-in; 4 new Lua hit")],
            [d.T("中国安卓 Top20", "China Android Top 20"), "11-13", "B", d.T("14 内置；4 新 Lua", "14 built-in; 4 new Lua")],
            [d.T("中国安卓 Top50", "China Android Top 50"), "11-15", "B", d.T("26 内置、6 已有、15 新生成、3 反模拟器", "26 built-in, 6 existing, 15 new, 3 anti-emu")],
            [d.T("中国安卓 51–100", "China Android 51–100"), "11-15", "B", d.T("14 内置、1 已有、18 新 Lua、17 失败", "14 built-in, 1 existing, 18 new, 17 failed")],
            [d.T("安卓手游 Top30", "Android games Top 30"), "11-16", "B", d.T("13 新 Lua、17 失败", "13 new Lua, 17 failed")],
            ["Go Lua Importer", "2026-11", "—", d.T("导入+激活约 100 s，Snort 3 不重启", "Import+activate ~100 s, no Snort restart")],
            [d.T("香港 Top50", "Hong Kong Top 50"), "11-17", "B", d.T("18 新、15 内置、2 母应用、1 不做、14 失败", "18 new, 15 built-in, 2 parent, 1 skip, 14 fail")]]
    d.table(s, 0.6, 1.75, 9.0, rows, col_w=[2.55, 0.95, 0.65, 4.85], row_h=0.425, size=11.5,
            accents={(9, 0): CYAN, (9, 3): CYAN})
    sw, sx = 2.88, 9.85
    d.stat_card(s, sx, 1.75, sw, 1.3, "~76", d.T("新 Lua 在 FTD 实测命中", "new Lua hit live on FTD"), GREEN)
    d.stat_card(s, sx, 3.22, sw, 1.3, "78", d.T("共享库现有 Lua", "Lua in the shared library"), CYAN)
    d.stat_card(s, sx, 4.69, sw, 1.3, "~100 s", d.T("Snort 3 激活生效，不重启", "Snort 3 activation, no restart"), BLUE)
    d.banner(s, "trophy", d.T("7 轮跑通同一套方法：约 76 个新 Lua 实测命中，共享库达到 78 个",
                              "One method, 7 rounds: ~76 new Lua verified live, shared library at 78"), accent=GREEN)


# ── 16 HK case study ───────────────────────────────────────────────────────
def s_hk(d):
    s = d.new_slide(d.T("案例：香港 Top 50（2026-11-17）", "Case study: Hong Kong Top 50 (2026-11-17)"),
                    d.T("50 个 App 全部在 FMC 10.0.1 / FTD 上实测，包括内置", "All 50 apps tested live on FMC 10.0.1 / FTD, built-ins included"),
                    notes=d.T(
                        "最近一轮的完整案例：香港市场 Top50 安卓 App，2026 年 11 月 17 日。范围是全部 50 个都在 FMC 10.0.1 和 FTD Snort 3 上实测，包括内置的。"
                        "环境是 Android 14（API 34）模拟器 Modern34，adb root 加 tcpdump，APK 来自 APKPure。"
                        "结果：18 个新 Lua 已验证，其中 Spotify_Mobile、KKBOX_Mobile、Google_Maps 是内置名存在但移动端不命中的情况；15 个内置命中；2 个识别为母应用，Messenger 识别为 Facebook，Threads 识别为 Instagram；1 个不做 Lua，foodpanda 只有 Delivery Hero 集团共享域名；14 个失败，主要是银行和政府类 App 的 root 检测或卡启动页。"
                        "替补：Meta AI、Poe、Taobao、Temu 在 APKPure 下架，换成 Klook、HK01、Lalamove、Agoda。"
                        "右边是 OpenRice 的真实证据：左边是模拟器里的客户端截图；右上是 FMC 里的自定义 Detector，类型 CUSTOM、已激活；右下是 FMC 连接事件，Web App 列显示 OpenRice。规则只用 openrice.com 一个根域名，验证时记录了 74 条命中。"
                        "事件截图已经去掉了源 IP 和目的 IP 列。新 Lua 已经发布到共享库，备注 Hong Kong market top 50。",
                        "The latest full round: Hong Kong Top 50 Android apps, 17 Nov 2026. All 50 were tested on FMC 10.0.1 and FTD Snort 3, built-ins "
                        "included, on the Android 14 (API 34) emulator Modern34 with adb root and tcpdump; APKs from APKPure. Results: 18 new Lua "
                        "verified — including Spotify_Mobile, KKBOX_Mobile and Google_Maps, where the built-in name missed mobile traffic; 15 built-in "
                        "hits; 2 identified as the parent — Messenger as Facebook, Threads as Instagram; 1 skipped — foodpanda only had the Delivery "
                        "Hero group domain; 14 failed, mostly banking and government apps with root detection or stuck splash screens. Meta AI, Poe, "
                        "Taobao and Temu were not on APKPure and were replaced by Klook, HK01, Lalamove and Agoda. On the right is real OpenRice "
                        "evidence: the client on the emulator, the custom detector in FMC (CUSTOM, active) and FMC Connection Events with Web App = "
                        "OpenRice. One root, openrice.com; 74 hits recorded. IP columns are removed from the crop. The new Lua were published with the "
                        "note 'Hong Kong market top 50'."))
    d.card(s, 0.6, 1.75, 4.1, 4.3)
    stats = [("18", GREEN, d.T("新 Lua 已验证", "new Lua verified")),
             ("15", BLUE, d.T("内置命中", "built-in hit")),
             ("2", BLUE, d.T("识别为母应用", "identified as parent")),
             ("1", BLUE, d.T("不做 Lua（共享域名）", "no Lua (shared infra)")),
             ("14", ORANGE, d.T("失败（root 检测 / 卡启动页…）", "failed (root check, splash…)"))]
    for i, (n, col, lab) in enumerate(stats):
        y = 1.95 + i * 0.6
        d.text(s, n, 0.85, y, 0.8, 0.5, size=24, color=col, valign=MSO_ANCHOR.MIDDLE)
        d.text(s, lab, 1.7, y, 2.9, 0.5, size=12.5, color=TEXT, valign=MSO_ANCHOR.MIDDLE)
    d.line(s, 0.85, 5.0, 4.45, 5.0, color=LINE, width=1)
    d.text(s, d.T("替补：Meta AI、Poe、Taobao、Temu 下架\n→ Klook、HK01、Lalamove、Agoda",
                  "Swaps: Meta AI, Poe, Taobao, Temu unavailable\n→ Klook, HK01, Lalamove, Agoda"),
           0.85, 5.08, 3.75, 0.9, size=11, color=MUTED)
    # evidence
    d.picture(s, ASSETS / "OpenRice_client.png", 4.95, 1.8, 2.1, 3.75)
    d.text(s, d.T("客户端（模拟器）", "Client (emulator)"), 4.85, 5.65, 2.3, 0.3, size=10.5, color=MUTED, align=PP_ALIGN.CENTER)
    ex, ew = 7.4, 5.33
    d.text(s, d.T("FMC 自定义 Detector · 已激活", "FMC custom detector · active"), ex, 1.75, ew, 0.3, size=11, color=CYAN)
    d.picture(s, ASSETS / "OpenRice_detector.png", ex, 2.1, ew, 0.78, anchor="top")
    d.text(s, d.T("FMC 连接事件 · Web App = OpenRice（已去除 IP 列）", "FMC Connection Events · Web App = OpenRice (IP columns removed)"),
           ex, 3.05, ew, 0.3, size=11, color=CYAN)
    d.picture(s, ASSETS / "OpenRice_events.png", ex, 3.4, ew, 1.95, anchor="top")
    d.pill(s, d.T("根域名 openrice.com · 74 条命中", "root openrice.com · 74 hits"), ex, 5.62, ew, 0.38, color=GREEN, size=11.5,
           line=GREEN)
    d.banner(s, "map-pin", d.T("香港 Top50：18 个新 Lua 实测命中，失败的 14 个都写明了原因",
                               "HK Top 50: 18 new Lua hit live; all 14 failures have a written reason"), accent=GREEN)


# ── 17 toolkit & hand-off ─────────────────────────────────────────────────
def s_toolkit(d):
    s = d.new_slide(d.T("工具包与交接：交给任何 AI", "Toolkit & hand-off: give it to any AI"),
                    d.T("ai_workflow/ 一个目录装下文档、脚本、记录；一段提示词就能开工",
                        "One folder holds docs, scripts and records; one prompt gets an AI started"),
                    notes=d.T(
                        "最后是怎么把它交给你自己的 AI。左边是 ai_workflow 目录：AI_WORKFLOW.md 是主文档，包括思路、拓扑、标准流程、Lua 规则、验证标准、人工节点、硬规则、已知坑、工具清单和历次记录；"
                        "AGENTS.md 是给 AI 助手的简短规则，会被自动加载；pipeline 是 Mac 侧驱动 VM、模拟器和 FMC 的脚本，其中 hk 是一轮任务的完整模板；apk_tools 负责下载、截图、证据、发布和清理；"
                        "config 里只有 lab.example.env，真实凭据放 lab.env，已 gitignore；runs 放每一轮的交接、证据和 PPT；history 是早期经验摘要和原 RUNBOOK；presentation 就是这套 PPT。"
                        "右边是开场提示词，直接复制给任何 AI：读 AI_WORKFLOW.md 和 runs 下最近一轮的交接，说明这次的市场或 App 范围，并且要求它先给清单和需要确认的事项、不要动 lab。"
                        "AI 接手时要做到五件事：先读第 1 到 8 节和最近一轮交接；不要直接开始，先和用户确认；动 lab 前认领、结束释放；遵守硬规则；结论只以 FMC 连接事件实测命中为准。",
                        "How to hand this to your own AI. On the left, the ai_workflow folder: AI_WORKFLOW.md is the main document — idea, topology, "
                        "standard flow, Lua rules, verification, human checkpoints, hard rules, pitfalls, tools and history. AGENTS.md holds short rules "
                        "that AI assistants load automatically. pipeline/ has the Mac-side scripts that drive the VM, emulator and FMC, with hk/ as a "
                        "complete round template. apk_tools/ downloads, screenshots, builds evidence, publishes and cleans up. config/ only ships "
                        "lab.example.env — real credentials go in the gitignored lab.env. runs/ holds each round's handoff, evidence and deck; history/ "
                        "the early digest and original runbook; presentation/ this deck. On the right is the opening prompt to paste into any AI. On "
                        "taking over, the AI reads sections 1–8 and the latest handoff, confirms with the user before starting, claims and releases the "
                        "lab, follows the hard rules, and trusts only live FMC Connection Event hits."))
    tree = ("ai_workflow/\n"
            "├─ AI_WORKFLOW.md  " + d.T("# 主文档", "# main doc") + "\n"
            "├─ AGENTS.md       " + d.T("# AI 规则，自动加载", "# AI rules, auto-loaded") + "\n"
            "├─ pipeline/       " + d.T("# 驱动 VM/模拟器/FMC", "# drive VM/emulator/FMC") + "\n"
            "│  └─ hk/          " + d.T("# 一轮的完整模板", "# full round template") + "\n"
            "├─ apk_tools/      " + d.T("# 下载·截图·证据·发布", "# download·shots·publish") + "\n"
            "├─ config/         " + d.T("# lab.example.env", "# lab.example.env") + "\n"
            "├─ runs/           " + d.T("# 每轮交接与证据", "# per-round handoff") + "\n"
            "├─ history/        " + d.T("# 早期经验摘要", "# early digest") + "\n"
            "└─ presentation/   " + d.T("# 本 PPT", "# this deck"))
    d.code_block(s, 0.6, 1.75, 5.9, 4.3, tree, title=d.T("# 目录结构", "# folder layout"), size=13.5)
    prompt = d.T("读 NGFW_appdetector/ai_workflow/AI_WORKFLOW.md\n和 runs/ 下最近一轮的交接。\n"
                 "这次要做：<市场/App 范围>。\n先给我清单和需要确认的事项，不要动 lab。",
                 "Read NGFW_appdetector/ai_workflow/AI_WORKFLOW.md\nand the latest handoff under runs/.\n"
                 "This time: <market / app scope>.\nFirst give me the list and the open\nquestions. Do not touch the lab.")
    d.code_block(s, 6.75, 1.75, 5.98, 2.0, prompt, title=d.T("# 开场提示词（复制给任何 AI）", "# opening prompt (paste into any AI)"),
                 size=11.5)
    d.bullet_card(s, 6.75, 3.92, 5.98, 2.13, "bot", BLUE, d.T("AI 接手时", "When the AI takes over"), [
        d.T("先读第 1–8 节和最近一轮交接，不直接开始", "Read sections 1–8 + latest handoff; don't start yet"),
        d.T("先确认范围；动 lab 前认领，结束释放", "Confirm scope; claim the lab, release at the end"),
        d.T("只以 FMC 连接事件实测命中为准", "Trust only live FMC Connection Event hits"),
    ], size=12, gap=0.06, d=0.5, title_size=15)
    d.banner(s, "bot", d.T("方法写在文档里，不在某个 AI 的记忆里 —— Copilot、Claude Code、Codex、Cursor 都能接手",
                           "The method lives in docs, not in one AI's memory — Copilot, Claude Code, Codex or Cursor can take over"),
             accent=CYAN)


# ── 18 next steps ──────────────────────────────────────────────────────────
def s_next(d):
    s = d.new_slide(d.T("下一步", "Next steps"),
                    d.T("AI_WORKFLOW.md 第 12 节的待改进项", "Open items from section 12 of AI_WORKFLOW.md"),
                    notes=d.T(
                        "最后是下一步，来自 AI_WORKFLOW.md 第 12 节。第一，vmfetch.py 要首次在 lab 上验证，它是 11 月 26 日整理时新增的，目前只做过离线检查。"
                        "第二，发布用的 info.json，也就是包名、API 版本和规则摘要，现在还是手填，可以从生成 Lua 时输出的 *.summary.json 自动生成。"
                        "第三，Windows 进程模式 A 目前靠 App Detector Web UI 操作，还没有像 Android 那样的批量脚本，券商、视频这类 PC 客户端想规模化就需要补上。"
                        "第四，银行和政府类 App 在 root 模拟器上跑不起来，需要非 root 或真机方案才能覆盖，这也是香港这一轮 14 个失败的主要来源。"
                        "收尾：这套方法的价值在于可复制。大家可以拿开场提示词，选一个自己客户关心的市场，比如新加坡、马来西亚或者某个行业的 Top N，跑一轮，把新的坑和工具补回 AI_WORKFLOW.md 和 runs 目录。谢谢。",
                        "Next steps from section 12. First, run vmfetch.py on the lab for the first time — it was added on Nov 26 and has not run on "
                        "the lab yet. Second, info.json for publishing — package, API level and rule summary — is still hand-written and could be "
                        "generated from the *.summary.json files produced with each Lua. Third, Windows process mode A still relies on the App Detector "
                        "web UI and has no batch script like Android, which PC clients such as brokers and video apps need to scale. Fourth, banking and "
                        "government apps won't run on a rooted emulator; covering them needs a non-root or real-device approach — the main source of "
                        "the 14 Hong Kong failures. To close: the value is that it is repeatable. Take the opening prompt, pick a market your customers "
                        "care about, run a round, and add the new pitfalls and tools back to AI_WORKFLOW.md and runs/. Thank you."))
    d.grid_cards(s, [
        ("flask-conical", ORANGE, d.T("vmfetch.py 首次上 lab 验证", "First lab run of vmfetch.py"),
         d.T("11-26 新增，尚未在 lab 上跑过", "Added Nov 26, not yet run on the lab")),
        ("zap", BLUE, d.T("info.json 自动生成", "Auto-generate info.json"),
         d.T("发布用规则摘要从 *.summary.json 生成", "Build publish summaries from *.summary.json")),
        ("monitor", BLUE, d.T("模式 A 批量脚本", "Batch script for mode A"),
         d.T("Windows 进程模式目前靠 Web UI 操作", "Windows process mode still uses the web UI")),
        ("smartphone", ORANGE, d.T("覆盖银行 / 政府类 App", "Cover banking / gov apps"),
         d.T("需要非 root 或真机方案", "Needs a non-root or real-device setup")),
    ], rows=2, cols=2, h=4.3)
    d.banner(s, "rocket", d.T("选一个你的市场跑一轮，把新坑和新工具补回 AI_WORKFLOW.md",
                              "Run a round for your market and add new pitfalls and tools back to AI_WORKFLOW.md"), accent=BLUE)


SLIDES = [s_cover, s_gap, s_idea, s_loop, s_topo, s_modes, s_flow1, s_flow2, s_flow3, s_lua, s_verify, s_human,
          s_rules, s_pitfalls, s_results, s_hk, s_toolkit, s_next]
OUT = {"zh": "AI_NGFW_AppDetector_Workflow_中文.pptx", "en": "AI_NGFW_AppDetector_Workflow_EN.pptx"}


def build(lang):
    d = Deck(lang, footer=FOOTER)
    for fn in SLIDES:
        fn(d)
    return d.save(HERE / OUT[lang])


if __name__ == "__main__":
    for lang in ("zh", "en"):
        print(*build(lang))
