# ai_workflow — AI 驱动 NGFW App Detector / AI-driven NGFW App Detector workflow

> 公开版说明：本仓库只包含文档和 PPT。文中提到的 `pipeline/`、`apk_tools/`、`config/`、`runs/`、`history/`（脚本、清单、证据和交接记录）保存在维护者的内部副本中；IP 等环境信息已替换为占位符。

> Public copy: this repository contains the docs and decks only. The `pipeline/`, `apk_tools/`, `config/`, `runs/` and `history/` folders mentioned here (scripts, lists, evidence, handoffs) are kept in the maintainer's internal copy; IPs and other environment details are replaced with placeholders.

这里集中存放“用 AI 驱动 NGFW App Detector”这套已验证流程的全部内容：文档、脚本、介绍 PPT、历次记录，以及以后每一轮的产出。
Everything for the verified "AI drives NGFW App Detector" workflow: docs, scripts, overview decks, past runs, and the output of every future round.

| 路径 Path | 内容 Contents |
|---|---|
| [AI_WORKFLOW.md](./AI_WORKFLOW.md) · [AI_WORKFLOW_EN.md](./AI_WORKFLOW_EN.md) | **主文档**（中文 / English，内容一致）：思路、拓扑、标准流程、Lua 规则、验证标准、人工节点、硬规则、已知坑、工具清单、历次记录<br>**Main doc** (same content): idea, topology, standard flow, Lua rules, verification, human checkpoints, hard rules, pitfalls, tools, past rounds |
| [AGENTS.md](./AGENTS.md) | 给 AI 助手的简短规则 / Short rules for AI assistants |
| [presentation/](./presentation/) | 介绍这套思路的 PPT（中文 / English）及生成脚本 / Overview decks and generator script |
| `pipeline/` | Mac 侧驱动 VM、模拟器、FMC 的脚本；`hk/` 是一轮任务的完整模板，`new_market.sh` 新建一轮<br>Scripts driving the VM, emulator and FMC; `hk/` is a complete round template, `new_market.sh` starts a new round |
| `apk_tools/` | APK 下载、截图、证据整理、发布、清理（`MARKET=<m>`）/ APK download, screenshots, evidence, publishing, cleanup |
| `config/` | `lab.example.env`；实际凭据放 `lab.env`（gitignored）/ real credentials go in `lab.env` (gitignored) |
| `runs/` | 每一轮的交接、证据、PPT；新一轮放 `runs/<yyyy-mm>_<market>/` / Per-round handoff, evidence and decks |
| `history/` | 早期阶段经验摘要、原 RUNBOOK / Lessons from earlier phases, original runbook |
| `work/` | 临时文件（APK、截图），每轮结束清空（gitignored）/ Scratch files, emptied after each round |

快速开始 / Quick start:

```bash
/usr/bin/python3 -m venv --system-site-packages .venv-lab && .venv-lab/bin/pip install -r requirements-lab.txt
cp config/lab.example.env config/lab.env    # 填凭据 / fill in credentials
bash pipeline/new_market.sh <market>        # 新一轮 / new round
```

然后按主文档第 4 节执行。/ Then follow section 4 of the main doc.
