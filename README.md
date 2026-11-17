# Cisco NGFW APP Detector

为 Cisco Secure Firewall（FMC / FTD）自动生成、验证并共享 OpenAppID 自定义 Lua 应用检测器（Local App Detector），重点覆盖 FMC 内置应用库尚未识别的国内应用。

Automatically generate, verify and share OpenAppID custom Lua application detectors for Cisco Secure Firewall (FMC / FTD), focusing on Chinese apps that the FMC built-in application library does not yet identify.

## 目录 / Repository layout

| 目录 Directory | 内容 Contents |
|------|------|
| [`library/`](library/) | 共享 Lua 库：每个应用一个目录，`index.json` 为索引（含 SHA256、分类、验证 FMC 版本）。所有条目都在 FMC/FTD 上实际验证过。<br>Shared Lua library, one folder per app; `index.json` lists SHA256, category and tested FMC version. Every entry was verified on FMC/FTD. |
| [`NGFW_appdetector/`](NGFW_appdetector/) | **NGFW App Detector**（Python，Windows）：在终端上运行目标应用，采集并关联流量，自动生成 Lua，导入 FMC 验证，并向共享库提交。<br>Runs the target app on a Windows endpoint, captures and correlates traffic, generates Lua, imports it into FMC for verification and submits it to the library. |
| [`NGFW_lua_importer/`](NGFW_lua_importer/) | **NGFW Lua Importer**（Go，Windows/macOS/Linux 单文件）：连接 FMC，浏览共享库，勾选后一键上传到 Local App Detector，可选激活。<br>Single-binary tool that connects to FMC, browses the library and uploads selected detectors, optionally activating them. |
| [`presentation/`](presentation/) | 方案介绍 PPT（中文 / 英文）。<br>Solution overview decks (Chinese / English). |

## 下载 / Downloads

编译好的程序在 [GitHub Releases](https://github.com/ongwei76/Cisco-NGFW-APPDetector/releases)：

| 程序 Program | Release | 文件 Files |
|------|------|------|
| NGFW Lua Importer 1.0.0 | [lua-importer-v1.0.0](https://github.com/ongwei76/Cisco-NGFW-APPDetector/releases/tag/lua-importer-v1.0.0) | Windows x64 `.exe`、macOS arm64 / x64、Linux x64、`SHA256SUMS.txt` |
| NGFW App Detector 1.2.0 | [app-detector-v1.2.0](https://github.com/ongwei76/Cisco-NGFW-APPDetector/releases/tag/app-detector-v1.2.0) | Windows 便携包 portable ZIP + `.sha256.txt` |

## 怎么选 / Which tool do I need?

- **只想用现成的 detector**：下载 NGFW Lua Importer，选择共享库中的应用上传到 FMC 即可，无需抓包或写 Lua。详见 [NGFW_lua_importer/README.md](NGFW_lua_importer/README.md)。
- **要为新应用生成 detector**：使用 NGFW App Detector，详见 [NGFW_appdetector/README.md](NGFW_appdetector/README.md)。
- **Just use verified detectors:** download NGFW Lua Importer and upload library entries to FMC — no capture or Lua writing needed. See [NGFW_lua_importer/README.md](NGFW_lua_importer/README.md).
- **Build detectors for new apps:** use NGFW App Detector. See [NGFW_appdetector/README.md](NGFW_appdetector/README.md).

## 方案介绍 / Overview decks

- [中文：NGFW_App_Detector_解决方案介绍_中文.pptx](presentation/NGFW_App_Detector_解决方案介绍_中文.pptx)
- [English: NGFW_App_Detector_Solution_Overview_EN.pptx](presentation/NGFW_App_Detector_Solution_Overview_EN.pptx)

## 兼容性 / Compatibility

已验证 FMC 10.0.1 / FTD 10.0.0（Snort 3）。其他版本遇到问题请发邮件至 / Tested on FMC 10.0.1 / FTD 10.0.0 (Snort 3). For problems on other versions, email **[yongwli@cisco.com](mailto:yongwli@cisco.com)**.
