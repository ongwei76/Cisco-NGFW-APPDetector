# AGENTS.md

Project-level instructions for AI coding agents (Copilot, Cursor, Claude Code,
Codex, etc.). Keep this file short, specific, and current — out-of-date
instructions hurt more than missing ones.

## What this project is

`ngfw-appdetector` — a tool that auto-generates **Cisco NGFW LUA App Detectors**
by correlating local macOS socket-table flows with Cisco FMC connection events,
then rendering Jinja2 LUA templates.

Pipeline:

```
flow_monitor (socket table, PID/proc) ──┐
                                        ├─► correlator (5-tuple + time window)
ngfw_collector (FMC connection events) ─┘            │
                                                     ▼
                                            lua_generator (Jinja2)
                                                     │
                                                     ▼
                                              *.lua → import to FMC
```

A `web/` FastAPI + HTMX GUI wraps the same pipeline plus an FMC event search.

## Tech stack & conventions

- **Python**: `>=3.9`. The package lives under `src/ngfw_appdetector/` (src
  layout). Always import with the full package path.
- **Models**: Pydantic v2 (`BaseModel`, `Field`). All cross-module data
  structures live in `src/ngfw_appdetector/models.py`.
- **Config**: `pydantic-settings`. Loader is `config.py::load_config`. YAML
  file + env override prefix `NGFW_APPDETECTOR_` with nested delimiter `__`
  (e.g. `NGFW_APPDETECTOR_FMC__PASSWORD`).
- **CLI**: Typer. All commands live in `cli.py` and are exposed via the
  console_script `ngfw-appdetector` (defined in `pyproject.toml`).
- **Web**: FastAPI + Jinja2 + HTMX + vanilla JS. Single template
  `web/templates/index.html`, single stylesheet `web/static/app.css`. No build
  step.
- **Logging**: stdlib `logging` plus `rich` for terminal tables. Don't add
  loguru / structlog.
- **Tests**: `pytest`. Lives under `tests/`. Run `pytest -q`.
- **Lint**: `ruff`. No black; ruff handles formatting too.

### Style rules

- No docstrings/comments on code you didn't change. New code: comment only when
  the *why* is non-obvious (hidden constraint, workaround, subtle invariant).
  Never narrate what the code already says.
- No backwards-compat shims or feature flags unless explicitly requested —
  change the call sites instead.
- Don't add validation/error handling for situations that can't happen.
  Validate only at boundaries (user input, external APIs).
- Pydantic models: prefer `Optional[X] = None` over `X | None` (Py 3.9 target).
- Keep `web/templates/index.html` and `web/static/app.css` the single source
  of UI truth. Don't introduce a JS framework.

## How to run

All commands assume you're in the repo root with `.venv` activated.

```bash
# Install (editable, with web + dev extras)
pip install -e ".[dev,web]"

# CLI smoke
ngfw-appdetector version

# End-to-end offline demo (no FMC, no sudo)
ngfw-appdetector demo --min-samples 1

# Live web GUI
ngfw-appdetector serve -c config.yaml --no-browser --port 8765
# → http://127.0.0.1:8765

# Search FMC events from terminal (rich table)
ngfw-appdetector fmc-search -c config.yaml --since 5m --limit 50
ngfw-appdetector fmc-search -c config.yaml --dst 1.2.3.4 --dport 443 --since 1h

# Tests
pytest -q
```

`-c` is optional: when omitted, `load_config` searches
`$NGFW_APPDETECTOR_CONFIG` → `./config.yaml` → `./config.yml` →
`~/.config/ngfw-appdetector/config.yaml`. A `-c` path that doesn't exist is
a hard error. See [ADR-0005](docs/decisions/0005-config-auto-discovery.md).

When running the web server in the background for verification, **redirect to a
log file** (`> /tmp/ngfw.log 2>&1 &`). The HTMX UI polls `/api/events` once a
second and the access-log spam will overflow your context otherwise.

## FMC integration: critical facts

The public Cisco FMC REST API on **FMC 7.6.x** does **not** expose connection
events. Don't try to add new `/api/fmc_config/...` paths for events — they 404.

We use the SPA's **private** endpoint instead:

