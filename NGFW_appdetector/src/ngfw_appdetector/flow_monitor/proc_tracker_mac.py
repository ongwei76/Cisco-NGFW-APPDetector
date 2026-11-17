"""macOS/Unix-specific helpers for socket-to-process discovery."""

from __future__ import annotations

import subprocess
from typing import Optional


def collect_mac_lsof_observations(
    timeout_sec: float = 2.0,
) -> list[tuple[str, tuple[str, int], tuple[str, int], int, str]]:
    """Parse `lsof -i -nP -F` output.

    Returns (proto, laddr, raddr, pid, process_name).
    """
    try:
        proc = subprocess.run(
            ["lsof", "-i", "-nP", "-F", "pcPnT"],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if proc.returncode not in (0, 1):
        return []

    out: list[tuple[str, tuple[str, int], tuple[str, int], int, str]] = []
    cur_pid: Optional[int] = None
    cur_name = "unknown"
    for line in proc.stdout.splitlines():
        if not line:
            continue
        tag, rest = line[0], line[1:]
        if tag == "p":
            try:
                cur_pid = int(rest)
            except ValueError:
                cur_pid = None
            cur_name = "unknown"
        elif tag == "c":
            cur_name = rest
        elif tag == "n" and cur_pid is not None:
            parsed = _parse_lsof_name(rest)
            if not parsed:
                continue
            proto, laddr, raddr = parsed
            out.append((proto, laddr, raddr, cur_pid, cur_name))
    return out


def _parse_lsof_name(name: str) -> Optional[tuple[str, tuple[str, int], tuple[str, int]]]:
    if "->" not in name:
        return None
    left, right = name.split("->", 1)
    laddr = _parse_endpoint(left)
    raddr = _parse_endpoint(right)
    if not laddr or not raddr:
        return None
    return ("tcp", laddr, raddr)


def _parse_endpoint(s: str) -> Optional[tuple[str, int]]:
    s = s.strip()
    if not s:
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
    try:
        return host, int(port)
    except ValueError:
        return None
