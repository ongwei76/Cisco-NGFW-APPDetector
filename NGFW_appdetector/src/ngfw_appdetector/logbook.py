"""Append-only JSONL writers for local-flow / proc-snapshot logs.

These files are the ground-truth record of what the program read locally:
  flows.jsonl         — one LocalFlow per line (final state on shutdown)
  proc_snapshot.jsonl — one (proto, laddr, raddr, pid, name, exe) per line,
                        captured from ProcessTracker right before shutdown
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .models import LocalFlow


def write_flows_jsonl(path: Path, flows: Iterable[LocalFlow]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w") as f:
        for fl in flows:
            f.write(fl.model_dump_json() + "\n")
            n += 1
    return n


def write_proc_snapshot_jsonl(path: Path, cache_items: Iterable[tuple]) -> int:
    """`cache_items` is iterable of (key, _CacheEntry) tuples from ProcessTracker._cache."""
    path.parent.mkdir(parents=True, exist_ok=True)
    snapped_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    n = 0
    with path.open("w") as f:
        for (proto, laddr, raddr), entry in cache_items:
            rec = {
                "snapped_at": snapped_at,
                "proto": proto,
                "local_ip": laddr[0],
                "local_port": laddr[1],
                "remote_ip": raddr[0],
                "remote_port": raddr[1],
                "pid": entry.info.pid,
                "process_name": entry.info.name,
                "process_path": entry.info.exe,
                "last_seen_monotonic": entry.last_seen,
            }
            f.write(json.dumps(rec) + "\n")
            n += 1
    return n
