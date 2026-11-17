"""Socket-table driven flow source.

Why this exists:
  For the LUA-detector generator use case we only need (5-tuple, process) tuples.
  The kernel socket table — which already maps both — gives us this directly,
  without root and without raw sockets. See README §架构 for the full rationale.

Limitations:
  - Sockets that open and close entirely between two refresh ticks may be missed.
    Mitigation: use a tight `proc_refresh_ms` (100–250ms).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable, Optional

from ..models import FiveTuple, LocalFlow
from .proc_tracker import ProcInfo, ProcessTracker

log = logging.getLogger(__name__)


class SocketFlowSource:
    """Emits LocalFlow events by subscribing to ProcessTracker observations."""

    def __init__(
        self,
        on_flow: Callable[[LocalFlow], None],
        proc_refresh_ms: int = 250,
        enable_lsof_fallback: bool = True,
        skip_loopback: bool = True,
        reemit_interval_s: float = 5.0,
    ) -> None:
        self.on_flow = on_flow
        self.skip_loopback = skip_loopback
        self.reemit_interval_s = reemit_interval_s
        self.proc = ProcessTracker(
            refresh_ms=proc_refresh_ms,
            enable_lsof_fallback=enable_lsof_fallback,
        )
        self.proc.subscribe(self._on_socket)
        self._flows: dict[tuple, LocalFlow] = {}
        self._last_emit: dict[tuple, float] = {}

    # ── lifecycle ────────────────────────────────────────────────────────────
    def start(self) -> None:
        log.info("Starting socket-flow source (refresh=%dms)", int(self.proc._refresh_s * 1000))
        self.proc.start()

    def stop(self) -> None:
        log.info("Stopping socket-flow source (%d unique flow(s) observed)", len(self._flows))
        self.proc.stop()

    @property
    def flows(self) -> dict[tuple, LocalFlow]:
        return self._flows

    # ── internals ───────────────────────────────────────────────────────────
    def _on_socket(
        self,
        proto: str,
        laddr: tuple,
        raddr: tuple,
        info: ProcInfo,
        ts: float,
    ) -> None:
        if self.skip_loopback and (laddr[0].startswith("127.") or raddr[0].startswith("127.")):
            return
        if laddr[0] == "::1" or raddr[0] == "::1":
            return

        ft = FiveTuple(
            src_ip=laddr[0], src_port=laddr[1],
            dst_ip=raddr[0], dst_port=raddr[1],
            proto=proto,  # type: ignore[arg-type]
        )
        key = ft.key(directional=False)
        now = datetime.now(timezone.utc)

        flow = self._flows.get(key)
        is_new = flow is None
        if is_new:
            flow = LocalFlow(
                five_tuple=ft,
                first_seen=now,
                last_seen=now,
                pid=info.pid,
                process_name=info.name,
                process_path=info.exe,
            )
            self._flows[key] = flow
        else:
            flow.last_seen = now
            if flow.process_name in (None, "unknown") and info.name:
                flow.process_name = info.name
                flow.pid = info.pid
                flow.process_path = info.exe

        # Throttle: emit on first sight, then at most once per reemit_interval_s.
        last = self._last_emit.get(key, 0.0)
        if is_new or (ts - last) >= self.reemit_interval_s:
            self._last_emit[key] = ts
            self.on_flow(flow)
