"""Time-windowed 5-tuple correlation between local flows and NGFW events.

Both sides feed records asynchronously; we keep recent items in per-key buckets
and emit a CorrelatedSample whenever a match appears.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Callable, Deque, Optional

from ..models import CorrelatedSample, LocalFlow, NgfwEvent

log = logging.getLogger(__name__)


class Correlator:
    def __init__(
        self,
        on_match: Callable[[CorrelatedSample], None],
        time_window_sec: int = 5,
        direction: str = "either",  # "either" | "strict"
    ) -> None:
        self.on_match = on_match
        self.window = timedelta(seconds=time_window_sec)
        self.directional = direction == "strict"
        self._lock = threading.Lock()
        self._local: dict[tuple, Deque[LocalFlow]] = defaultdict(deque)
        self._ngfw: dict[tuple, Deque[NgfwEvent]] = defaultdict(deque)
        self._emitted: set[tuple] = set()

    # ── ingest ──────────────────────────────────────────────────────────────
    def add_local(self, flow: LocalFlow) -> None:
        key = flow.five_tuple.key(directional=self.directional)
        with self._lock:
            self._local[key].append(flow)
            self._evict(self._local[key], flow.last_seen)
            self._try_match(key, local=flow)

    def add_ngfw(self, evt: NgfwEvent) -> None:
        key = evt.five_tuple.key(directional=self.directional)
        with self._lock:
            self._ngfw[key].append(evt)
            self._evict(self._ngfw[key], evt.timestamp)
            self._try_match(key, ngfw=evt)

    # ── internals ───────────────────────────────────────────────────────────
    def _evict(self, dq: Deque, now: datetime) -> None:
        cutoff = now - self.window
        while dq:
            ts = dq[0].last_seen if isinstance(dq[0], LocalFlow) else dq[0].timestamp
            if ts < cutoff:
                dq.popleft()
            else:
                break

    def _try_match(
        self,
        key: tuple,
        local: Optional[LocalFlow] = None,
        ngfw: Optional[NgfwEvent] = None,
    ) -> None:
        if local is not None:
            for evt in list(self._ngfw.get(key, ())):
                if self._within_window(local.last_seen, evt.timestamp):
                    if self._emit(local, evt):
                        return
        elif ngfw is not None:
            for flow in list(self._local.get(key, ())):
                if self._within_window(flow.last_seen, ngfw.timestamp):
                    if self._emit(flow, ngfw):
                        return

    def _within_window(self, a: datetime, b: datetime) -> bool:
        a = a if a.tzinfo else a.replace(tzinfo=timezone.utc)
        b = b if b.tzinfo else b.replace(tzinfo=timezone.utc)
        return abs(a - b) <= self.window

    def _emit(self, flow: LocalFlow, evt: NgfwEvent) -> bool:
        dedupe_key = (flow.five_tuple.key(directional=True), flow.pid, evt.event_id)
        if dedupe_key in self._emitted:
            return False
        self._emitted.add(dedupe_key)
        sample = CorrelatedSample(local=flow, ngfw=evt, confidence=1.0)
        try:
            self.on_match(sample)
        except Exception:
            log.exception("on_match callback failed")
        return True
