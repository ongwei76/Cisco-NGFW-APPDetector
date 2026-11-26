# ai_workflow — AI 驱动 NGFW App Detector 的流程、工具和记录

> 公开版说明：本仓库只包含文档和 PPT。文中提到的 `pipeline/`、`apk_tools/`、`config/`、`runs/`、`history/`（脚本、清单、证据和交接记录）保存在维护者的内部副本中；IP 等环境信息已替换为占位符。

这里集中存放“用 AI 驱动 NGFW App Detector”这套已验证流程的全部内容：文档、脚本、介绍 PPT、历次记录，以及以后每一轮的产出。

| 路径 | 内容 |
|---|---|
| [AI_WORKFLOW.md](./AI_WORKFLOW.md) | **主文档**：思路、拓扑、标准流程、Lua 规则、验证标准、人工节点、硬规则、已知坑、工具清单、历次记录 |
| [AGENTS.md](./AGENTS.md) | 给 AI 助手的简短规则（自动加载） |
| [presentation/](./presentation/) | 介绍这套思路的 PPT（中文 / English）及生成脚本 |
| `pipeline/` | Mac 侧驱动 VM、模拟器、FMC 的脚本；`hk/` 是一轮任务的完整模板，`new_market.sh` 新建一轮 |
| `apk_tools/` | APK 下载、截图、证据整理、发布、清理（`MARKET=<m>`） |
| `config/` | `lab.example.env`；实际凭据放 `lab.env`（gitignored） |
| `runs/` | 每一轮的交接、证据、PPT；新一轮放 `runs/<yyyy-mm>_<market>/` |
| `history/` | 早期阶段经验摘要、原 RUNBOOK |
| `work/` | 临时文件（APK、截图），每轮结束清空（gitignored） |

快速开始：

```bash
/usr/bin/python3 -m venv --system-site-packages .venv-lab && .venv-lab/bin/pip install -r requirements-lab.txt
cp config/lab.example.env config/lab.env    # 填凭据
bash pipeline/new_market.sh <market>        # 新一轮
```

然后按 [AI_WORKFLOW.md](./AI_WORKFLOW.md) 第 4 节执行。
