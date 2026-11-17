# ADR-0004: FastAPI + HTMX + vanilla JS for the web GUI — no SPA framework
Status: Accepted
Date: 2026-05-29

## Context
The tool already ships a Typer CLI. We added a web GUI so non-CLI users
(security analysts, lab engineers) can configure FMC, run a capture, and
search connection events. Scope is small: a handful of forms, a few result
tables, an SSE-driven status line. There is no app store, no auth, no
multi-tenancy — it runs on `127.0.0.1` next to the CLI.

We did *not* want:
- a Node toolchain in the repo,
- a build step every time someone tweaks a label,
- a bundle to ship alongside the Python package,
- a TypeScript learning curve for anyone working on the UI.

## Decision
**FastAPI** for endpoints, **Jinja2** for the single page shell, **HTMX**
for triggers (form submits, status refresh hookups), and **vanilla JS** for
result rendering. One template (`web/templates/index.html`) and one
stylesheet (`web/static/app.css`) — that's the whole UI.

Server endpoints return **JSON**, not HTML fragments. We use HTMX for
ergonomics (`hx-post`, SSE binding) but render results client-side so the
same JSON endpoints stay usable for `curl`, tests, and any future programmatic
consumer.

## Consequences
+ Zero JS build pipeline. Edit `index.html` / `app.css`, refresh.
+ JSON endpoints double as the documented external API
  (`POST /api/fmc/search`, `GET /api/flows`, etc.).
+ Single FastAPI process serves everything; the `[web]` install extra is
  the only extra dependency.
+ Easy for AI coding agents (and humans) — no framework idioms to learn.
- We're hand-rolling table rendering, escape helpers, expand/collapse
  patterns. That cost stays manageable as long as scope stays small.
- If the UI grows to dozens of views with shared state, we'll hit limits
  of "one big HTML file + JS functions". When that happens, reconsider —
  but the bar should be high (real product complexity, not feature creep).

## Alternatives considered
- **React/Vue + Vite**: overkill for the current surface; adds Node, build,
  ship complexity.
- **Pure HTMX with server-rendered HTML fragments**: loses the JSON API as
  a side benefit; also harder to test.
- **Streamlit / Gradio**: opinionated layouts, doesn't fit a sidebar-style
  config + dynamic result panel; we'd lose direct API access.
