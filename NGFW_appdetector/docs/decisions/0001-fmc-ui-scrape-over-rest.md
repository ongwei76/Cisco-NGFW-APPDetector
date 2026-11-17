# ADR-0001: Use FMC Web-UI scrape instead of REST API for connection events
Status: Accepted
Date: 2026-05-29

## Context
Our pipeline needs FMC Connection Events (with Snort parse results: SNI,
HTTP host/UA, web_app, etc.) to correlate against local socket-table flows.
On FMC **7.6.x** the public REST API (`/api/fmc_config/...`) returns 404 for
every connection-event path we tried; only audit/policy resources are exposed.
We verified this empirically against the lab FMC at `173.39.116.232`.

We need *some* programmatic way to read events; without them the whole
correlator / LUA-generation pipeline has no FMC-side input.

## Decision
Talk to the same private endpoint the FMC SPA's "Unified Events" page hits:

- `GET /events/get.cgi?format=ndjson-objs&table=rna_flow_stats&...`
- Auth: form `POST /login.cgi` (primed by `GET /ui/login`) → server sets a
  `CGISESSID` cookie. Reuse the cookie for subsequent calls.
- Response is NDJSON; each cell is wrapped as `{"_0":{"v":..., "c":{...}}}`.

Implementation: `src/ngfw_appdetector/ngfw_collector/ui_source.py`
(`FmcUiClient`, `FmcUiEventPoller`). The legacy `FmcClient` (REST) is kept
only for the `fmc-test` login probe.

## Consequences
+ We get richer fields than REST would have given us anyway (TLS fingerprint,
  bytes, web_app_tag_mult, detection_type, referenced_host, …).
+ Same auth surface as the GUI — if a human can log in, the tool can.
+ Zero changes required on the FMC side (no API user, no domain UUID dance).
- Endpoint is **undocumented**. Column names, response shape, and even the
  URL can change across FMC upgrades. Treat it as a scrape, not an API.
- When the column set changes, both `_DEFAULT_COLUMNS` and `_flatten()` in
  `ui_source.py` must be updated together.
- Session-based auth ⇒ we must handle expiry (see [ADR-0002](0002-cookie-session-caching.md)).

## Alternatives considered
- **REST API**: dead end on 7.6.x for connection events. Rejected.
- **Syslog / eStreamer**: requires server-side config we can't always touch;
  ingestion pipeline is heavier than HTTP polling.
- **Wait for Cisco to add a REST endpoint**: not a plan.
