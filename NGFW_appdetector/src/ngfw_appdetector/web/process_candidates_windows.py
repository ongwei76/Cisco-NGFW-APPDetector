"""Windows-specific process candidate discovery for the web UI."""

from __future__ import annotations

from typing import Dict, List, Optional, Union

import psutil

from ..flow_monitor.proc_tracker_windows import collect_windows_netstat_observations


def discover_windows_socket_process_counts() -> dict[str, int]:
    counts: dict[str, int] = {}

    # Primary path: psutil connection table.
    try:
        for conn in psutil.net_connections(kind="inet"):
            _add_conn_count(counts, conn.pid)
    except (psutil.AccessDenied, PermissionError):
        pass

    # Fallback: netstat parsing for environments where psutil yields nothing.
    if not counts:
        observations = collect_windows_netstat_observations(timeout_sec=3.0)
        for _proto, _laddr, _raddr, pid in observations:
            _add_conn_count(counts, pid)

    return counts


def running_process_name_candidates() -> List[Dict[str, Union[int, str]]]:
    seen: set[str] = set()
    out: List[Dict[str, Union[int, str]]] = []
    for proc in psutil.process_iter(attrs=["pid", "name"]):
        try:
            name = (proc.info.get("name") or "unknown") if proc.info else "unknown"
            key = str(name or "unknown")
            if key in seen:
                continue
            seen.add(key)
            out.append({"process_name": key, "connections": 0})
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception:
            continue
    return out


def _add_conn_count(counts: Dict[str, int], pid: Optional[int]) -> None:
    if not pid:
        return
    try:
        name = psutil.Process(pid).name() or "unknown"
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        name = "unknown"
    except Exception:
        name = "unknown"
    key = str(name or "unknown")
    counts[key] = counts.get(key, 0) + 1
