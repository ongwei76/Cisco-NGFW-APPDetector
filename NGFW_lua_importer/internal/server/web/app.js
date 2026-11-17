"use strict";
const TOKEN = document.querySelector('meta[name="token"]').content;
const PAGE_SIZE = 6;
const $ = (id) => document.getElementById(id);

const I18N = {
  zh: {
    title: "NGFW Lua 导入工具", subtitle: "从共享库选择 OpenAppID Lua，一键上传到 Cisco FMC",
    aboutTitle: "上传方式与版本", progVer: "程序版本", testedFmc: "已验证 FMC 版本", connectedFmc: "当前 FMC 版本",
    method: "上传方式", library: "共享库",
    methodText: "通过 HTTPS 模拟 FMC Web 管理界面的操作（与在 Policies → Application Detectors 中手工新建 Detector 并上传 Lua 相同的内部接口：login.cgi、pjb.cgi、detectors.cgi），不使用 FMC 公开 REST API（REST API 不支持上传自定义 Lua）。",
    compat: "遇到兼容性问题（例如 FMC 版本不同导致上传失败），请发送邮件至", compat2: "（点击会自动附带版本与错误信息）",
    fmcTitle: "FMC 连接", host: "FMC 地址", user: "用户名", pass: "密码", verify: "校验 HTTPS 证书", test: "测试连接", save: "保存",
    saved: "已保存 FMC 地址、用户名和证书设置（密码不会写入磁盘）", needHost: "请先填写 FMC 地址",
    passHint: "密码只保存在本页面内存中，不会写入磁盘。",
    sessionHint: "FMC 每个账号只保留一个 Web 会话：本工具登录会使同一账号在浏览器中的 FMC 会话退出，建议使用单独的 FMC 账号。",
    libTitle: "共享 Lua 库", selAll: "全选", search: "搜索应用 / 分类 / 备注", refresh: "刷新",
    cApp: "应用", cVer: "版本", cCat: "分类 / 风险 / 业务相关", cFmc: "验证 FMC", cNotes: "备注",
    cStatus: "状态", cActive: "激活", cMsg: "说明", view: "查看 Lua",
    importTitle: "上传结果", activate: "上传后激活这些 Local App Detector", import: "上传所选 Lua",
    hintInactive: "只上传、不激活：不影响现有业务。已存在同名应用的会跳过，不会覆盖。",
    hintActive: "激活后立即下发到所有受管 FTD，无需 Deploy；Snort 2 设备会重启 Snort。上传前会显示影响说明。已存在同名应用的会跳过。",
    dlgTitleA: "激活 Local App Detector 前请确认", dlgTitleI: "确认上传",
    dlgLeadA: (n) => `将上传 ${n} 个 Lua 并立即激活。激活后 FMC 会立即把 detector 下发到所有受管 FTD，不需要 Deploy。`,
    dlgLeadI: (n) => `将上传 ${n} 个 Lua，不激活。`,
    dlgItemsA: [
      "<b>Snort 3 设备</b>：不重启 Snort，不中断流量；激活过程中应用识别可能短暂中断（FMC 官方提示）。",
      "<b>Snort 2 设备</b>：每次激活/停用都会立即重启 Snort 进程，检测暂停；流量会被丢弃还是不检测直接放行取决于设备配置（接口模式、Fail-Open、Snort 重启时是否保持连接等）。",
      "<b>识别结果会变化</b>：原来被识别为 HTTPS / SSL 等的流量将被识别为新应用，可能开始或不再命中现有的访问控制、QoS、解密等规则。",
      "多域部署中，当前域及其子域下的设备都会受影响。激活大约需要 1–2 分钟，期间请勿关闭本页面。",
    ],
    dlgItemsI: [
      "只在 FMC 中创建应用和 Lua detector（状态为未激活），不重启 Snort，不影响现有业务。",
      "需要时可在 FMC 的 Policies → Advanced → Applications 中手动打开 State 开关激活，FMC 会给出同样的影响提示。",
    ],
    dlgMeasured: "实测（FMC 10.0.1 / FTD 10.0.0，Snort 3）：上传、激活、停用、删除 detector 时 Snort 进程 PID 均未变化，没有待 Deploy 的变更，新建连接、长连接和 ping 都没有丢失，激活后 detector 立即生效。",
    dlgAdvice: "建议：生产环境在维护窗口执行，先用测试设备或少量 Lua 验证。",
    dlgAck: "我已了解上述影响，确认继续", cancel: "取消", goA: "上传并激活", goI: "上传",
    log: "运行日志", loading: "加载中…", entries: (n, src) => `共 ${n} 个 Lua · 来源 ${src}`,
    page: (p, t) => `第 ${p} / ${t} 页`, selected: (n) => `已选 ${n} 个`, empty: "没有匹配的条目",
    testing: "正在登录 FMC…", testOk: (v) => `连接成功${v ? "，FMC 版本 " + v : "（未能读取 FMC 版本）"}`,
    needLogin: "请先填写 FMC 地址、用户名和密码", needSel: "请至少选择一个 Lua",
    running: "正在执行…", done: "完成", failed: "失败",
    st: { pending: "等待", importing: "上传中", imported: "已上传", skipped: "已跳过", error: "失败" },
    yes: "是", no: "否",
    quit: "退出程序", quitConfirm: "退出 NGFW Lua Importer？退出后本页面将无法使用，再次使用请重新打开程序。",
    quitDone: "NGFW Lua Importer 已退出，可以关闭此页面。", quitFail: "退出失败：",
  },
  en: {
    title: "NGFW Lua Importer", subtitle: "Pick OpenAppID Lua detectors from the shared library and upload them to Cisco FMC",
    aboutTitle: "Upload method & versions", progVer: "Program version", testedFmc: "Tested FMC version", connectedFmc: "Connected FMC version",
    method: "Upload method", library: "Shared library",
    methodText: "HTTPS automation of the FMC Web UI (the same internal endpoints used when you create a detector and upload Lua under Policies → Application Detectors: login.cgi, pjb.cgi, detectors.cgi). The public FMC REST API is not used because it cannot upload custom Lua.",
    compat: "For compatibility problems (for example a different FMC version rejects the upload) please email", compat2: "(the link pre-fills versions and errors)",
    fmcTitle: "FMC connection", host: "FMC address", user: "Username", pass: "Password", verify: "Verify HTTPS certificate", test: "Test connection", save: "Save",
    saved: "Saved FMC address, username and certificate option (the password is never written to disk)", needHost: "Enter the FMC address first",
    passHint: "The password is kept only in this page's memory and is never written to disk.",
    sessionHint: "FMC keeps one Web UI session per account: logging in from this tool logs out the same account in your browser, so a dedicated FMC account is recommended.",
    libTitle: "Shared Lua library", selAll: "Select all", search: "Search app / category / notes", refresh: "Refresh",
    cApp: "App", cVer: "Version", cCat: "Category / risk / relevance", cFmc: "Tested FMC", cNotes: "Notes",
    cStatus: "Status", cActive: "Active", cMsg: "Details", view: "View Lua",
    importTitle: "Upload results", activate: "Activate these Local App Detectors after upload", import: "Upload selected Lua",
    hintInactive: "Upload only, no activation: existing traffic is not affected. Apps that already exist are skipped, never overwritten.",
    hintActive: "Activation is pushed to all managed FTDs immediately, no deploy needed; Snort 2 devices restart Snort. An impact notice is shown before upload. Existing apps are skipped.",
    dlgTitleA: "Confirm before activating Local App Detectors", dlgTitleI: "Confirm upload",
    dlgLeadA: (n) => `${n} Lua detector(s) will be uploaded and activated. FMC pushes activated detectors to all managed FTDs immediately; no deploy is needed.`,
    dlgLeadI: (n) => `${n} Lua detector(s) will be uploaded without activation.`,
    dlgItemsA: [
      "<b>Snort 3 devices</b>: Snort is not restarted and traffic is not interrupted; application detection may be briefly interrupted while activating (FMC's own notice).",
      "<b>Snort 2 devices</b>: every activation/deactivation restarts the Snort process immediately and pauses inspection; whether traffic is dropped or passed uninspected depends on the device (interface mode, Fail-Open, preserve-connection on Snort restart, etc.).",
      "<b>Identification changes</b>: traffic previously identified as HTTPS / SSL etc. will be identified as the new app and may start or stop matching existing access control, QoS or decryption rules.",
      "In multidomain deployments, devices in the current domain and its subdomains are affected. Activation takes about 1–2 minutes; keep this page open.",
    ],
    dlgItemsI: [
      "Only creates the applications and Lua detectors on FMC (inactive). Snort is not restarted and traffic is not affected.",
      "Activate later in FMC under Policies → Advanced → Applications (State switch); FMC shows the same impact warning.",
    ],
    dlgMeasured: "Measured on FMC 10.0.1 / FTD 10.0.0 (Snort 3): upload, activate, deactivate and delete kept the Snort process PIDs unchanged, created no pending deployment, lost no new connections, keep-alive connections or pings, and the detector worked immediately after activation.",
    dlgAdvice: "Recommendation: run this in a maintenance window on production devices and validate with a test device or a few detectors first.",
    dlgAck: "I understand the impact and want to continue", cancel: "Cancel", goA: "Upload and activate", goI: "Upload",
    log: "Log", loading: "Loading…", entries: (n, src) => `${n} detectors · source ${src}`,
    page: (p, t) => `Page ${p} / ${t}`, selected: (n) => `${n} selected`, empty: "No matching entries",
    testing: "Logging in to FMC…", testOk: (v) => `Connected${v ? ", FMC version " + v : " (FMC version not readable)"}`,
    needLogin: "Enter FMC address, username and password first", needSel: "Select at least one detector",
    running: "Running…", done: "Done", failed: "Failed",
    st: { pending: "Pending", importing: "Uploading", imported: "Uploaded", skipped: "Skipped", error: "Error" },
    yes: "Yes", no: "No",
    quit: "Quit", quitConfirm: "Quit NGFW Lua Importer? This page stops working; open the program again to continue.",
    quitDone: "NGFW Lua Importer has quit. You can close this page.", quitFail: "Quit failed: ",
  },
};

