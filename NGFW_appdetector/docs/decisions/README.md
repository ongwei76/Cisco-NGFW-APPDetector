# Architecture Decision Records

Short, immutable notes capturing *why* a non-obvious decision was made.
New decisions get a new numbered file — don't edit history in place.
When a decision is reversed, add a new ADR that supersedes the old one
and update the **Status** line of the old one.

Format (keep each ADR ≤ 1 page):

```
# ADR-NNNN: Title
Status: Accepted | Superseded by ADR-XXXX | Deprecated
Date: YYYY-MM-DD

## Context
What problem are we facing? What constraints matter?

## Decision
What did we pick?

## Consequences
Good and bad. What does this commit us to?

## Alternatives considered
Brief: what else was on the table, and why not.
```

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-fmc-ui-scrape-over-rest.md) | Use FMC Web-UI scrape instead of REST API for connection events | Accepted |
| [0002](0002-cookie-session-caching.md) | Cache a single `CGISESSID` session in app state | Accepted |
| [0003](0003-socket-table-over-pcap.md) | Socket-table polling (psutil + lsof) over packet capture for PID attribution | Accepted |
| [0004](0004-fastapi-htmx-no-spa.md) | FastAPI + HTMX + vanilla JS — no SPA framework, no build step | Accepted |
| [0005](0005-config-auto-discovery.md) | Auto-discover `config.yaml` when `-c` is omitted | Accepted |
