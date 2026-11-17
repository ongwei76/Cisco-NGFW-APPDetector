(() => {
  const translations = {
    en: {
      'nav.overview': 'Overview',
      'nav.search': 'FMC Connection Search',
      'nav.help': 'Help',
      'nav.language': '中文',
      "nav.share": "Shared Lua Library",
      "lua.share": "Submit selected Lua to the library",
      "share.title": "Shared Lua library",
      "share.description": "Download Lua detectors that the maintainer has reviewed and published, or submit your own detector for review. No GitHub account is needed.",
      "share.library": "Published detectors",
      "share.filter": "Filter by app, submitter, Host/SNI, notes",
      "share.refresh": "Refresh",
      "share.contactLine": "Questions about a detector? Contact the maintainer:",
      "share.download": "Download",
      "share.submit": "Submit a Lua to the maintainer",
      "share.step1": "Select a local Lua that you have validated on FMC and fill in the form.",
      "share.step2": "Click the button. The program creates a submission package (ZIP), saves it, and opens your email client with a message to the maintainer already filled in.",
      "share.step3": "Attach the ZIP to the email and send it. Email links cannot attach files automatically.",
      "share.step4": "The maintainer reviews it offline. After approval it appears in the list above for everyone, and the maintainer replies to your email either way.",
      "share.privacy": "Only your nickname is published. Your email address goes only to the maintainer so they can reply.",
      "share.luaFile": "Local Lua file",
      "share.nickname": "Nickname (published)",
      "share.email": "Your email (maintainer only)",
      "share.fmcVersion": "FMC version tested",
      "share.notes": "Notes (validation result, excluded CDN domains, known limits)",
      "share.submitButton": "Create package and email maintainer",
      "share.openMailAgain": "Open email again",
      "share.downloadPackage": "Download package again",
      "share.copyMail": "Copy email text",
      "share.noMailApp": "No email app opened. This computer probably has no default email program configured for mailto links (for example, the built-in Windows Mail app without an account). Click \"Copy email text\" and send it from your mailbox, and remember to attach the ZIP.",
      "share.copied": "Email text copied. Paste it into a new email, attach the ZIP, and send it.",
      "share.submitDone": "Package {file} was downloaded to your browser's Downloads folder, and a copy was saved to {path}. Your email client should now be open, addressed to {email}. <b>Attach the ZIP and send the email.</b> If no email client opened, click Copy email text and send it from your mailbox.",
      "share.mail.intro": "Hello, please review this Lua detector for the NGFW App Detector library.",
      "share.mail.attach": "Attachment: {file} (please attach it before sending)",
      "share.libraryFailed": "Unable to read the library:",
      "share.count": "{count} published detector(s).",
      "share.source.github-commit": "Source: latest GitHub commit (anonymous, no account needed).",
      "share.source.jsdelivr-commit": "Source: jsDelivr at the latest GitHub commit.",
      "share.source.github": "Source: GitHub Raw cache (live branch lookup unavailable; recent changes may be delayed).",
      "share.source.empty": "The maintainer has not published anything yet.",
      "share.source.jsdelivr": "Source: jsDelivr mirror (GitHub unreachable; recent changes may be delayed).",
      "share.empty": "No published Lua detectors yet.",
      "share.col.app": "Application",
      "share.col.submitter": "Submitted by",
      "share.col.published": "Published",
      "share.col.fmc": "FMC tested",
      "share.col.notes": "Notes",
      "share.col.actions": "Actions",
      "share.toolVersion": "Tool version",
      "share.reviewNote": "Maintainer:",
      "share.view": "View",
      "share.ask": "Ask",
      "share.patterns": "Host/SNI patterns:",
      "share.shaOk": "SHA256 verified",
      "share.shaBad": "SHA256 mismatch - do not use",
      "share.saved": "Saved.",
      "share.checking": "Testing GitHub connection…",
      "share.checkFailed": "Connection failed:",
      "share.category": "FMC application category",
      "share.risk": "Risk",
      "share.relevance": "Business relevance",
      "share.level.1": "Very Low",
      "share.level.2": "Low",
      "share.level.3": "Medium",
      "share.level.4": "High",
      "share.level.5": "Very High",
      "share.col.category": "Category",
      "share.categoryUnset": "not set",
      "share.selectAll": "Select all (latest versions)",
      "share.prevPage": "Previous",
      "share.nextPage": "Next",
      "share.pageInfo": "Page {page} of {pages} · {count} apps",
      "share.importButton": "Import selected to FMC",
      "share.importHint": "Imports the selected detectors into FMC (Policies > Application Detectors) using the FMC login configured on the Overview page. Each application is created with its category, risk and business relevance, and the detector is left <b>Inactive</b>. Applications that already exist in FMC are skipped. Activate and deploy them in FMC when ready.",
      "share.importNone": "Select at least one detector first.",
      "share.importConfirm": "Import {count} detector(s) into FMC {host}? They will be created Inactive; applications that already exist are skipped.",
      "share.importNoFmc": "FMC is not configured. Set the FMC host, username and password on the Overview page first.",
      "share.importing": "Importing {count} detector(s) into FMC… this can take a few seconds per detector.",
      "share.importDone": "FMC import finished: {imported} imported, {skipped} skipped, {failed} failed.",
      "share.importStatus.imported": "Imported (Inactive)",
      "share.importStatus.skipped": "Skipped",
      "share.importStatus.error": "Failed",
      'common.loading': 'loading…',
      'common.ready': 'Ready',
      'common.none': 'none yet',
      'common.optional': 'optional',
      'common.save': 'Save',
      'common.clear': 'Clear',
      'common.search': 'Search',
      'common.results': 'Results',
      'common.error': 'Error',
      'overview.title': 'Operational overview',
      'overview.description': 'Fingerprint local Windows applications and correlate them with FMC connection events.',
      'sidebar.fmc': 'FMC Connection',
      'sidebar.session': 'Session',
      'sidebar.runtime': 'Runtime state',
      'sidebar.flows': 'Flows seen',
      'sidebar.samples': 'Samples',
      'lua.history': 'Generated Lua',
      'lua.none': 'No generated Lua',
      'lua.choose': 'Choose a Lua file…',
      'lua.selectHint': 'Select a Lua file to view its content.',
      'lua.download': 'Download selected Lua',
      'lua.loadFailed': 'Unable to load this Lua file.',
      'summary.flows': 'Flows',
      'summary.flowsHint': 'local socket observations',
      'summary.samples': 'Samples',
      'summary.samplesHint': 'correlated hits',
      'summary.fingerprints': 'Fingerprints',
      'summary.fingerprintsHint': 'strong-signal candidates',
      'summary.lua': 'Lua',
      'summary.luaHint': 'generated detector files',
      'fmc.integration': 'FMC integration',
      'fmc.host': 'Host (FQDN or IP)',
      'fmc.username': 'Username',
      'fmc.password': 'Password',
      'fmc.passwordKeep': 'leave blank to keep existing',
      'fmc.domain': 'Domain UUID',
      'fmc.verifyTls': 'Verify TLS certificate',
      'fmc.pollInterval': 'Poll interval (s)',
      'fmc.lookback': 'Lookback window (s)',
      'fmc.persist': 'Also save to config.yaml',
      'fmc.test': 'Test connection',
      'session.orchestration': 'Session orchestration',
      'session.target': 'Target process',
      'session.loadingProcesses': 'Loading processes…',
      'session.exclude': 'Exclude hosts (comma separated)',
      'session.start': 'Start',
      'session.stop': 'Stop',
      'session.refresh': 'Refresh processes',
      'session.generate': 'Generate Lua',
      'session.generating': 'Generating Lua detector…',
      'session.generated': 'Generated {count} Lua detector file(s):',
      'session.generateFailed': 'Generate Lua failed:',
      'session.importHelp': 'How to import into FMC',
      'session.collecting': 'Collecting Local Flows and correlating them with FMC connection-event queries.',
      'session.stopWaiting': 'Local Flow capture has stopped. Please wait 20–30 seconds for delayed FMC events before generating Lua.',
      'session.drainCountdown': 'Waiting for delayed FMC events… approximately {seconds} seconds remaining. Generate Lua will be enabled when correlation is complete.',
      'session.drainComplete': 'FMC correlation is complete. Review the final events, then generate Lua.',
      'session.captureRunning': 'Stop the capture before generating a Lua detector.',
      'session.fmcDraining': 'FMC events are still arriving. Wait approximately {seconds} more seconds.',
      'session.notReady': 'No detector is ready. Capture and correlate at least {min} strong-signal FMC samples for the target process (current fingerprint candidates: {count}).',
      'flows.title': 'Local flows & FMC correlation',
      'flows.process': 'Process',
      'flows.proto': 'Proto',
      'flows.src': 'Src',
      'flows.dst': 'Dst',
      'flows.lastSeen': 'Last seen',
      'flows.fmcEvents': 'FMC Events',
      'flows.correlated': '{count} correlated connection event(s)',
      'flows.fmcExplanation': 'These are the flows observed by Secure Firewall Management Center.',
      'fingerprints.title': 'Fingerprints & Lua',
      'fingerprints.noLua': '(no .lua files yet — complete a capture, stop it, then click Generate Lua)',
      'fingerprints.generated': 'Generated:',
      'status.state': 'state',
      'status.error': 'error',
      'status.flows': 'flows',
      'status.samples': 'samples',
      'status.fingerprints': 'fingerprints ready/total',
      'status.started': 'started',
      'status.tracker': 'proc-tracker',
      'state.idle': 'idle',
      'state.running': 'running',
      'state.draining': 'waiting for FMC',
      'state.stopped': 'stopped',
      'state.error': 'error',
      'table.time': 'Time (UTC)',
      'table.action': 'Action',
      'table.sourceIp': 'Source IP',
      'table.sourcePort': 'Sport',
      'table.destinationIp': 'Destination IP',
      'table.destinationPort': 'Dport',
      'table.protocol': 'Protocol',
      'table.webApp': 'Web App',
      'table.rule': 'Rule',
      'table.policy': 'Policy',
      'table.sensor': 'Sensor',
      'table.bytesSent': 'Bytes sent',
      'table.bytesRecv': 'Bytes recv',
      'table.eventId': 'Event ID',
      'table.webAppTags': 'Web App Tags',
      'table.detectionType': 'Detection Type',
      'table.host': 'Referenced Host / SNI',
      'table.referer': 'HTTP Referer',
      'table.userAgent': 'User-Agent',
      'table.info': 'Info / URL',
      'table.tlsFingerprint': 'TLS Fingerprint',
      'search.title': 'FMC connection search',
      'search.description': 'Filter live connection events from the FMC Web UI without exporting data.',
      'search.back': 'Back to overview',
      'search.filters': 'Search filters',
      'search.sourceIp': 'Source IP',
      'search.destinationIp': 'Destination IP',
      'search.sourcePort': 'Source port',
      'search.destinationPort': 'Destination port',
      'search.webApp': 'Web App',
      'search.protocol': 'Protocol',
      'search.since': 'Since (seconds)',
      'search.limit': 'Limit',
      'search.noSearch': 'No search yet.',
      'search.searching': 'Searching…',
      'search.failed': 'Search failed:',
      'search.noMatches': 'No events matched.',
      'search.rows': '{count} row(s)',
      'search.window': 'window',
      'search.filter': 'filter',
      'search.noFilter': 'no filter',
      'fmc.current': 'Current',
      'fmc.user': 'user',
      'fmc.passwordLabel': 'password',
      'fmc.set': 'set',
      'fmc.unset': 'unset',
      'fmc.configFile': 'config file',
      'fmc.savedMemory': 'Saved in memory.',
      'fmc.savedFile': 'Saved and written to',
      'fmc.saveFailed': 'Save failed:',
      'fmc.testing': 'Testing…',
      'fmc.testFailed': 'Test failed:',
      'process.unavailable': 'Unable to load processes',
      'session.startFailed': 'Start failed:',
      'generate.title': 'Name the application',
      'generate.appName': 'Application name',
      'generate.rules': 'Use 1–15 English letters or underscores only. This name appears in FMC.',
      'generate.invalid': 'Enter 1–15 English letters or underscores only.',
      'generate.signalsTitle': 'Review detector signals',
      'generate.cdnRisk': 'Shared CDN domains can classify unrelated applications and may affect policies that use this custom application. Select any CDN/shared domains to exclude them from the Lua.',
      'generate.signalsFailed': 'Unable to load detector signals.',
      'generate.noSignals': 'No ready Host/SNI signals are available.',
      'generate.signal.tls_sni': 'TLS SNI',
      'generate.signal.tls_certificate': 'TLS Certificate',
      'generate.signal.tls_host_suffix': 'TLS Host Suffix',
      'generate.signal.http_host': 'HTTP Host',
      'generate.markCdn': 'Exclude as CDN',
      'generate.historyCdn': 'Previously marked CDN',
      'generate.historyWarningTitle': 'Previously marked CDN domains found',
      'generate.historyWarningQuestion': 'These signals were previously excluded as CDN but are not selected now. Do you want to exclude them again?',
      'generate.excludeAndGenerate': 'Exclude and generate',
      'generate.keepAndGenerate': 'Keep and generate',
      'generate.reviewAgain': 'Review again',
      'generate.noSignalsAfterExclusion': 'All usable Host/SNI signals were excluded. Keep at least one non-CDN signal before generating.',
      'generate.confirm': 'Generate',
      'generate.cancel': 'Cancel',
      'help.close': 'Close help',
    },
    zh: {
      'nav.overview': '概览',
      'nav.search': 'FMC 连接事件查询',
      'nav.help': '帮助',
      'nav.language': 'English',
      "nav.share": "Lua 共享库",
      "lua.share": "提交所选 Lua 到共享库",
      "share.title": "Lua 共享库",
      "share.description": "下载维护者审核并发布的 Lua Detector，也可以把你自己的 Detector 提交审核。不需要 GitHub 账号。",
      "share.library": "已发布的 Detector",
      "share.filter": "按应用、提交者、Host/SNI、备注筛选",
      "share.refresh": "刷新",
      "share.contactLine": "对 Detector 有疑问？请联系维护者：",
      "share.download": "下载",
      "share.submit": "提交 Lua 给维护者",
      "share.step1": "选择一个已经在 FMC 上验证过的本地 Lua，填写下面的表单。",
      "share.step2": "点击按钮后，程序会生成提交包（ZIP）并保存，同时打开邮件程序，收件人和邮件内容都已填好。",
      "share.step3": "把 ZIP 作为附件加到邮件里再发送（邮件链接无法自动添加附件）。",
      "share.step4": "维护者离线审核。通过后，所有人都能在上面的列表里看到；无论是否通过，维护者都会回复你的邮件。",
      "share.privacy": "只会公开你的昵称。你的邮箱只发给维护者，用于回复你。",
      "share.luaFile": "本地 Lua 文件",
      "share.nickname": "昵称（会公开）",
      "share.email": "你的邮箱（仅维护者可见）",
      "share.fmcVersion": "测试的 FMC 版本",
      "share.notes": "备注（验证结果、排除的 CDN 域名、已知限制）",
      "share.submitButton": "生成提交包并发邮件给维护者",
      "share.openMailAgain": "重新打开邮件",
      "share.downloadPackage": "重新下载提交包",
      "share.copyMail": "复制邮件内容",
      "share.noMailApp": "没有检测到邮件程序打开。这台电脑可能没有配置处理邮件链接的默认邮件程序（例如 Windows 自带的“邮件”应用还没有添加账号）。请点击“复制邮件内容”，在你的邮箱里发送，并记得添加 ZIP 附件。",
      "share.copied": "邮件内容已复制。请粘贴到新邮件中，添加 ZIP 附件后发送。",
      "share.submitDone": "提交包 {file} 已下载到浏览器的“下载”文件夹，另存了一份在 {path}。邮件程序应该已经打开，收件人是 {email}。<b>请添加 ZIP 附件后发送邮件。</b>如果没有弹出邮件程序，请点击“复制邮件内容”，在你的邮箱里发送。",
      "share.mail.intro": "您好，请审核这个 NGFW App Detector 共享库的 Lua Detector。",
      "share.mail.attach": "附件：{file}（发送前请先添加附件）",
      "share.libraryFailed": "无法读取共享库：",
      "share.count": "共 {count} 个已发布的 Detector。",
      "share.source.github-commit": "来源：GitHub 最新提交（匿名读取，无需账号）。",
      "share.source.jsdelivr-commit": "来源：jsDelivr 镜像中的 GitHub 最新提交。",
      "share.source.github": "来源：GitHub Raw 缓存（无法查询最新提交，最新变化可能有延迟）。",
      "share.source.empty": "维护者还没有发布任何内容。",
      "share.source.jsdelivr": "来源：jsDelivr 镜像（GitHub 无法访问，最新变化可能有延迟）。",
      "share.empty": "还没有已发布的 Lua Detector。",
      "share.col.app": "应用",
      "share.col.submitter": "提交者",
      "share.col.published": "发布时间",
      "share.col.fmc": "测试的 FMC 版本",
      "share.col.notes": "备注",
      "share.col.actions": "操作",
      "share.toolVersion": "工具版本",
      "share.reviewNote": "维护者：",
      "share.view": "查看",
      "share.ask": "咨询",
      "share.patterns": "Host/SNI 规则：",
      "share.shaOk": "SHA256 校验通过",
      "share.shaBad": "SHA256 不一致，请勿使用",
      "share.saved": "已保存。",
      "share.checking": "正在测试 GitHub 连接…",
      "share.checkFailed": "连接失败：",
      "share.category": "FMC 应用分类",
      "share.risk": "风险等级",
      "share.relevance": "业务相关性",
      "share.level.1": "很低",
      "share.level.2": "低",
      "share.level.3": "中",
      "share.level.4": "高",
      "share.level.5": "很高",
      "share.col.category": "分类",
      "share.categoryUnset": "未设置",
      "share.selectAll": "全选（最新版本）",
      "share.prevPage": "上一页",
      "share.nextPage": "下一页",
      "share.pageInfo": "第 {page} / {pages} 页 · 共 {count} 个应用",
      "share.importButton": "导入所选到 FMC",
      "share.importHint": "把所选 Detector 导入 FMC（Policies > Application Detectors），使用概览页里配置的 FMC 登录信息。每个应用会按其分类、风险等级和业务相关性创建，Detector 保持 <b>Inactive（未激活）</b>。FMC 中已存在的应用会被跳过。准备好后请在 FMC 中激活并部署。",
      "share.importNone": "请先勾选至少一个 Detector。",
      "share.importConfirm": "确定把 {count} 个 Detector 导入 FMC {host} 吗？导入后为未激活状态；已存在的应用会被跳过。",
      "share.importNoFmc": "还没有配置 FMC。请先在概览页设置 FMC 地址、用户名和密码。",
      "share.importing": "正在把 {count} 个 Detector 导入 FMC…每个大约需要几秒。",
      "share.importDone": "FMC 导入完成：成功 {imported} 个，跳过 {skipped} 个，失败 {failed} 个。",
      "share.importStatus.imported": "已导入（未激活）",
      "share.importStatus.skipped": "已跳过",
      "share.importStatus.error": "失败",
      'common.loading': '加载中…',
      'common.ready': '就绪',
      'common.none': '暂无数据',
      'common.optional': '可选',
      'common.save': '保存',
      'common.clear': '清空',
      'common.search': '查询',
      'common.results': '查询结果',
      'common.error': '错误',
      'overview.title': '运行概览',
      'overview.description': '识别本地 Windows 应用流量，并与 FMC 连接事件进行关联。',
      'sidebar.fmc': 'FMC 连接',
      'sidebar.session': '采集会话',
      'sidebar.runtime': '运行状态',
      'sidebar.flows': '本地 Flow',
      'sidebar.samples': '关联样本',
      'lua.history': '历史生成的 Lua',
      'lua.none': '暂无 Lua 文件',
      'lua.choose': '请选择 Lua 文件…',
      'lua.selectHint': '选择一个 Lua 文件后在这里查看内容。',
      'lua.download': '下载所选 Lua',
      'lua.loadFailed': '无法加载该 Lua 文件。',
      'summary.flows': '本地 Flow',
      'summary.flowsHint': '本地 Socket 观测',
      'summary.samples': '关联样本',
      'summary.samplesHint': '成功关联的 FMC 事件',
      'summary.fingerprints': '指纹',
      'summary.fingerprintsHint': '强信号候选规则',
      'summary.lua': 'Lua',
      'summary.luaHint': '已生成的 Detector 文件',
      'fmc.integration': 'FMC 集成配置',
      'fmc.host': 'FMC 地址（FQDN 或 IP）',
      'fmc.username': '用户名',
      'fmc.password': '密码',
      'fmc.passwordKeep': '留空可保留现有密码',
      'fmc.domain': 'Domain UUID',
      'fmc.verifyTls': '验证 TLS 证书',
      'fmc.pollInterval': '轮询间隔（秒）',
      'fmc.lookback': '回溯窗口（秒）',
      'fmc.persist': '同时保存到 config.yaml',
      'fmc.test': '测试连接',
      'session.orchestration': '采集与生成',
      'session.target': '目标进程',
      'session.loadingProcesses': '正在加载进程…',
      'session.exclude': '排除的 Host（逗号分隔）',
      'session.start': '开始采集',
      'session.stop': '停止采集',
      'session.refresh': '刷新进程',
      'session.generate': '生成 Lua',
      'session.generating': '正在生成 Lua Detector…',
      'session.generated': '已生成 {count} 个 Lua Detector：',
      'session.generateFailed': '生成 Lua 失败：',
      'session.importHelp': '如何导入 FMC',
      'session.collecting': '正在收集 Local Flow，并开始查询和关联 FMC Connection Events。',
      'session.stopWaiting': '本地 Flow 采集已停止。请等待 20–30 秒，让延迟到达的 FMC Event 完成关联后再生成 Lua。',
      'session.drainCountdown': '正在等待延迟到达的 FMC Event，预计还需 {seconds} 秒。关联完成前“生成 Lua”按钮不可用。',
      'session.drainComplete': 'FMC Event 关联已完成。请检查最终事件，然后生成 Lua。',
      'session.captureRunning': '请先停止采集，再生成 Lua Detector。',
      'session.fmcDraining': 'FMC Event 仍在到达，请再等待大约 {seconds} 秒。',
      'session.notReady': '尚无可生成的 Detector。请为目标进程采集并关联至少 {min} 条包含强信号的 FMC 样本（当前指纹候选：{count}）。',
      'flows.title': '本地 Flow 与 FMC 关联',
      'flows.process': '进程',
      'flows.proto': '协议',
      'flows.src': '本地端点',
      'flows.dst': '远端端点',
      'flows.lastSeen': '最后发现时间',
      'flows.fmcEvents': 'FMC 事件',
      'flows.correlated': '{count} 条关联连接事件',
      'flows.fmcExplanation': '以下 Flow 来自 Secure Firewall Management Center。',
      'fingerprints.title': '指纹与 Lua Detector',
      'fingerprints.noLua': '（尚未生成 .lua 文件，请完成采集、停止后再点击“生成 Lua”）',
      'fingerprints.generated': '已生成：',
      'status.state': '状态',
      'status.error': '错误',
      'status.flows': 'Flow',
      'status.samples': '样本',
      'status.fingerprints': '就绪/全部指纹',
      'status.started': '开始时间',
      'status.tracker': '进程跟踪',
      'state.idle': '空闲',
      'state.running': '采集中',
      'state.draining': '等待 FMC Event',
      'state.stopped': '已停止',
      'state.error': '错误',
      'table.time': '时间（UTC）',
      'table.action': '动作',
      'table.sourceIp': '源 IP',
      'table.sourcePort': '源端口',
      'table.destinationIp': '目的 IP',
      'table.destinationPort': '目的端口',
      'table.protocol': '协议',
      'table.webApp': 'Web 应用',
      'table.rule': '规则',
      'table.policy': '策略',
      'table.sensor': '传感器',
      'table.bytesSent': '发送字节',
      'table.bytesRecv': '接收字节',
      'table.eventId': '事件 ID',
      'table.webAppTags': 'Web 应用标签',
      'table.detectionType': '检测类型',
      'table.host': '关联 Host / SNI',
      'table.referer': 'HTTP Referer',
      'table.userAgent': 'User-Agent',
      'table.info': '信息 / URL',
      'table.tlsFingerprint': 'TLS 指纹',
      'search.title': 'FMC 连接事件查询',
      'search.description': '直接查询 FMC Web UI 中的实时连接事件，无需导出数据。',
      'search.back': '返回概览',
      'search.filters': '查询条件',
      'search.sourceIp': '源 IP',
      'search.destinationIp': '目的 IP',
      'search.sourcePort': '源端口',
      'search.destinationPort': '目的端口',
      'search.webApp': 'Web 应用',
      'search.protocol': '协议',
      'search.since': '回溯时间（秒）',
      'search.limit': '最大结果数',
      'search.noSearch': '尚未执行查询。',
      'search.searching': '正在查询…',
      'search.failed': '查询失败：',
      'search.noMatches': '没有匹配的事件。',
      'search.rows': '{count} 条记录',
      'search.window': '时间窗口',
      'search.filter': '过滤条件',
      'search.noFilter': '无过滤条件',
      'fmc.current': '当前',
      'fmc.user': '用户',
      'fmc.passwordLabel': '密码',
      'fmc.set': '已设置',
      'fmc.unset': '未设置',
      'fmc.configFile': '配置文件',
      'fmc.savedMemory': '已保存到当前运行实例。',
      'fmc.savedFile': '已保存并写入',
      'fmc.saveFailed': '保存失败：',
      'fmc.testing': '正在测试…',
      'fmc.testFailed': '测试失败：',
      'process.unavailable': '无法加载进程',
      'session.startFailed': '启动失败：',
      'generate.title': '设置应用名称',
      'generate.appName': '应用名称',
      'generate.rules': '仅允许 1–15 个英文字母或下划线；该名称将显示在 FMC 中。',
      'generate.invalid': '请输入 1–15 个英文字母或下划线。',
      'generate.signalsTitle': '检查 Detector 匹配特征',
      'generate.cdnRisk': '共享 CDN 域名可能把无关应用错误识别为该应用，并影响引用该自定义应用的策略。请勾选 CDN/共享域名，将其从 Lua 中排除。',
      'generate.signalsFailed': '无法加载 Detector 匹配特征。',
      'generate.noSignals': '当前没有可用的 Host/SNI 强特征。',
      'generate.signal.tls_sni': 'TLS SNI',
      'generate.signal.tls_certificate': 'TLS 证书名称',
      'generate.signal.tls_host_suffix': 'TLS 域名后缀',
      'generate.signal.http_host': 'HTTP Host',
      'generate.markCdn': '作为 CDN 排除',
      'generate.historyCdn': '历史曾标记为 CDN',
      'generate.historyWarningTitle': '发现历史 CDN 记录',
      'generate.historyWarningQuestion': '这些特征以前曾作为 CDN 排除，但本次没有勾选。是否再次排除？',
      'generate.excludeAndGenerate': '排除并生成',
      'generate.keepAndGenerate': '保留并生成',
      'generate.reviewAgain': '返回检查',
      'generate.noSignalsAfterExclusion': '所有可用的 Host/SNI 特征都已被排除。请至少保留一个非 CDN 强特征后再生成。',
      'generate.confirm': '生成',
      'generate.cancel': '取消',
      'help.close': '关闭帮助',
    },
  };

  const help = {
    en: {
      overview: {
        title: 'NGFW App Detector workflow',
        body: `
          <p><b>Purpose:</b> This tool observes network sockets created by a selected Windows process, correlates the five-tuples with FMC connection events, extracts stable Host/SNI/certificate signals, and generates a Snort 3 Lua App Detector.</p>
          <h3>End-to-end workflow</h3>
          <ol>
            <li>Configure the FMC host and credentials, save them, then use <b>Test connection</b>.</li>
            <li>Select the target process. Start the application first if it is not listed.</li>
            <li>Click <b>Start</b>, then exercise the target application so it creates representative traffic.</li>
            <li>Click <b>Stop</b>. Local capture stops immediately while FMC polling continues for up to 30 seconds to collect delayed events; the final table is then frozen.</li>
            <li>Expand a Local Flow to review the matching <b>FMC EVENT</b> rows and their detection fields.</li>
            <li>Confirm that enough strong-signal fingerprints are ready, then click <b>Generate Lua</b>.</li>
            <li>Download the generated Lua file. In FMC, open the custom Application Detector area, import/create the detector from the Lua content, activate it, and deploy policy changes to the FTD.</li>
            <li>Restart the target application and validate new FMC Connection Events show the custom application name.</li>
          </ol>
          <h3>How correlation and generation work</h3>
          <p>Local process sockets and FMC events are correlated by normalized five-tuple, direction, and time window. Detector rules are generated only from strong application signals such as HTTP Host, TLS SNI, and certificate names. Port, IP, URI-only, and User-Agent-only observations are not sufficient.</p>
          <h3 id="import-lua">How to import a Lua Local App Detector into FMC</h3>
          <ol>
            <li><b>Review and back up:</b> open the generated Lua in the left-side history viewer. Confirm the application name and Host/SNI patterns belong only to the target application. Export the current FMC configuration or create an appropriate backup before production changes.</li>
            <li><b>Create the detector:</b> in FMC, open <b>Policies → Application Detectors</b> (menu wording may vary by release), choose <b>Create Detector</b>, and select the advanced/custom Lua detector workflow.</li>
            <li><b>Configure identity:</b> enter the same ASCII application name used during generation and a clear description. Create or select the custom application entries required by the detector. Replace placeholder application IDs in the Lua if the FMC workflow assigns different IDs.</li>
            <li><b>Add the Lua:</b> paste or upload the generated script in the detector editor. Save it, resolve any FMC validation errors, then mark the detector <b>Active</b>.</li>
            <li><b>Deploy:</b> deploy the configuration to the FTD devices that inspect the target traffic. Wait for deployment to complete before testing.</li>
            <li><b>Generate fresh traffic:</b> close and reopen the target desktop application so new connections are created. Existing long-lived connections may retain their previous classification.</li>
            <li><b>Verify:</b> open <b>FMC Connection Search</b>, enter the generated name in the <b>Web App</b> filter, choose a suitable lookback window, and confirm new events show that application.</li>
          </ol>
          <h3>Enablement and business-impact guidance</h3>
          <ul>
            <li>Activating a detector changes application classification. It does not block traffic by itself, but any Access Control, QoS, SSL, IPS, or reporting logic that references the custom application can change behavior.</li>
            <li>Shared CDN or overly broad domain patterns can misclassify unrelated business traffic. Validate in a test policy/device first and inspect Connection Events before using the application in enforcement rules.</li>
            <li>FMC deployment can update inspection configuration on managed FTDs. Use a change window, monitor deployment health, and keep a rollback plan.</li>
            <li>Enable Connection Event logging on the relevant Access Control rules. Detector matches may not be visible immediately because FTD analysis, event logging, and FMC ingestion introduce delay.</li>
            <li>If false positives occur, deactivate the detector or remove it from policy, redeploy, then refine exclusions and regenerate the Lua.</li>
          </ul>
          <h3>Important cautions</h3>
          <ul>
            <li>Enable connection-event logging in the relevant FMC Access Control rules.</li>
            <li>Capture multiple representative sessions; incidental CDN or shared-service domains should be excluded.</li>
            <li>Review the generated Lua before production deployment and validate hits after policy deployment.</li>
            <li>Persisting FMC settings writes the configured credentials to the local config file; protect its filesystem permissions.</li>
          </ul>`,
      },
      fmc: {
        title: 'FMC Connection Search help',
        body: `
          <p>Use this page to inspect the same FMC connection-event source used by correlation.</p>
          <ol>
            <li>Enter any known source/destination IP or port. Leave fields blank to search broadly.</li>
            <li>Choose TCP or UDP, set the lookback window and result limit, then click <b>Search</b>.</li>
            <li>Expand an event to inspect Sensor, bytes, Event ID, Web App, Detection Type, Host/SNI, URL, and TLS fingerprint.</li>
            <li>Use the five-tuple and timestamp to compare an FMC event with a Local Flow on the Overview page.</li>
          </ol>
          <p><b>Note:</b> This private FMC Web UI event source is used because the supported FMC REST endpoints do not expose the required connection-event fields in this environment.</p>`,
      },
      share: {
        title: 'Shared Lua Library help',
        body: `
          <p>The library is maintained by one maintainer. Users <b>do not need a GitHub account</b>: the program reads the published list anonymously from GitHub, and falls back to the jsDelivr mirror when GitHub is unreachable.</p>
          <h3>Using a published detector</h3>
          <ol>
            <li>Find the application in <b>Published detectors</b> and click <b>View</b>. Check the Host/SNI patterns and the <b>SHA256 verified</b> badge. Download is refused if the SHA256 does not match.</li>
            <li>Click <b>Download</b> and import the Lua into FMC using the procedure in the Overview help, then confirm hits in FMC Connection Search.</li>
            <li>For questions, click <b>Ask</b> to email the maintainer; the subject already contains the detector name and version.</li>
          </ol>
          <h3>Submitting your detector</h3>
          <ol>
            <li>Validate the Lua on FMC first. Select it under <b>Submit a Lua to the maintainer</b>, enter a nickname, your email, the FMC version, and notes.</li>
            <li>Click <b>Create package and email maintainer</b>. The ZIP (Lua + submission.json with the SHA256) is downloaded and also saved under <code>generated_detectors/submissions</code>, and your email client opens.</li>
            <li><b>Attach the ZIP</b> and send the email. Without an email client, use <b>Copy email text</b> and send it from webmail.</li>
          </ol>
          <p><b>Privacy:</b> only the nickname, Lua, and notes are published. Your email is seen only by the maintainer.</p>
          <p><b>Delay:</b> a newly published detector appears within about 5 minutes from GitHub; the jsDelivr mirror can take up to 12 hours.</p>`,
      },
    },
    zh: {
      overview: {
        title: 'NGFW App Detector 使用流程',
        body: `
          <p><b>产品作用：</b>本工具采集指定 Windows 进程创建的网络 Socket，与 FMC Connection Events 按五元组和时间进行关联，提取稳定的 Host、SNI、证书等强信号，并生成 Snort 3 Lua App Detector。</p>
          <h3>端到端使用步骤</h3>
          <ol>
            <li>填写 FMC 地址和账号，保存后点击<b>测试连接</b>。</li>
            <li>选择目标进程。如果列表中没有该进程，请先启动目标应用，再刷新进程列表。</li>
            <li>点击<b>开始采集</b>，在目标应用中执行有代表性的业务操作，使其产生网络流量。</li>
            <li>点击<b>停止采集</b>。本地采集立即停止，FMC 查询继续最多 30 秒以接收迟到事件；完成后最终表格自动冻结。</li>
            <li>展开 Local Flow，确认其下方标记为 <b>FMC EVENT</b> 的连接事件及检测字段。</li>
            <li>确认已有足够的强信号指纹后，点击<b>生成 Lua</b>并下载文件。</li>
            <li>在 FMC 的自定义 Application Detector 页面导入或按 Lua 内容创建 Detector，激活后将策略部署到 FTD。</li>
            <li>重新启动目标应用并产生流量，在 FMC Connection Events 中验证自定义应用名称是否命中。</li>
          </ol>
          <h3>关联与生成原理</h3>
          <p>本地进程 Socket 与 FMC Event 按归一化五元组、方向和时间窗口进行关联。Detector 只使用 HTTP Host、TLS SNI、证书名称等强应用信号；仅端口、IP、URI 或 User-Agent 不足以生成规则。</p>
          <h3 id="import-lua">如何在 FMC 导入 Lua Local App Detector</h3>
          <ol>
            <li><b>检查并备份：</b>先在左侧历史 Lua 查看器中打开脚本，确认应用名称以及 Host/SNI 规则仅属于目标应用。生产环境变更前，请导出当前 FMC 配置或完成适当备份。</li>
            <li><b>创建 Detector：</b>在 FMC 打开<b>策略（Policies）→ Application Detectors</b>（不同版本菜单名称可能略有差异），点击<b>创建 Detector</b>，选择高级/自定义 Lua Detector 流程。</li>
            <li><b>配置应用身份：</b>填写生成时使用的同一英文应用名称和清晰描述；创建或选择 Detector 所需的自定义应用。如果 FMC 分配的应用 ID 与 Lua 中的占位 ID 不同，需要按 FMC 分配结果替换。</li>
            <li><b>添加 Lua：</b>在 Detector 编辑器中粘贴或上传生成的脚本，保存并修复 FMC 提示的语法或配置错误，然后将 Detector 设置为<b>启用（Active）</b>。</li>
            <li><b>部署配置：</b>将变更部署到负责检测目标流量的 FTD，等待部署成功后再测试。</li>
            <li><b>产生新流量：</b>关闭并重新启动目标桌面应用，使其建立新连接。已存在的长连接可能仍保留旧的应用分类。</li>
            <li><b>验证命中：</b>打开<b>FMC 连接事件查询</b>，在 <b>Web 应用</b>字段输入生成的名称，设置合适的回溯时间，确认新事件已显示该应用。</li>
          </ol>
          <h3>启用影响与业务风险</h3>
          <ul>
            <li>启用 Detector 会改变应用分类，本身不会自动阻断流量；但引用该自定义应用的访问控制、QoS、SSL、IPS 或报表逻辑可能随之改变。</li>
            <li>共享 CDN 或过宽的域名规则可能把无关业务误识别为目标应用。请先在测试策略/设备验证，并检查 Connection Events，再用于阻断等强制策略。</li>
            <li>FMC 部署会更新受管 FTD 的检测配置。生产环境应安排变更窗口、监控部署状态，并准备回退方案。</li>
            <li>相关 Access Control 规则必须启用 Connection Event 日志。FTD 分析、事件记录及 FMC 入库会产生一定延迟，Detector 命中不会立即显示。</li>
            <li>如果发生误报，请停用 Detector 或从策略移除后重新部署，再调整排除域名并重新生成 Lua。</li>
          </ul>
          <h3>注意事项</h3>
          <ul>
            <li>必须在相关 FMC Access Control 规则中启用连接事件日志。</li>
            <li>建议采集多次有代表性的会话，并排除 CDN、系统更新等共享服务域名。</li>
            <li>生产部署前请检查生成的 Lua，并在策略部署后验证真实命中。</li>
            <li>选择持久化 FMC 设置会把配置写入本地文件，请保护该文件的访问权限。</li>
          </ul>`,
      },
      fmc: {
        title: 'FMC 连接事件查询帮助',
        body: `
          <p>本页面用于查看 Correlation 所使用的同一来源 FMC Connection Events。</p>
          <ol>
            <li>输入已知的源/目的 IP 或端口；留空可以扩大查询范围。</li>
            <li>选择 TCP 或 UDP，设置回溯窗口与结果数量，然后点击<b>查询</b>。</li>
            <li>展开事件可查看 Sensor、字节数、Event ID、Web App、检测类型、Host/SNI、URL 和 TLS 指纹。</li>
            <li>使用五元组和时间戳，与概览页面的 Local Flow 进行比对。</li>
          </ol>
          <p><b>说明：</b>当前环境的 FMC 公共 REST API 不提供所需的完整连接事件字段，因此产品使用 FMC Web UI 的事件数据源。</p>`,
      },
      share: {
        title: 'Lua 共享库帮助',
        body: `
          <p>共享库由一位维护者统一管理。使用者<b>不需要 GitHub 账号</b>：程序会匿名从 GitHub 读取已发布列表，GitHub 无法访问时自动改用 jsDelivr 镜像。</p>
          <h3>使用已发布的 Detector</h3>
          <ol>
            <li>在<b>已发布的 Detector</b>中找到应用，点击<b>查看</b>，检查 Host/SNI 规则和<b>SHA256 校验通过</b>标记。SHA256 不一致时程序会拒绝下载。</li>
            <li>点击<b>下载</b>，按照概览页帮助中的步骤导入 FMC，再在 FMC 连接事件查询页面确认命中。</li>
            <li>有疑问时点击<b>咨询</b>给维护者发邮件，邮件标题会自动带上 Detector 名称和版本。</li>
          </ol>
          <h3>提交自己的 Detector</h3>
          <ol>
            <li>先在 FMC 上验证好 Lua，再在<b>提交 Lua 给维护者</b>中选择它，填写昵称、邮箱、FMC 版本和备注。</li>
            <li>点击<b>生成提交包并发邮件给维护者</b>：ZIP（包含 Lua 和带 SHA256 的 submission.json）会被下载，同时保存在 <code>generated_detectors/submissions</code>，并打开邮件程序。</li>
            <li><b>添加 ZIP 附件</b>后发送。如果没有邮件程序，点击<b>复制邮件内容</b>，用网页邮箱发送。</li>
          </ol>
          <p><b>隐私：</b>只会公开昵称、Lua 内容和备注；你的邮箱只有维护者能看到。</p>
          <p><b>延迟：</b>新发布的 Detector 一般 5 分钟内可以从 GitHub 看到；jsDelivr 镜像最长可能需要 12 小时。</p>`,
      },
    },
  };

  let language = localStorage.getItem('ngfw-language')
    || (navigator.language.toLowerCase().startsWith('zh') ? 'zh' : 'en');

  function t(key, values = {}) {
    let text = translations[language][key] ?? translations.en[key] ?? key;
    Object.entries(values).forEach(([name, value]) => {
      text = text.replaceAll(`{${name}}`, String(value));
    });
    return text;
  }

  function applyTranslations() {
    document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en';
    document.querySelectorAll('[data-i18n]').forEach((element) => {
      element.textContent = t(element.dataset.i18n);
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach((element) => {
      element.placeholder = t(element.dataset.i18nPlaceholder);
    });
    window.dispatchEvent(new CustomEvent('languagechange', {detail: {language}}));
  }

  function toggleLanguage() {
    language = language === 'en' ? 'zh' : 'en';
    localStorage.setItem('ngfw-language', language);
    applyTranslations();
  }

  function openHelp(section = '') {
    const page = document.body.dataset.page || 'overview';
    const content = help[language][page] || help[language].overview;
    document.getElementById('helpTitle').textContent = content.title;
    document.getElementById('helpContent').innerHTML = content.body;
    document.getElementById('helpModal').hidden = false;
    document.body.classList.add('modal-open');
    if (section) {
      requestAnimationFrame(() => {
        const target = document.getElementById(section);
        if (target) target.scrollIntoView({block: 'start'});
      });
    }
  }

  function closeHelp() {
    document.getElementById('helpModal').hidden = true;
    document.body.classList.remove('modal-open');
  }

  document.addEventListener('DOMContentLoaded', applyTranslations);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeHelp();
  });

  window.appI18n = {
    t,
    language: () => language,
    toggleLanguage,
    openHelp,
    closeHelp,
    applyTranslations,
  };
})();
