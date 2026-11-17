"""Best-effort socket→PID→process mapping on macOS.

There is no kernel API that hands us a (5-tuple → PID) callback, so we approximate:

  1. A background thread polls `psutil.net_connections()` on a short interval
     and caches every (proto, laddr, raddr) → ProcInfo it sees.
  2. Closed sockets stay in the cache for `history_ttl_sec` so that flows
     observed shortly after the socket disappears can still be attributed.
  3. On a lookup miss, the tracker can do an immediate `refresh_now()`
     (debounced) — much faster than waiting for the next poll tick.
  4. If psutil keeps returning nothing for a given endpoint (sandboxed apps,
     permission issues), we fall back to a one-shot `lsof -i -nP` parse.

For production-grade per-packet attribution on macOS, the proper answer is a
Network Extension (Swift, NEFilterDataProvider) — see README §Roadmap.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import psutil

log = logging.getLogger(__name__)

SocketObservation = Callable[[str, tuple, tuple, "ProcInfo", float], None]
"""(proto, laddr, raddr, info, monotonic_ts) -- fired on every refresh per socket."""


@dataclass(frozen=True)
class ProcInfo:
    pid: int
    name: str
    exe: Optional[str]


@dataclass
class _CacheEntry:
    info: ProcInfo
    last_seen: float


class ProcessTracker:
    """Polls socket table, retains TTL'd history, exposes lookup with miss-refresh."""

    LSOF_DEBOUNCE_SEC = 1.0
    REFRESH_DEBOUNCE_SEC = 0.05

    def __init__(
        self,
        refresh_ms: int = 500,
        history_ttl_sec: float = 60.0,
        enable_lsof_fallback: bool = True,
    ) -> None:
        self._refresh_s = max(refresh_ms, 100) / 1000.0
        self._history_ttl = history_ttl_sec
        self._enable_lsof = enable_lsof_fallback and shutil.which("lsof") is not None

        self._lock = threading.Lock()
        self._cache: dict[tuple, _CacheEntry] = {}
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._refresh_lock = threading.Lock()
        self._last_refresh: float = 0.0
        self._last_lsof: float = 0.0
        self._subscribers: list[SocketObservation] = []

        # Stats
        self.lookups = 0
        self.hits = 0
        self.miss_refresh_hits = 0
        self.lsof_hits = 0

    # ── subscribe ────────────────────────────────────────────────────────────
    def subscribe(self, callback: SocketObservation) -> None:
        """Register a callback fired for every socket observation (each refresh)."""
        self._subscribers.append(callback)

    def _notify(self, proto: str, laddr: tuple, raddr: tuple, info: ProcInfo, ts: float) -> None:
        for cb in self._subscribers:
            try:
                cb(proto, laddr, raddr, info, ts)
            except Exception:
                log.exception("proc-tracker subscriber failed")

    # ── lifecycle ────────────────────────────────────────────────────────────
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        # Prime the cache immediately so the very first packet has a chance.
        self._refresh()
        self._thread = threading.Thread(target=self._run, daemon=True, name="proc-tracker")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    # ── lookup ───────────────────────────────────────────────────────────────
    def lookup(
        self,
        proto: str,
        src_ip: str,
        src_port: int,
        dst_ip: str,
        dst_port: int,
        allow_refresh: bool = True,
    ) -> Optional[ProcInfo]:
        """Look up by either direction (local end may be src or dst)."""
        self.lookups += 1
        hit = self._lookup_cached(proto, src_ip, src_port, dst_ip, dst_port)
        if hit:
            self.hits += 1
            return hit

        if allow_refresh:
            self._refresh_debounced()
            hit = self._lookup_cached(proto, src_ip, src_port, dst_ip, dst_port)
            if hit:
                self.miss_refresh_hits += 1
                return hit

        if self._enable_lsof and (time.monotonic() - self._last_lsof) > self.LSOF_DEBOUNCE_SEC:
            self._lsof_refresh()
            hit = self._lookup_cached(proto, src_ip, src_port, dst_ip, dst_port)
            if hit:
                self.lsof_hits += 1
                return hit
        return None

    def stats(self) -> dict:
        return {
            "lookups": self.lookups,
            "hits": self.hits,
            "miss_refresh_hits": self.miss_refresh_hits,
            "lsof_hits": self.lsof_hits,
            "hit_rate": (self.hits + self.miss_refresh_hits + self.lsof_hits) / self.lookups
            if self.lookups
            else 0.0,
            "cache_size": len(self._cache),
        }

    # ── internals ────────────────────────────────────────────────────────────
    def _lookup_cached(
        self, proto: str, src_ip: str, src_port: int, dst_ip: str, dst_port: int
    ) -> Optional[ProcInfo]:
        keys = (
            (proto, (src_ip, src_port), (dst_ip, dst_port)),
            (proto, (dst_ip, dst_port), (src_ip, src_port)),
        )
        with self._lock:
            for k in keys:
                entry = self._cache.get(k)
                if entry:
                    return entry.info
        return None

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._refresh()
            except Exception:
                log.debug("proc-tracker refresh failed", exc_info=True)
            self._stop.wait(self._refresh_s)

    def _refresh_debounced(self) -> None:
        now = time.monotonic()
        if (now - self._last_refresh) < self.REFRESH_DEBOUNCE_SEC:
            return
        if self._refresh_lock.acquire(blocking=False):
            try:
                self._refresh()
            finally:
                self._refresh_lock.release()

    def _refresh(self) -> None:
        try:
            conns = psutil.net_connections(kind="inet")
        except (psutil.AccessDenied, PermissionError):
            log.debug("psutil.net_connections denied; lsof fallback only")
            conns = []

        now = time.monotonic()
        with self._lock:
            for c in conns:
                if not c.laddr or not c.raddr or not c.pid:
                    continue
                proto = "tcp" if c.type == 1 else "udp"  # SOCK_STREAM=1
                info = self._proc_info(c.pid)
                laddr = (c.laddr.ip, c.laddr.port)
                raddr = (c.raddr.ip, c.raddr.port)
                key = (proto, laddr, raddr)
                self._cache[key] = _CacheEntry(info=info, last_seen=now)
                self._notify(proto, laddr, raddr, info, now)
            self._evict_expired(now)
            self._last_refresh = now

        # If psutil gave us nothing useful, augment with lsof (best-effort).
        if not conns and self._enable_lsof:
            self._lsof_refresh()

    def _evict_expired(self, now: float) -> None:
        if len(self._cache) < 2000:
            return
        cutoff = now - self._history_ttl
        stale = [k for k, e in self._cache.items() if e.last_seen < cutoff]
        for k in stale:
            del self._cache[k]
        # Hard cap
        if len(self._cache) > 20_000:
            ordered = sorted(self._cache.items(), key=lambda kv: kv[1].last_seen)
            for k, _ in ordered[: len(self._cache) - 10_000]:
                del self._cache[k]

    def _proc_info(self, pid: int) -> ProcInfo:
        try:
            p = psutil.Process(pid)
            return ProcInfo(pid=pid, name=p.name(), exe=p.exe() or None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return ProcInfo(pid=pid, name="unknown", exe=None)

    # ── lsof fallback ───────────────────────────────────────────────────────
    def _lsof_refresh(self) -> None:
        """Parse `lsof -i -nP` and merge into cache. Best-effort."""
        self._last_lsof = time.monotonic()
        try:
            proc = subprocess.run(
                ["lsof", "-i", "-nP", "-F", "pcPnT"],
                capture_output=True,
                text=True,
                timeout=2,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return
        if proc.returncode not in (0, 1):  # lsof returns 1 if some FDs unreadable
            return

        now = time.monotonic()
        cur_pid = None
        cur_name = "unknown"
        added = 0
        with self._lock:
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
                    proto_lower, laddr, raddr = parsed
                    info = ProcInfo(pid=cur_pid, name=cur_name, exe=None)
                    key = (proto_lower, laddr, raddr)
                    self._cache[key] = _CacheEntry(info=info, last_seen=now)
                    self._notify(proto_lower, laddr, raddr, info, now)
                    added += 1
        if added:
            log.debug("lsof fallback added %d socket(s)", added)


def _parse_lsof_name(name: str) -> Optional[tuple[str, tuple[str, int], tuple[str, int]]]:
    """Parse the 'n' field from `lsof -F`.

    Examples:
      10.0.0.5:51234->1.2.3.4:443      (TCP, no proto prefix in -F mode)
      *:5353                            (listener, ignored — no raddr)
      [::1]:8080->[::1]:51234
    """
    if "->" not in name:
        return None
    left, right = name.split("->", 1)
    laddr = _parse_endpoint(left)
    raddr = _parse_endpoint(right)
    if not laddr or not raddr:
        return None
    # `lsof -F pcPnT` doesn't give us proto on the 'n' line; assume tcp (most common).
    # In practice, the live psutil refresh will overwrite with the correct proto.
    return ("tcp", laddr, raddr)


def _parse_endpoint(s: str) -> Optional[tuple[str, int]]:
    s = s.strip()
    if not s:
        return None
    # [::1]:port
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