const state = { lang: "zh", info: null, libInfo: null, testedVersion: null, job: null, entries: [], filtered: [], page: 1, selected: new Set(), fmcVersion: "", lastError: "", polling: null };
const t = (k) => I18N[state.lang][k];
const key = (e) => e.app_name + "@" + e.version;

async function api(path, opts = {}) {
  const res = await fetch(path, {
    ...opts,
    headers: { "X-Token": TOKEN, ...(opts.body ? { "Content-Type": "application/json" } : {}) },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

function el(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v);
  }
  for (const c of kids) n.append(c instanceof Node ? c : document.createTextNode(c ?? ""));
  return n;
}

function applyLang() {
  document.documentElement.lang = state.lang;
  for (const n of document.querySelectorAll("[data-i18n]")) n.textContent = t(n.dataset.i18n);
  for (const n of document.querySelectorAll("[data-i18n-ph]")) n.placeholder = t(n.dataset.i18nPh);
  $("langBtn").textContent = state.lang === "zh" ? "English" : "中文";
  renderRows();
  renderLibMeta();
  updateUploadHint();
  if (state.testedVersion !== null) setMsg("testMsg", t("testOk")(state.testedVersion), "ok");
  if (state.job) renderJob(state.job);
  updateMail();
}

function updateUploadHint() {
  const a = $("activate").checked;
  $("uploadHint").textContent = t(a ? "hintActive" : "hintInactive");
  $("uploadHint").classList.toggle("warnText", a);
}

// Resolves true only when the user confirms; activation also requires the acknowledgement checkbox.
function confirmUpload(n, activate) {
  const dlg = $("confirmDlg");
  dlg.classList.toggle("activate", activate);
  $("cfTitle").textContent = t(activate ? "dlgTitleA" : "dlgTitleI");
  $("cfLead").textContent = t(activate ? "dlgLeadA" : "dlgLeadI")(n);
  // Static, trusted i18n strings (contain <b> markup only).
  $("cfItems").innerHTML = t(activate ? "dlgItemsA" : "dlgItemsI").map((x) => `<li>${x}</li>`).join("");
  $("cfMeasured").textContent = t("dlgMeasured");
  $("cfAdvice").textContent = t("dlgAdvice");
  $("cfAdvice").classList.toggle("hidden", !activate);
  $("cfAckRow").classList.toggle("hidden", !activate);
  $("cfAck").checked = false;
  $("cfAckText").textContent = t("dlgAck");
  $("cfCancel").textContent = t("cancel");
  $("cfOk").textContent = t(activate ? "goA" : "goI");
  $("cfOk").className = activate ? "danger" : "";
  $("cfOk").disabled = activate;
  $("cfAck").onchange = () => { $("cfOk").disabled = !$("cfAck").checked; };
  return new Promise((resolve) => {
    const finish = (v) => { dlg.onclose = null; if (dlg.open) dlg.close(); resolve(v); };
    $("cfOk").onclick = () => finish(true);
    $("cfCancel").onclick = () => finish(false);
    dlg.onclose = () => finish(false);
    dlg.showModal();
  });
}

function renderLibMeta() {
  const l = state.libInfo;
  if (l) $("libMeta").textContent = t("entries")(l.n, l.src) + (l.commit ? " @" + l.commit.slice(0, 7) : "");
}

function updateMail() {
  if (!state.info) return;
  const i = state.info;
  $("mailLink").textContent = i.contact;
  const body = [
    `${i.name} ${i.version} (${i.os})`,
    `Tested FMC: ${i.tested_fmc}`,
    `Connected FMC: ${state.fmcVersion || "unknown"}`,
    `Error: ${state.lastError || "(describe the problem)"}`,
  ].join("\n");
  $("mailLink").href = `mailto:${i.contact}?subject=${encodeURIComponent(i.name + " compatibility issue")}&body=${encodeURIComponent(body)}`;
}

function login() {
  return { host: $("host").value.trim(), username: $("user").value.trim(), password: $("pass").value, verify_tls: $("verify").checked };
}

function filter() {
  const q = $("search").value.trim().toLowerCase();
  state.filtered = state.entries.filter((e) =>
    !q || [e.app_name, e.category, e.notes, e.review_note, e.nickname, (e.host_patterns || []).join(" ")].join(" ").toLowerCase().includes(q));
  const pages = Math.max(1, Math.ceil(state.filtered.length / PAGE_SIZE));
  state.page = Math.min(state.page, pages);
}

function renderRows() {
  const tb = $("rows");
  tb.replaceChildren();
  const pages = Math.max(1, Math.ceil(state.filtered.length / PAGE_SIZE));
  const slice = state.filtered.slice((state.page - 1) * PAGE_SIZE, state.page * PAGE_SIZE);
  if (!slice.length) tb.append(el("tr", {}, el("td", { colspan: "8", class: "empty" }, t("empty"))));
  for (const e of slice) {
    const cb = el("input", { type: "checkbox" });
    cb.checked = state.selected.has(key(e));
    cb.addEventListener("change", () => { cb.checked ? state.selected.add(key(e)) : state.selected.delete(key(e)); syncSelAll(); });
    const notes = [e.notes, e.review_note].filter(Boolean).join(" | ");
    tb.append(el("tr", {},
      el("td", {}, cb),
      el("td", {}, el("b", {}, e.app_name), el("div", { class: "meta" }, (e.host_patterns || []).slice(0, 3).join(", "))),
      el("td", {}, "v" + e.version),
      el("td", {}, `${e.category || "others"} / ${e.risk || 2} / ${e.business_relevance || 3}`),
      el("td", {}, e.fmc_version || "-"),
      el("td", { class: "notes", title: notes }, notes || "-"),
      el("td", { class: "mono", title: e.sha256 }, (e.sha256 || "").slice(0, 12)),
      el("td", {}, el("button", { class: "ghost small", onclick: () => viewLua(e) }, t("view"))),
    ));
  }
  $("pageInfo").textContent = t("page")(state.page, pages);
  $("prevBtn").disabled = state.page <= 1;
  $("nextBtn").disabled = state.page >= pages;
  syncSelAll();
}

function syncSelAll() {
  const all = state.filtered.length > 0 && state.filtered.every((e) => state.selected.has(key(e)));
  $("selAll").checked = all;
  $("selCount").textContent = t("selected")(state.selected.size);
}

async function loadLibrary(refresh) {
  $("libMeta").textContent = t("loading");
  try {
    const snap = await api("/api/library" + (refresh ? "?refresh=1" : ""));
    state.entries = (snap.entries || []).sort((a, b) => a.app_name.localeCompare(b.app_name) || b.version - a.version);
    const valid = new Set(state.entries.map(key));
    for (const k of [...state.selected]) if (!valid.has(k)) state.selected.delete(k);
    state.libInfo = { n: state.entries.length, src: snap.source, commit: snap.commit };
    renderLibMeta();
  } catch (err) {
    state.libInfo = null;
    $("libMeta").textContent = err.message;
    state.lastError = err.message;
    updateMail();
  }
  filter();
  renderRows();
}

async function viewLua(e) {
  $("luaTitle").textContent = `${e.app_name} v${e.version}`;
  $("luaBody").textContent = t("loading");
  $("luaDlg").showModal();
  try {
    const r = await api(`/api/lua?app_name=${encodeURIComponent(e.app_name)}&version=${e.version}`);
    $("luaBody").textContent = r.lua;
  } catch (err) {
    $("luaBody").textContent = err.message;
  }
}

function setMsg(id, text, kind) {
  $(id).textContent = text;
  $(id).className = "msg " + (kind || "");
}

async function testFMC() {
  const l = login();
  if (!l.host || !l.username || !l.password) return setMsg("testMsg", t("needLogin"), "err");
  state.testedVersion = null;
  setMsg("testMsg", t("testing"));
  $("testBtn").disabled = true;
  try {
    const r = await api("/api/fmc/test", { method: "POST", body: JSON.stringify(l) });
    state.fmcVersion = r.fmc_version || "";
    state.testedVersion = state.fmcVersion;
    $("iFmc").textContent = state.fmcVersion || "-";
    setMsg("testMsg", t("testOk")(state.fmcVersion), "ok");
  } catch (err) {
    state.lastError = err.message;
    setMsg("testMsg", err.message, "err");
  } finally {
    $("testBtn").disabled = false;
    updateMail();
  }
}

async function saveFMC() {
  const l = login();
  if (!l.host) return setMsg("testMsg", t("needHost"), "err");
  $("saveBtn").disabled = true;
  try {
    await api("/api/settings", { method: "POST", body: JSON.stringify({ host: l.host, username: l.username, verify_tls: l.verify_tls }) });
    setMsg("testMsg", t("saved"), "ok");
  } catch (err) {
    setMsg("testMsg", err.message, "err");
  } finally {
    $("saveBtn").disabled = false;
  }
}

async function startImport() {
  const l = login();
  if (!l.host || !l.username || !l.password) return alert(t("needLogin"));
  const items = state.entries.filter((e) => state.selected.has(key(e))).map((e) => ({ app_name: e.app_name, version: e.version }));
  if (!items.length) return alert(t("needSel"));
  const activate = $("activate").checked;
  if (!(await confirmUpload(items.length, activate))) return;
  $("importBtn").disabled = true;
  try {
    renderJob(await api("/api/import", { method: "POST", body: JSON.stringify({ fmc: l, items, activate }) }));
    poll();
  } catch (err) {
    state.lastError = err.message;
    updateMail();
    alert(err.message);
    $("importBtn").disabled = false;
  }
}

function poll() {
  clearTimeout(state.polling);
  state.polling = setTimeout(async () => {
    try {
      const r = await api("/api/job");
      if (r.job) renderJob(r.job);
      if (r.job && r.job.state === "running") return poll();
    } catch (err) { return poll(); }
    $("importBtn").disabled = false;
    $("testBtn").disabled = false;
  }, 1500);
}

function renderJob(job) {
  state.job = job;
  $("jobBox").classList.remove("hidden");
  const busy = job.state === "running";
  $("importBtn").disabled = busy;
  $("testBtn").disabled = busy;
  if (job.fmc_version) { state.fmcVersion = job.fmc_version; $("iFmc").textContent = job.fmc_version; }
  const label = job.state === "running" ? t("running") : job.state === "done" ? t("done") : t("failed");
  setMsg("jobState", `${label}${job.error ? ": " + job.error : ""}`, job.state === "failed" ? "err" : job.state === "done" ? "ok" : "");
  const errs = job.results.filter((r) => r.status === "error").map((r) => `${r.app_name}: ${r.message}`);
  if (job.error) errs.unshift(job.error);
  if (errs.length) { state.lastError = errs.join("; ").slice(0, 600); updateMail(); }
  $("jobRows").replaceChildren(...job.results.map((r) => el("tr", { class: "st-" + r.status },
    el("td", {}, r.app_name), el("td", {}, "v" + r.version),
    el("td", {}, t("st")[r.status] || r.status),
    el("td", {}, r.active === undefined || r.active === null ? "-" : r.active ? t("yes") : t("no")),
    el("td", {}, r.message || ""))));
  $("jobLog").textContent = (job.log || []).join("\n");
}

async function quitApp() {
  if (!confirm(t("quitConfirm"))) return;
  try {
    await api("/api/quit", { method: "POST" });
  } catch (err) {
    alert(t("quitFail") + err.message);
    return;
  }
  clearTimeout(state.polling);
  document.body.replaceChildren(el("main", {}, el("section", { class: "card quit-done" }, el("p", {}, t("quitDone")))));
}

async function init() {
  $("langBtn").addEventListener("click", async () => {
    state.lang = state.lang === "zh" ? "en" : "zh";
    applyLang();
    api("/api/settings", { method: "POST", body: JSON.stringify({ lang: state.lang }) }).catch(() => {});
  });
  $("quitBtn").addEventListener("click", quitApp);
  $("saveBtn").addEventListener("click", saveFMC);
  $("testBtn").addEventListener("click", testFMC);
  $("refreshBtn").addEventListener("click", () => loadLibrary(true));
  $("search").addEventListener("input", () => { state.page = 1; filter(); renderRows(); });
  $("selAll").addEventListener("change", () => {
    for (const e of state.filtered) $("selAll").checked ? state.selected.add(key(e)) : state.selected.delete(key(e));
    renderRows();
  });
  $("prevBtn").addEventListener("click", () => { state.page--; renderRows(); });
  $("nextBtn").addEventListener("click", () => { state.page++; renderRows(); });
  $("importBtn").addEventListener("click", startImport);
  $("activate").addEventListener("change", updateUploadHint);
  $("luaClose").addEventListener("click", () => $("luaDlg").close());

  try {
    const i = await api("/api/info");
    state.info = i;
    state.lang = i.settings.lang === "en" ? "en" : "zh";
    $("iVersion").textContent = i.version;
    $("iTested").textContent = i.tested_fmc;
    $("iLib").textContent = i.library;
    $("iLib").href = i.library;
    $("host").value = i.settings.host || "";
    $("user").value = i.settings.username || "admin";
    $("verify").checked = !!i.settings.verify_tls;
  } catch (err) {
    state.lastError = err.message;
  }
  applyLang();
  loadLibrary(false);
  try {
    const r = await api("/api/job");
    if (r.job) { renderJob(r.job); if (r.job.state === "running") poll(); }
  } catch (_) {}
}

init();
