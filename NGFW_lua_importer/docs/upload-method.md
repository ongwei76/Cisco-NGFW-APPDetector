# 上传方式（Upload method）

FMC 的公开 REST API 没有上传自定义 Lua 应用检测器（custom application detector）的接口，所以本程序复现 FMC 网页界面在 **Policies → Application Detectors** 页面上的调用。下面的顺序在 **FMC 10.0.1 (build 1)** 上验证通过。

所有请求都是对 FMC 管理地址的 HTTPS 请求，不经过代理，使用同一个 `CGISESSID` 会话 Cookie。

## 1. 登录

| 步骤 | 请求 | 说明 |
|------|------|------|
| 1 | `GET /ui/login` | 打开登录页 |
| 2 | `POST /login.cgi`（表单 `username`、`password`） | 成功时返回 `CGISESSID` Cookie |
| 3 | `GET /ddd/` | 从页面中读取 `sf_action_id`（每个会话的 CSRF 令牌）以及 FMC 版本（`"fmcBuild":"10.0.1-1"`） |

> FMC 版本直接从网页读取，**不调用 REST API 的 `generatetoken`**：实测同一账号申请 REST 令牌会让当前网页会话失效，导致后续调用返回空数据。

## 2. pjb.cgi 调用格式

`POST /pjb.cgi`，表单字段：

```
function       = SF::Cache::RNADetector::<函数名>
parameters     = <JSON 数组>
get_all_errors = 1
sf_action_id   = <第 1 步得到的令牌>
ss             = DetectorList 或 DetectorEditor
```

返回 JSON：`{"data": ..., "error": ...}`。`data` 为空表示会话已被退出（例如同一账号在别处登录），程序会对只读调用自动重新登录一次。

## 3. 上传一个 Lua

| 步骤 | 函数 / 请求 | 主要参数 |
|------|-------------|----------|
| 1 | `getFilterList` `[]` | 取得已有应用名（判断是否已存在）和分类列表（分类名 → tagId） |
| 2 | `saveApp` | `appName`、`appId:-1`、`risk_index`、`productivity_index`、`appDescription`、`categories:[{tagId, tagType:"category", tagName}]`，返回新 `appId` |
| 3 | `setDetector` `["new", null, {...}]` | `name`、`appId`、`protocol:"custom"`、`active:0`、`lua:0`，返回 detector `uuid` |
| 4 | `initDetectorEditorForAllApps` `[uuid]` | 打开 detector 编辑器（`ss=DetectorEditor`） |
| 5 | `POST /RNADetector/detectors.cgi`（multipart） | `sf_action_id`、`detector_uuid`、文件字段 `lua_upload`；返回 `FILENAME=...!!SUCCESS=...` 或 `!!ERROR=<原因>` |
| 6 | `setDetector` `["save", uuid, {...}]` | `lua:1`、`subtype:5`、`active:0`；返回保存后的 Lua，程序会与上传内容比对（忽略换行和非 ASCII 字符差异） |

第 3–6 步任一步失败，都会调用 `deleteDetectors [[uuid]]` 回滚，FMC 会同时删除第 2 步创建的应用。

## 4. 激活（可选）

| 步骤 | 函数 | 说明 |
|------|------|------|
| 1 | `activateDetectors` `[[uuid, ...]]` | FMC 常常要 1–3 分钟才返回；程序最多等 3 分钟，超时后改为轮询 |
| 2 | `getDetectorList` `[[], {"column":null,"ascending":0}, offset, 2000]` | 分页读取全部 detector（约 1 万条），检查 `data.active == 1`；每 15 秒一次，最多 6 分钟 |

只会激活 `data.editable == 1` 的自定义 detector，Cisco 内置 detector 不会被改动。

激活由 FMC 直接下发到所有受管设备，**不需要 Deploy**（实测 FMC 10.0.1：激活后没有待 Deploy 的变更，detector 立即生效）。按 FMC 官方提示，Snort 2 设备在激活/停用时会立即重启 Snort；Snort 3 设备不重启、不中断流量，只是应用识别可能短暂中断。本程序不会自动 Deploy。

## 5. 共享库读取

- 先通过 `https://github.com/<owner>/<repo>.git/info/refs?service=git-upload-pack` 读取分支最新 commit，然后从该 commit 读取 `library/index.json` 和 Lua 文件，保证索引和 Lua 来自同一个版本；
- 主地址 `raw.githubusercontent.com`，失败时使用 `cdn.jsdelivr.net` 镜像；
- 每个 Lua 必须与索引中的 SHA256 一致才会上传。
