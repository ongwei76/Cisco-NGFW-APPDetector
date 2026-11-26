# AGENTS.md — ai_workflow

AI agents working in this directory: read [AI_WORKFLOW.md](./AI_WORKFLOW.md) (English) or [AI_WORKFLOW.zh-CN.md](./AI_WORKFLOW.zh-CN.md) (Chinese) first — same content, then the latest handoff under `runs/`.

Hard rules:
- Before logging into, sending traffic through, deploying to, or reconfiguring the lab (Windows VM <VM_IP>, FMC <FMC_IP>, FTD, ESXi), claim it: `python3 ~/.copilot/lab/labctl.py claim fmc ftd win-test-host --holder ... --session ... --purpose ...`; release when done. On conflict, stop and ask the user.
- Confirm market/app list, verification scope and publishing with the user before starting a round.
- Credentials live only in `config/lab.env` (gitignored) and are read via `pipeline/labcfg.py`. Never write them into code, docs, handoffs, decks or the share library.
- Never upload PCAPs. Do not git commit unless asked. Publishing to GitHub needs the user's OK.
- Kill processes by PID only. Do not touch the user's Lua Importer on :8790.
- A detector counts as verified only with a live FMC Connection Event (`web_app = <name>`) after re-running the app. Record failures with a reason; never fabricate evidence.
- Decks/posters: delegate to the "deck generator" agent.
- At the end of a round, write a handoff in `runs/<yyyy-mm>_<market>/` and update both AI_WORKFLOW.md and AI_WORKFLOW.zh-CN.md with new pitfalls/tools.