- **Endpoint**: `GET /events/get.cgi?format=ndjson-objs&table=rna_flow_stats&...`
- **Auth**: form POST to `/login.cgi` (priming GET `/ui/login` first) → sets
  `CGISESSID` cookie. The REST `X-auth-access-token` does **not** work here.
- **Re-login**: on 403, drop the cookie and re-auth once.
- **Implementation**: `src/ngfw_appdetector/ngfw_collector/ui_source.py`
  (`FmcUiClient`, `FmcUiEventPoller`).
- **Default columns** include `tlsfp_fingerprint`, `user_agent`, `http_referer`,
  `web_app`, `web_app_tag_mult`, `referenced_host`, etc. See `_DEFAULT_COLUMNS`.
- **Constraints field names**: `source`, `destination`, `sport`, `dport`. Port
  values must be quoted as `"<port> / <proto>"` (e.g. `"443 / tcp"`).
- **Caveat**: undocumented endpoint; column set and shape can change between
  FMC versions. Treat it as a scrape, not an API.

The legacy `FmcClient` in `ngfw_collector/fmc_client.py` is still kept for
`fmc-test` (login probe) but is **not** the data source for events.

## Code layout quick map

- `cli.py` — every Typer command + small helpers like `_parse_since`.
- `config.py` — `AppConfig` (Pydantic), YAML loader, env overrides.
- `models.py` — `FiveTuple`, `LocalFlow`, `NgfwEvent`, `CorrelatedSample`,
  `AppFingerprint`. Edit here when adding fields visible to multiple modules.
- `correlator/engine.py` — 5-tuple + time-window matcher.
- `flow_monitor/` — `proc_tracker.py` (psutil + `lsof` fallback) and
  `socket_source.py` (polling source).
- `lua_generator/` — `aggregator.py` distills `AppFingerprint`, `renderer.py`
  renders `templates/detector.lua.j2`.
- `ngfw_collector/`
  - `ui_source.py` — **primary** event source (UI scrape).
  - `poller.py` — `_to_ngfw_event` normalizer + legacy REST poller.
  - `fmc_client.py` — legacy REST client (login probe only).
  - `mock.py` — JSONL fixture replay.
- `web/`
  - `server.py` — FastAPI routes (`/api/...`, SSE `/api/events`).
  - `session.py` — start/stop the capture pipeline from the UI.
  - `templates/index.html` + `static/app.css` — the whole UI.

## When editing the web UI

- All result tables are rendered client-side from JSON. Server endpoints
  return plain JSON, **not** HTML fragments (we use HTMX only for triggers and
  status, not for HTML swapping).
- Always HTML-escape user/event data: use the local `esc()` helper in
  `index.html`.
- For new detail/expand UI, follow the pattern of `.fmc-detail` /
  `toggleFmcDetail(i)` — a hidden `<tr>` toggled by a `▶/▼` button.

## Things NOT to do

- Don't switch the FMC event source back to REST.
- Don't introduce React/Vue/build tooling for the web UI.
- Don't add database/persistence layers — current pipeline is in-memory +
  optional JSONL log files (`logbook.py`).
- Don't auto-format files you didn't touch.
- Don't print the FMC password to logs or include it in errors.

## Known gaps / open items

- macOS Network Extension replacement for `psutil` socket polling is on the
  roadmap — not started.

## Documentation languages

- User-facing docs are English (`README.md`, `*.md`) with a Chinese copy in
  the same folder (`README.zh-CN.md`, `*.zh-CN.md`). The first lines of each
  file link to its counterpart (`**English** | [简体中文](README.zh-CN.md)`).
- When you change one language version, update the other in the same change
  (same sections, same order). New user-facing docs get both versions.
- Developer docs (ADRs, `AGENTS.md`, `CHANGELOG.md`) are English only.

## See also

- `README.md` / `README.zh-CN.md` — user-facing install + usage (English / Chinese).
- `config.example.yaml` — annotated config reference.
- `docs/decisions/` — Architecture Decision Records (why we chose UI scrape,
  cookie caching, socket-table polling, HTMX, config auto-discovery).
- `/memories/repo/` — short verified facts that survive across sessions.
- `ai_workflow/` — the verified AI-driven workflow (run apps → capture → generate
  Lua → verify on FMC/FTD → evidence deck → publish). Start with
  `ai_workflow/AI_WORKFLOW.md`; it has its own `AGENTS.md`.
