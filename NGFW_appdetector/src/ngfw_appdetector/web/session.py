"""Web session: wraps a long-running flow-capture pipeline behind a single
start/stop interface so the FastAPI app can drive it. One session at a time —
the GUI is meant for interactive operator use, not multi-tenant serving.
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from ..config import AppConfig
from ..correlator import Correlator
from ..flow_monitor import SocketFlowSource
from ..lua_generator import FingerprintAggregator, LuaRenderer
from ..models import CorrelatedSample, LocalFlow
from ..ngfw_collector import FmcUiClient, FmcUiEventPoller

log = logging.getLogger(__name__)


class SessionState:
    IDLE = "idle"
    RUNNING = "running"
    DRAINING = "draining"
    STOPPED = "stopped"
    ERROR = "error"


class CaptureSession:
    """Singleton-ish capture session driven by the web UI."""

    def __init__(self, cfg: AppConfig, output_dir: Path) -> None:
        self.cfg = cfg
        self.output_dir = output_dir
        self.state: str = SessionState.IDLE
        self.error: Optional[str] = None
        self.started_at: Optional[datetime] = None
        self.stopped_at: Optional[datetime] = None
        self.drain_until: Optional[datetime] = None
        self.params: dict[str, Any] = {}

        self._lock = threading.Lock()
        self._flows: dict[tuple, LocalFlow] = {}
        self._samples: list[CorrelatedSample] = []
        self._flow_log: deque[LocalFlow] = deque(maxlen=500)
        self._match_log: deque[CorrelatedSample] = deque(maxlen=500)

        self._socket_src: Optional[SocketFlowSource] = None
        self._poller: Any = None
        self._correlator: Optional[Correlator] = None
        self._aggregator: Optional[FingerprintAggregator] = None
        self._drain_thread: Optional[threading.Thread] = None

    # ── lifecycle ───────────────────────────────────────────────────────────
    def start(
        self,
        *,
        exclude_host: Optional[list[str]] = None,
        process_name: Optional[str] = None,
    ) -> None:
        with self._lock:
            if self.state in {SessionState.RUNNING, SessionState.DRAINING}:
                raise RuntimeError("Session already running or waiting for FMC events")
            self.state = SessionState.RUNNING
            self.error = None
            self.started_at = datetime.now(timezone.utc)
            self.stopped_at = None
            self.drain_until = None
            self.params = {
                "exclude_host": list(exclude_host or []),
                "process_name": process_name,
            }
            self._flows.clear()
            self._samples.clear()
            self._flow_log.clear()
            self._match_log.clear()

        try:
            self._aggregator = FingerprintAggregator(
                min_samples=self.cfg.generator.min_samples,
                excluded_hosts=exclude_host,
            )
            self._correlator = Correlator(
                on_match=self._on_match,
                time_window_sec=self.cfg.correlator.time_window_sec,
                direction=self.cfg.correlator.match_direction,
            )
            self._socket_src = SocketFlowSource(
                on_flow=self._on_flow,
                proc_refresh_ms=self.cfg.capture.proc_refresh_ms,
            )

            if True:
                fmc = FmcUiClient(
                    host=self.cfg.fmc.host,
                    username=self.cfg.fmc.username,
                    password=self.cfg.fmc.password,
                    verify_tls=self.cfg.fmc.verify_tls,
                )
                fmc.login()
                self._poller = FmcUiEventPoller(
                    client=fmc,
                    on_event=self._correlator.add_ngfw,
                    interval_sec=self.cfg.fmc.poll_interval_sec,
                    lookback_sec=self.cfg.fmc.poll_lookback_sec,
                )

            self._socket_src.start()
            self._poller.start()
            log.info("Web session started")
        except Exception as e:
            self.state = SessionState.ERROR
            self.error = str(e)
            self._teardown()
            raise

    def stop(self) -> None:
        with self._lock:
            if self.state != SessionState.RUNNING:
                return
            self.state = SessionState.DRAINING
            self.drain_until = datetime.now(timezone.utc) + timedelta(
                seconds=max(0, self.cfg.capture.fmc_drain_sec)
            )

        if self._socket_src is not None:
            try:
                self._socket_src.stop()
            except Exception as e:
                log.exception("socket_src stop failed")
                if self._poller is not None:
                    try:
                        self._poller.stop()
                    except Exception:
                        log.exception("poller cleanup failed after local capture stop error")
                with self._lock:
                    self.state = SessionState.ERROR
                    self.error = f"Failed to stop local flow capture: {e}"
                    self.drain_until = None
                return

        self._drain_thread = threading.Thread(
            target=self._finish_fmc_drain,
            daemon=True,
            name="fmc-drain",
        )
        self._drain_thread.start()
        log.info("Local capture stopped; draining FMC events for %d seconds", self.cfg.capture.fmc_drain_sec)

    def _finish_fmc_drain(self) -> None:
        drain_seconds = max(0, self.cfg.capture.fmc_drain_sec)
        if drain_seconds:
            threading.Event().wait(drain_seconds)
        try:
            if self._poller is not None:
                self._poller.stop()
        except Exception as e:
            log.exception("poller stop failed")
            with self._lock:
                self.state = SessionState.ERROR
                self.error = f"Failed while waiting for FMC events: {e}"
                self.drain_until = None
            return

        with self._lock:
            self.state = SessionState.STOPPED
            self.stopped_at = datetime.now(timezone.utc)
            self.drain_until = None
        log.info("Web session stopped (%d flows, %d samples)", len(self._flows), len(self._samples))

    def _teardown(self) -> None:
        if self._poller is not None:
            try:
                self._poller.stop()
            except Exception:
                log.exception("poller stop failed")
        if self._socket_src is not None:
            try:
                self._socket_src.stop()
            except Exception:
                log.exception("socket_src stop failed")

    # ── callbacks ──────────────────────────────────────────────────────────
    def _on_flow(self, fl: LocalFlow) -> None:
        target = self.params.get("process_name")
        if target and (fl.process_name or "").casefold() != str(target).casefold():
            return
        with self._lock:
            self._flows[fl.five_tuple.key(directional=False)] = fl
            self._flow_log.append(fl)
        if self._correlator is not None:
            self._correlator.add_local(fl)

    def _on_match(self, s: CorrelatedSample) -> None:
        with self._lock:
            self._samples.append(s)
            self._match_log.append(s)
        if self._aggregator is not None:
            self._aggregator.add(s)

    # ── readers ────────────────────────────────────────────────────────────
    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            proc_stats = self._socket_src.proc.stats() if self._socket_src else {}
            remaining = 0
            if self.drain_until is not None:
                remaining = max(
                    0,
                    int((self.drain_until - datetime.now(timezone.utc)).total_seconds() + 0.999),
                )
            return {
                "state": self.state,
                "error": self.error,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
                "drain_until": self.drain_until.isoformat() if self.drain_until else None,
                "drain_remaining_sec": remaining,
                "params": dict(self.params),
                "counts": {
                    "flows": len(self._flows),
                    "samples": len(self._samples),
                    "fingerprints_ready": (
                        sum(1 for _ in self._aggregator.ready()) if self._aggregator else 0
                    ),
                    "fingerprints_total": (
                        sum(1 for _ in self._aggregator.all()) if self._aggregator else 0
                    ),
                },
                "proc_tracker": proc_stats,
            }

    def flows(self, limit: int = 100) -> list[LocalFlow]:
        with self._lock:
            items = list(self._flows.values())
        items.sort(key=lambda f: f.last_seen, reverse=True)
        return items[:limit]

    def samples(self, limit: int = 100) -> list[CorrelatedSample]:
        with self._lock:
            items = list(self._samples)
        return items[-limit:][::-1]

    def fingerprints(self) -> dict[str, list[Any]]:
        if self._aggregator is None:
            return {"ready": [], "all": []}
        return {
            "ready": list(self._aggregator.ready()),
            "all": list(self._aggregator.all()),
        }

    def generation_signals(self) -> list[dict[str, str]]:
        signal_types = (
            ("tls_sni", "TLS SNI", "tls_snis"),
            ("tls_certificate", "TLS Certificate", "tls_cnames"),
            ("tls_host_suffix", "TLS Host Suffix", "tls_host_suffixes"),
            ("http_host", "HTTP Host", "http_hosts"),
        )
        signals: dict[tuple[str, str], dict[str, str]] = {}
        for fp in self.fingerprints()["ready"]:
            for signal_type, label, attribute in signal_types:
                for value in getattr(fp, attribute):
                    key = (signal_type, value.casefold())
                    signals[key] = {
                        "type": signal_type,
                        "type_label": label,
                        "value": value,
                    }
        return sorted(
            signals.values(),
            key=lambda item: (item["value"].casefold(), item["type"]),
        )

    @staticmethod
    def _filtered_fingerprint(fp: Any, exclude_hosts: list[str]) -> Any:
        selected = {value.strip().casefold() for value in exclude_hosts if value.strip()}
        selected_exact = {value for value in selected if not value.startswith(".")}
        selected_suffix = {value for value in selected if value.startswith(".")}

        def exact_is_excluded(value: str) -> bool:
            normalized = value.casefold()
            return normalized in selected_exact or any(
                normalized == suffix[1:] or normalized.endswith(suffix)
                for suffix in selected_suffix
            )

        def suffix_is_excluded(value: str) -> bool:
            normalized = value.casefold()
            return (
                normalized in selected_suffix
                or any(
                    exact == normalized[1:] or exact.endswith(normalized)
                    for exact in selected_exact
                )
            )

        return fp.model_copy(
            update={
                "tls_snis": [
                    value for value in fp.tls_snis if not exact_is_excluded(value)
                ],
                "tls_cnames": [
                    value for value in fp.tls_cnames if not exact_is_excluded(value)
                ],
                "http_hosts": [
                    value for value in fp.http_hosts if not exact_is_excluded(value)
                ],
                "tls_host_suffixes": [
                    value
                    for value in fp.tls_host_suffixes
                    if not suffix_is_excluded(value)
                ],
                "excluded_hosts": sorted(
                    set(fp.excluded_hosts).union(exclude_hosts),
                    key=str.casefold,
                ),
            }
        )

    def generate_lua(self, app_name: str, exclude_hosts: Optional[list[str]] = None) -> list[Path]:
        if self._aggregator is None:
            return []
        renderer = LuaRenderer(self.output_dir)
        written: list[Path] = []
        for fp in self._aggregator.ready():
            filtered_fp = self._filtered_fingerprint(fp, exclude_hosts or [])
            if not any(
                (
                    filtered_fp.tls_snis,
                    filtered_fp.tls_cnames,
                    filtered_fp.tls_host_suffixes,
                    filtered_fp.http_hosts,
                )
            ):
                continue
            named_fp = filtered_fp.model_copy(update={"app_name": app_name})
            written.append(renderer.render(named_fp))
        return written
