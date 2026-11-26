# ai_workflow — AI-driven NGFW App Detector workflow

**English** | [简体中文](./README.zh-CN.md)

> Public copy: this repository contains the docs and decks only. The `pipeline/`, `apk_tools/`, `config/`, `runs/` and `history/` folders mentioned here (scripts, lists, evidence, handoffs) are kept in the maintainer's internal copy; IPs and other environment details are replaced with placeholders.

Everything for the verified "AI drives NGFW App Detector" workflow: docs, scripts, overview decks, past runs, and the output of every future round.

| Path | Contents |
|---|---|
| [AI_WORKFLOW.md](./AI_WORKFLOW.md) | **Main doc** ([中文](./AI_WORKFLOW.zh-CN.md)): idea, topology, standard flow, Lua rules, verification standard, human checkpoints, hard rules, pitfalls, tools, past rounds |
| [AGENTS.md](./AGENTS.md) | Short rules for AI assistants |
| [presentation/](./presentation/) | Overview decks of this workflow (English / Chinese) and the generator script; [verification_decks/](./presentation/verification_decks/) holds the evidence decks of every verification round |
| `pipeline/` | Mac-side scripts that drive the VM, emulator and FMC; `hk/` is a complete round template, `new_market.sh` starts a new round |
| `apk_tools/` | APK download, screenshots, evidence, publishing, cleanup (`MARKET=<m>`) |
| `config/` | `lab.example.env`; real credentials go in `lab.env` (gitignored) |
| `runs/` | Per-round handoff, evidence and decks; a new round goes in `runs/<yyyy-mm>_<market>/` |
| `history/` | Lessons from earlier phases (Chinese), original runbook |
| `work/` | Scratch files (APKs, screenshots), emptied after each round (gitignored) |

Quick start:

```bash
/usr/bin/python3 -m venv --system-site-packages .venv-lab && .venv-lab/bin/pip install -r requirements-lab.txt
cp config/lab.example.env config/lab.env    # fill in credentials
bash pipeline/new_market.sh <market>        # new round
```

Then follow section 4 of [AI_WORKFLOW.md](./AI_WORKFLOW.md).
