"""Mock FMC event source used for offline demos and tests."""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Union

from ..models import NgfwEvent
from .poller import _to_ngfw_event


def _coerce_event(raw: Any) -> Optional[NgfwEvent]:
    if isinstance(raw, NgfwEvent):
        return raw
    if not isinstance(raw, dict):
        return None
    if "five_tuple" in raw:
        try:
            return NgfwEvent.model_validate(raw)
        except Exception:
            pass
    return _to_ngfw_event(raw)


def _load_events(fixture: Union[str, Path], *, retime: bool = True) -> List[NgfwEvent]:
    path = Path(fixture)
    if not path.exists():
        raise FileNotFoundError(f"mock FMC fixture not found: {path}")

    events: list[NgfwEvent] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            evt = _coerce_event(raw)
            if evt is not None:
                events.append(evt)

    if not events or not retime:
        return events

    start = min(evt.timestamp for evt in events)
    base = datetime.now(timezone.utc)
    delta = base - start
    for evt in events:
        evt.timestamp = evt.timestamp + delta
    return events


class MockEventPoller:
    """Replay a fixture as though it came from FMC."""

    def __init__(
        self,
        fixture: Union[str, Path],
        on_event: Callable[[NgfwEvent], None],
        *,
        mode: str = "burst",
        retime: bool = True,
        interval_sec: float = 1.0,
    ) -> None:
        self.fixture = Path(fixture)
        self.on_event = on_event
        self.mode = mode
        self.retime = retime
        self.interval_sec = max(interval_sec, 0.05)
        self._events: list[NgfwEvent] = _load_events(self.fixture, retime=retime)
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="mock-fmc-poller")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        if self.mode == "burst":
            for evt in self._events:
                if self._stop.is_set():
                    break
                self.on_event(evt)
            return

        prev: Optional[datetime] = None
        for evt in self._events:
            if self._stop.is_set():
                break
            if prev is not None:
                sleep_for = (evt.timestamp - prev).total_seconds()
                if sleep_for > 0:
                    time.sleep(min(sleep_for, self.interval_sec))
            prev = evt.timestamp
            self.on_event(evt)


def _load_mock_events(fixture: Union[str, Path], *, retime: bool = True) -> Iterable[NgfwEvent]:
    return _load_events(fixture, retime=retime)
