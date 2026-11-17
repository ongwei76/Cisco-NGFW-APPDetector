"""macOS-specific process candidate discovery for the web UI."""

from __future__ import annotations

from typing import Dict, List, Optional, Union

import psutil


def discover_mac_socket_process_counts() -> dict[str, int]:
    counts: dict[str, int] = {}

    def _add_conn(pid: Optional[int], default_name: str = "unknown") -> None:
        if not pid:
            return
        try:
            name = psutil.Process(pid).name() or "unknown"
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            name = default_name
        except Exception:
            name = default_name
        key = str(name or "unknown")
        counts[key] = counts.get(key, 0) + 1

    try:
        for conn in psutil.net_connections(kind="inet"):
            _add_conn(conn.pid)
    except (psutil.AccessDenied, PermissionError):
        # macOS can reject global scans when protected PIDs exist.
        for proc in psutil.process_iter(attrs=["pid", "name"]):
            try:
                proc_name = (proc.info.get("name") or "unknown") if proc.info else "unknown"
                for conn in proc.net_connections(kind="inet"):
                    _add_conn(conn.pid, default_name=proc_name)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception:
                continue

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
