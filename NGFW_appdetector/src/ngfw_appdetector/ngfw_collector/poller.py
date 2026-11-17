"""Poll FMC connection events on an interval and emit normalized NgfwEvent objects."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Callable, Optional

import re

from ..models import FiveTuple, NgfwEvent
from .fmc_client import FmcClient

log = logging.getLogger(__name__)


def _parse_port(value: object) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).strip()
    if not text:
        return None
    match = re.search(r"(\d+)", text)
    if not match:
        return None
    return int(match.group(1))


def _parse_proto(value: object) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    if "/" in text:
        text = text.split("/")[-1].strip()
    if " " in text:
        text = text.split()[-1].strip()
    if text in {"tcp", "udp"}:
        return text
    return None


def _to_ngfw_event(raw: dict) -> Optional[NgfwEvent]:
    """Translate one FMC connection-event dict → NgfwEvent.

    FMC field names vary across versions; we look up common variants and stash
    the rest in `extras` so downstream code can keep iterating.
    """
    def pick(*names: str) -> Optional[str]:
        for n in names:
            v = raw.get(n)
            if v not in (None, "", 0):
                return v if isinstance(v, str) else str(v)
        return None

    src_ip = pick("initiatorIP", "sourceIP", "src_ip")
    dst_ip = pick("responderIP", "destinationIP", "dst_ip")
    src_port = _parse_port(raw.get("initiatorPort") or raw.get("sourcePort") or raw.get("src_port"))
    dst_port = _parse_port(raw.get("responderPort") or raw.get("destinationPort") or raw.get("dst_port"))
    proto_raw = _parse_proto(raw.get("protocol") or raw.get("ipProtocol"))
    if proto_raw is None:
        proto_raw = _parse_proto(raw.get("proto"))
    if proto_raw not in ("tcp", "udp"):
        return None
    if not (src_ip and dst_ip and src_port and dst_port):
        return None

    ts_raw = (
        raw.get("last_packet_unix")
        or raw.get("firstPacketSecond")
        or raw.get("eventSecond")
        or raw.get("timestamp")
    )
    try:
        ts = datetime.fromtimestamp(int(ts_raw), tz=timezone.utc) if ts_raw else datetime.now(timezone.utc)
    except (TypeError, ValueError):
        ts = datetime.now(timezone.utc)

    return NgfwEvent(
        event_id=str(raw.get("id") or raw.get("eventId") or f"{ts.timestamp()}-{src_ip}:{src_port}"),
        timestamp=ts,
        five_tuple=FiveTuple(
            src_ip=src_ip,
            src_port=int(src_port),
            dst_ip=dst_ip,
            dst_port=int(dst_port),
            proto=proto_raw,  # type: ignore[arg-type]
        ),
        application_protocol=pick("applicationProtocol", "appProto"),
        client_application=pick("clientApplication", "client"),
        web_application=pick("webApplication", "webApp"),
        tls_sni=pick("sslServerName", "tlsServerName", "sni"),
        tls_cname=pick("sslCertCN", "tlsCertCN", "certCommonName"),
        http_host=pick("httpHost", "host"),
        http_uri=pick("httpURI", "uri"),
        http_user_agent=pick("userAgent", "httpUserAgent"),
        http_referrer=pick("httpReferrer", "referrer"),
        payload_hex=pick("payloadHex", "clientPayloadHex"),
        extras={k: v for k, v in raw.items() if k not in {
            "initiatorIP", "responderIP", "sourceIP", "destinationIP",
            "initiatorPort", "responderPort", "sourcePort", "destinationPort",
            "protocol", "ipProtocol",
        }},
    )


class EventPoller:
    """Background thread that polls FMC and invokes a callback per event."""

    def __init__(
        self,
        client: FmcClient,
        on_event: Callable[[NgfwEvent], None],
        interval_sec: int = 10,
        lookback_sec: int = 60,
    ) -> None:
        self.client = client
        self.on_event = on_event
        self.interval = max(interval_sec, 1)
        self.lookback = max(lookback_sec, interval_sec)
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._seen_ids: set[str] = set()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="fmc-poller")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._poll_once()
            except Exception:
                log.exception("FMC poll failed")
            self._stop.wait(self.interval)

    def _poll_once(self) -> None:
        end = int(time.time())
        start = end - self.lookback
        offset = 0
        while True:
            page = self.client.list_connection_events(start, end, limit=100, offset=offset)
            items = page.get("items") or page.get("events") or []
            if not items:
                break
            for raw in items:
                evt = _to_ngfw_event(raw)
                if not evt or evt.event_id in self._seen_ids:
                    continue
                self._seen_ids.add(evt.event_id)
                try:
                    self.on_event(evt)
                except Exception:
                    log.exception("on_event callback failed")
            if len(items) < 100:
                break
            offset += 100
        # Cap memory of dedupe set
        if len(self._seen_ids) > 50_000:
            self._seen_ids = set(list(self._seen_ids)[-25_000:])
