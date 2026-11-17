# ADR-0003: Socket-table polling for PID attribution, not packet capture
Status: Accepted
Date: 2026-05-29

## Context
To generate per-app LUA detectors we need (5-tuple → PID → process name) on
the macOS side, then we correlate that 5-tuple against the FMC event stream.
The "obvious" path is `pcap` + a sniffer, but pcap gives you packets without
process identity — the kernel doesn't write PID into the packet metadata
that BPF exposes.

Recovering PID from a packet capture requires either:
- a Network Extension / system extension (Apple signed, Developer ID),
- DTrace probes (root, brittle across macOS versions), or
- joining pcap against `lsof`/`netstat` snapshots at capture time (race-prone).

We need this to work on a developer's laptop, without sudo, without a signed
Network Extension, and without the user installing kernel modules.

## Decision
Poll the **kernel socket table** directly using `psutil.net_connections()`,
keyed by (laddr, raddr, pid). Fall back to `lsof -nP -iTCP -iUDP` when psutil
returns an empty PID for a socket (common for processes the user can't
inspect without elevated privileges).

Implementation:
- `flow_monitor/proc_tracker.py` — TTL cache, on-demand refresh, hit-rate
  stats, lsof fallback.
- `flow_monitor/socket_source.py` — the polling source the pipeline consumes.

## Consequences
+ No root, no signed extension, no kernel module.
+ The socket table already includes both the 5-tuple **and** the owning PID
  — exactly what packet capture cannot give us directly.
+ Works identically on any macOS dev machine.
- We see *flows*, not packets — can't read the wire bytes. That's fine for
  this project: Snort on the FMC side already did the deep parse (SNI, host,
  UA, payload patterns), so we just consume those parsed fields.
- Short-lived sockets that open and close between polls are missed. Mitigated
  by `proc_refresh_ms: 500` default and TTL retention of recently-seen
  sockets. Acceptable for LUA-detector generation (we want stable apps, not
  one-shot probes).
- Production deployments wanting per-packet PID attribution should follow up
  with a macOS Network Extension as a back-end signal source — listed in
  the roadmap in [README.md](../../README.md). Not yet started.

## Alternatives considered
- **pcap + post-hoc lsof join**: race-prone, misses short flows, requires sudo.
- **macOS Network Extension**: correct long-term answer; requires Swift app,
  Developer ID signing, system-extension approval, IPC. Out of scope for v0.
- **`/proc` style scrape on Linux**: not portable; we're targeting macOS dev
  machines first.
