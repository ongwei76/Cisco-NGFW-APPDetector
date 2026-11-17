"""Windows-specific helpers for socket-to-process discovery."""

from __future__ import annotations

import subprocess
from typing import Optional


def collect_windows_netstat_observations(
    timeout_sec: float = 3.0,
) -> list[tuple[str, tuple[str, int], tuple[str, int], int]]:
    """Return ESTABLISHED TCP socket observations from `netstat -ano -p tcp`.

    Each item is: (proto, laddr, raddr, pid)
    """
    try:
        proc = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []

    out: list[tuple[str, tuple[str, int], tuple[str, int], int]] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or not line.startswith("TCP"):
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        laddr = _parse_netstat_endpoint(parts[1])
        raddr = _parse_netstat_endpoint(parts[2])
        state = parts[3].upper()
        pid_text = parts[4]
        if state != "ESTABLISHED":
            continue
        if not laddr or not raddr:
            continue
        try:
            pid = int(pid_text)
        except ValueError:
            continue
        if pid <= 0:
            continue
        out.append(("tcp", laddr, raddr, pid))
    return out


def _parse_netstat_endpoint(s: str) -> Optional[tuple[str, int]]:
    s = s.strip()
    if not s or s == "*:*":
        return None
    if s.startswith("["):
        end = s.find("]")
        if end == -1:
            return None
        host = s[1:end]
        rest = s[end + 1 :]
        if not rest.startswith(":"):
            return None
        try:
            return host, int(rest[1:])
        except ValueError:
            return None
    if ":" not in s:
        return None
    host, _, port = s.rpartition(":")
    if not host or host == "*":
        return None
    try:
        return host, int(port)
    except ValueError:
        return None
