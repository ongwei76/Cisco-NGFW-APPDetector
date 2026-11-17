# 兼容性说明（Compatibility）

## 已验证环境

| 项目 | 版本 |
|------|------|
| FMC | Cisco Secure Firewall Management Center for VMware **10.0.1 (build 1)** |
| 本程序 | 1.0.0 |
| 运行平台 | macOS 27（Apple 芯片）、Windows 10 Enterprise x64（实测） |

在 10.0.1 上验证过的流程：登录 → 读取版本 → 上传（Inactive）→ 上传并激活 → 已存在应用跳过 → 已存在的 Inactive 自定义 detector 激活 → 上传失败自动回滚（模拟 FMC 测试）。

其他 FMC 版本（例如 7.x）**理论上**使用相同的网页接口，但没有实测。因为本程序使用的是 FMC 网页界面的内部接口，而不是公开 REST API，所以 Cisco 升级 FMC 后接口可能变化。

## 常见提示

| 提示 | 可能原因 / 处理 |
|------|----------------|
| `cannot reach FMC` | 地址错误、网络不通，或勾选了“校验 HTTPS 证书”但 FMC 是自签名证书 |
| `FMC login failed ... check the username and password` | 用户名/密码错误，或账号被锁定 |
| `FMC Web UI session could not be established ... may not be compatible` | 登录成功但 `/ddd/` 页面中找不到会话令牌，可能是 FMC 版本差异 → **请反馈** |
| `FMC returned no data; the FMC Web UI session was logged out` | 同一账号在其他地方（浏览器、另一个工具）登录了 FMC。FMC 每个账号只保留一个网页会话，请改用专用账号后重试 |
| `getFilterList: unexpected FMC response` / `getDetectorList: unexpected FMC response` | FMC 返回格式不同 → **请反馈** |
| `Lua upload rejected by FMC: <原因>` | FMC 拒绝了 Lua（语法或 API 不支持）。如果同一 Lua 在 10.0.1 正常，说明版本差异 → **请反馈** |
| `FMC saved the detector without the uploaded Lua` | FMC 保存后的 Lua 与上传内容不一致，已自动回滚 → **请反馈** |
| `FMC did not report all detectors as active within 6 minutes` | FMC 繁忙；稍后在 FMC 页面确认，或再次运行并勾选“激活” |
| `SHA256 mismatch with the library index; refused` | 下载内容与共享库索引不一致（网络劫持或镜像缓存过期），稍后点“刷新”重试 |
| `category "xxx" not found on this FMC, used "others"` | 该 FMC 没有此分类名，已用 others 代替，可在 FMC 中手工修改 |

## 反馈方式

请发送邮件至 **[yongwli@cisco.com](mailto:yongwli@cisco.com)**，邮件中请包含：

1. 本程序版本和操作系统（`ngfw-lua-importer -version` 或界面上“程序版本”）；
2. FMC 版本（界面上“当前 FMC 版本”，或 FMC 的 Help → About）；
3. 出错的应用名和版本；
4. 界面上的错误提示和“运行日志”全文。

界面上的邮件链接会自动填好第 1、2 项和最近一次错误。请不要在邮件中发送 FMC 密码。
