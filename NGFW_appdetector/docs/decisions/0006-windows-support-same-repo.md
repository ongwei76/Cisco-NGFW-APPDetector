# ADR-0006: Windows support lives in this repo, not a new project
Status: Accepted
Date: 2026-07-22

## Context
Office machines are mostly Windows; the tool currently targets macOS only.
We need to decide whether Windows support is a new project or an extension
of `ngfw-appdetector`.

Auditing the codebase: `ngfw_collector` (FMC scrape), `correlator`,
`lua_generator`, `web/`, `cli.py`, and `config.py` are pure Python using
cross-platform libraries (`requests`, `fastapi`, `jinja2`, `typer`, `rich`,
`pydantic`) — none of it is OS-specific. The only OS-coupled code is
`flow_monitor/proc_tracker.py`'s socket→PID mapping:

- Primary path, `psutil.net_connections(kind="inet")` + `psutil.Process(pid)`,
  is already cross-platform (Linux/macOS/Windows) per psutil's own docs.
- The only Unix-only piece is the `lsof -i -nP` fallback, gated by
  `shutil.which("lsof") is not None`. On Windows this is `None`, so the
  fallback silently no-ops — it does not error.

So today's code already *runs* the psutil path unmodified on Windows; what's
missing is validation on real Windows hardware and (optionally) a
Windows-native fallback to replace the `lsof` one.

## Decision
Keep one repo. Treat `flow_monitor` as the only platform-sensitive module:
- Primary attribution (`psutil.net_connections`) stays shared across OSes —
  no per-OS subclassing needed unless testing proves otherwise.
- `lsof` fallback stays macOS/Linux-only, auto-disabled on Windows via the
  existing `shutil.which` check.
- A Windows-native fallback (e.g. parsing `netstat -ano`) is deferred until
  the psutil-only path is proven insufficient on real Windows hardware —
  YAGNI until a VM test says otherwise.
- No macOS Network Extension equivalent (e.g. WFP callout driver) is planned;
  out of scope, would need separate Windows dev/signing investment.

## Consequences
+ Zero duplicated maintenance of FMC scraping, correlation, LUA generation,
  or the web UI across two codebases.
+ `flow_monitor` is already the correct seam — no refactor needed to "make
  it pluggable", it already degrades gracefully per-OS.
- `~/.config/ngfw-appdetector/config.yaml` auto-discovery path (ADR-0005)
  resolves to `C:\Users\<user>\.config\...` on Windows — works, but isn't
  the Windows-idiomatic location (`%APPDATA%`). Left as-is until it's an
  actual pain point.
- Real validation (permissions needed for `psutil.net_connections` as a
  non-admin user, PyInstaller/pipx behavior, etc.) still requires testing on
  an actual Windows VM — not yet done as of this ADR.

## Alternatives considered
- **New sibling project for Windows**: rejected — would fork ~80% of the
  codebase (FMC collector, correlator, LUA generator, web UI) that has no
  OS dependency at all.
- **Full backend-interface abstraction (strategy pattern) for `flow_monitor`
  now**: rejected for now — premature, since the existing psutil path
  already works unmodified on Windows. Revisit if/when a Windows-native
  fallback (netstat) is actually needed.
