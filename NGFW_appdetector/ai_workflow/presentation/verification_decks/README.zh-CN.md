# 验证证据 PPT

[English](README.md) | **简体中文**

历次 AI 驱动验证的证据 PPT，每轮一份。每份按 App 列出客户端截图、FMC 中的 Detector、FMC 连接事件里出现的新 `Web App` 名，以及无法验证的 App 和原因。PDF 用于在线查看，PPTX 用于编辑。

各 PPT 保持制作时的语言，目前没有其他语言版本。GitHub 上公开的副本已对文字、备注和截图中的 IP 地址打码。

| 轮次 | 日期 | 语言 | 页数 | 结果 | 文件 |
|---|---|---|---|---|---|
| 券商 PC 客户端 Top5 | 2026-11-11 | 中文 | 8 | 中信、国泰海通、华泰、广发、银河 5 个新 Lua 全部命中 | [PDF](券商App验证证据.pdf) · [PPTX](券商App验证证据.pptx) |
| 中国视频 App Top10 | 2026-11-12 | 中文 | 8 | 6 个内置；抖音、西瓜、咪咕、央视频 4 个新 Lua 命中 | [PDF](视频App验证证据.pdf) · [PPTX](视频App验证证据.pptx) |
| 中国安卓 Top20 | 2026-11-13 | 中文 | 8 | 14 内置；拼多多、高德、滴滴、饿了么 4 个新 Lua | [PDF](安卓App验证证据.pdf) · [PPTX](安卓App验证证据.pptx) |
| 中国安卓 Top50 | 2026-11-15 | 中文 | 19 | 26 内置、6 库中已有、15 个新生成（14 个 Detector）、3 个反模拟器 | [PDF](安卓Top50App验证证据.pdf) · [PPTX](安卓Top50App验证证据.pptx) |
| 中国安卓 51–100 | 2026-11-15 | 中文 | 23 | 14 内置、1 库中已有、18 个新 Lua、17 个失败 | [PDF](安卓Top100App验证证据.pdf) · [PPTX](安卓Top100App验证证据.pptx) |
| 安卓手游 Top30 | 2026-11-16 | 中文 | 18 | 13 个新 Lua、17 个失败 | [PDF](安卓Top30手游验证证据.pdf) · [PPTX](安卓Top30手游验证证据.pptx) |
| 香港市场 Top50 | 2026-11-17 | 英文 | 36 | 18 新 Lua、15 内置、2 识别为母应用、1 不做、14 失败 | [PDF](HK_Top50_Android_Verification_EN.pdf) · [PPTX](HK_Top50_Android_Verification_EN.pptx) |

新一轮：把 PPT（及 PDF）放到这里，命名 `<Market>_Top<N>_<Platform>_Verification_<LANG>.pptx`，并在本表和英文索引各加一行。

原件和生成脚本在项目的 `presentation/`（`generate_*_ppt.py`）和 `runs/<yyyy-mm>_<market>/` 中。
