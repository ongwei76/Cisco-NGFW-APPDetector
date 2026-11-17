# ADR-0002: Cache a single `CGISESSID` session in app state
Status: Accepted
Date: 2026-05-29

## Context
Per [ADR-0001](0001-fmc-ui-scrape-over-rest.md) the FMC UI scrape uses
form-login at `/login.cgi` and reuses a `CGISESSID` cookie. Each login
adds 1–2 round-trips and (more importantly) creates a server-side session;
re-logging in per request would be wasteful and may trip rate limits / fill
the FMC's session table.

The web GUI's search panel may fire many `/api/fmc/search` requests in quick
succession (user iterating on filters), and the background `FmcUiEventPoller`
hits the same endpoint every `poll_interval_sec`.

## Decision
Keep **one** `FmcUiClient` cached per `(host, username)` in FastAPI app state
(`_ui_state["client"]`). `_get_ui_client()` lazily logs in once and reuses
the cookie for every subsequent call. On HTTP 403 the client drops the
cookie and re-authenticates exactly once before retrying the request.

If FMC config (host/user) changes via `POST /api/config/fmc`, the cached
client is invalidated so the next request re-logs in with the new credentials.

## Consequences
+ One login per server lifetime in the common case.
+ Session expiry handled transparently — callers don't see 403s.
+ Threaded poller and HTTP handlers can share the same session safely
  (`requests.Session` is thread-safe for our usage pattern: single-host,
  short requests, no streaming).
- Cache lives in process memory only — restart = re-login.
- Multi-worker deployments would each hold their own session. Currently we
  only run uvicorn single-process, so this is fine.

## Alternatives considered
- **Re-login per request**: simplest, safe, but wasteful and fragile under
  any non-trivial polling rate.
- **Persist cookies to disk**: adds I/O and a secret-handling surface for
  marginal benefit (login is fast); rejected.
- **Per-request token via REST**: not available ([ADR-0001](0001-fmc-ui-scrape-over-rest.md)).
