"""FMC Web-UI scraper source.

Uses the same private endpoint the Unified Events page hits (`/events/get.cgi`).
Auth is a plain form POST to `/login.cgi` which sets a `CGISESSID` cookie.
This bypasses the public REST API (which on FMC 7.6.x exposes no connection
events) at the cost of relying on an undocumented surface — subject to change
across FMC upgrades.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
import urllib.parse
import uuid
from datetime import timedelta
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Iterable, Optional

import requests

from ..models import NgfwEvent
from .poller import _to_ngfw_event

log = logging.getLogger(__name__)

_DEFAULT_COLUMNS = [
    "index",
    "connection_index",
    "first_packet_unix",
    "last_packet_unix",
    "fw_rule_action",
    "source",
    "destination",
    "sport",
    "dport",
    "sensor",
    "bytes_sent",
    "bytes_recv",
    "fw_policy",
    "web_app",
    "fw_rule_name_list",
    "tlsfp_fingerprint",
    "http_referer",
    "web_app_tag_mult",
    "user_agent",
    "detection_type",
    "referenced_host",
    "info",
]


def _cell(row: dict, col: str) -> tuple[Optional[str], dict]:
    inner = (row.get(col) or {}).get("_0") or {}
    return inner.get("v"), (inner.get("c") or {})


def _flatten(row: dict) -> dict:
    """Reshape one UI row into the flat dict our `_to_ngfw_event` expects."""
    src_v, _ = _cell(row, "source")
    dst_v, _ = _cell(row, "destination")
    sport_v, sport_c = _cell(row, "sport")
    dport_v, dport_c = _cell(row, "dport")
    ts_v, _ = _cell(row, "first_packet_unix")
    last_ts_v, _ = _cell(row, "last_packet_unix")
    idx_v, _ = _cell(row, "index")
    web_v, _ = _cell(row, "web_app")
    client_v, _ = _cell(row, "clientapp")
    policy_v, _ = _cell(row, "fw_policy")
    rule_v, _ = _cell(row, "fw_rule_name_list")
    action_v, _ = _cell(row, "fw_rule_action")
    sensor_v, _ = _cell(row, "sensor")
    bs_v, _ = _cell(row, "bytes_sent")
    br_v, _ = _cell(row, "bytes_recv")
    tlsfp_v, _ = _cell(row, "tlsfp_fingerprint")
    referer_v, _ = _cell(row, "http_referer")
    ua_v, _ = _cell(row, "user_agent")
    tags_v, _ = _cell(row, "web_app_tag_mult")
    det_v, _ = _cell(row, "detection_type")
    host_v, _ = _cell(row, "referenced_host")
    info_v, _ = _cell(row, "info")

    def _port(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        m = re.search(r"(\d+)", text)
        return m.group(1) if m else None

    def _proto_from_text(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        text = str(value).strip().lower()
        if "/" in text:
            text = text.split("/")[-1]
        if " " in text:
            parts = text.split()
            if parts and parts[-1] in {"tcp", "udp"}:
                return parts[-1]
        if text in {"tcp", "udp"}:
            return text
        return None

    src_port = sport_c.get("src_port") or _port(sport_v)
    dst_port = dport_c.get("dst_port") or _port(dport_v)
    protocol = sport_c.get("protocol") or dport_c.get("protocol") or _proto_from_text(sport_v) or _proto_from_text(dport_v)

    return {
        "id": idx_v,
        "src_ip": src_v,
        "dst_ip": dst_v,
        "src_port": src_port,
        "dst_port": dst_port,
        "protocol": protocol,
        "firstPacketSecond": ts_v,
        "webApplication": web_v or None,
        "clientApplication": client_v or None,
        "fw_policy": policy_v,
        "fw_rule_name": rule_v,
        "fw_rule_action": action_v,
        "sensor": sensor_v,
        "bytes_sent": bs_v,
        "bytes_recv": br_v,
        "tlsfp_fingerprint": tlsfp_v,
        "httpReferrer": referer_v,
        "userAgent": ua_v,
        "web_app_tags": tags_v,
        "detection_type": det_v,
        "referenced_host": host_v,
        "host": host_v,
        "sni": host_v,
        "info": info_v,
        "last_packet_unix": last_ts_v,
    }


class FmcUiClient:
    """Minimal cookie-session client for the FMC Web UI events endpoint."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        *,
        verify_tls: bool = False,
        timeout: int = 30,
    ) -> None:
        self.base = f"https://{host}"
        self.username = username
        self.password = password
        self.timeout = timeout
        self._session = requests.Session()
        self._session.verify = verify_tls
        self._session.headers.update({"User-Agent": "Mozilla/5.0 ngfw-appdetector"})
        self._logged_in = False
        self.clock_offset_sec = 0.0

    @property
    def http_session(self) -> requests.Session:
        """Cookie session shared with other FMC Web UI features (detector import)."""
        return self._session

    def _sync_clock(self, response: requests.Response, request_started: float) -> None:
        date_header = response.headers.get("Date")
        if not date_header:
            return
        try:
            server_time = parsedate_to_datetime(date_header).timestamp()
        except (TypeError, ValueError, OverflowError):
            log.warning("Unable to parse FMC Date header: %r", date_header)
            return
        request_midpoint = (request_started + time.time()) / 2
        self.clock_offset_sec = server_time - request_midpoint
        log.info("FMC clock offset is %.1f seconds", self.clock_offset_sec)

    def server_now_epoch(self) -> int:
        return int(time.time() + self.clock_offset_sec)

    def normalize_event_time(self, event: NgfwEvent) -> NgfwEvent:
        if abs(self.clock_offset_sec) < 0.5:
            return event
        return event.model_copy(
            update={"timestamp": event.timestamp - timedelta(seconds=self.clock_offset_sec)}
        )

    def login(self) -> None:
        # Priming GET so the server is happy with subsequent POST.
        request_started = time.time()
        priming = self._session.get(f"{self.base}/ui/login", timeout=self.timeout)
        self._sync_clock(priming, request_started)
        r = self._session.post(
            f"{self.base}/login.cgi",
            data={"username": self.username, "password": self.password},
            headers={"Referer": f"{self.base}/ui/login"},
            allow_redirects=False,
            timeout=self.timeout,
        )
        if r.status_code not in (200, 302) or "CGISESSID" not in self._session.cookies:
            raise RuntimeError(
                f"FMC web login failed: status={r.status_code} body={r.text[:200]!r}"
            )
        self._logged_in = True
        log.info("FMC UI login OK (CGISESSID set)")

    def fetch_events(
        self,
        start: int,
        end: int,
        *,
        constraints: Optional[str] = None,
        limit: int = 300,
        columns: Optional[Iterable[str]] = None,
    ) -> list[dict]:
        if not self._logged_in:
            self.login()
        params = {
            "format": "ndjson-objs",
            "table": "rna_flow_stats",
            "columns": ",".join(columns or _DEFAULT_COLUMNS),
            "sort": "-first_packet_unix,-connection_index",
            "start": str(start),
            "end": str(end),
            "limit": str(limit),
            "id": str(uuid.uuid4()),
        }
        if constraints:
            params["constraints"] = constraints
        qs = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        url = f"{self.base}/events/get.cgi?{qs}"
        r = self._session.get(
            url,
            headers={"Referer": f"{self.base}/ui/unified-events"},
            timeout=self.timeout,
        )
        if r.status_code == 403:
            # Session likely expired — re-login once.
            self._logged_in = False
            self.login()
            r = self._session.get(url, headers={"Referer": f"{self.base}/ui/unified-events"}, timeout=self.timeout)
        r.raise_for_status()
        out: list[dict] = []
        for line in r.text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                log.debug("skip non-JSON line: %s (%s)", line[:80], e)
        return out

    @staticmethod
    def build_tuple_constraints(
        src_ip: Optional[str] = None,
        dst_ip: Optional[str] = None,
        src_port: Optional[int] = None,
        dst_port: Optional[int] = None,
        protocol: Optional[str] = None,
        web_app: Optional[str] = None,
    ) -> Optional[str]:
        """Compose an `and(eq(...),eq(...))` constraints string."""
        parts: list[str] = []
        if src_ip:
            parts.append(f"eq(source,{json.dumps(src_ip)})")
        if dst_ip:
            parts.append(f"eq(destination,{json.dumps(dst_ip)})")
        if src_port and protocol:
            parts.append(f"eq(sport,{json.dumps(f'{src_port} / {protocol}')})")
        if dst_port and protocol:
            parts.append(f"eq(dport,{json.dumps(f'{dst_port} / {protocol}')})")
        if web_app:
            parts.append(f"eq(web_app,{json.dumps(web_app)})")
        if not parts:
            return None
        return f"and({','.join(parts)})" if len(parts) > 1 else parts[0]


class FmcUiEventPoller:
    """Drop-in alternative to `EventPoller` — scrapes the Web UI endpoint."""

    def __init__(
        self,
        client: FmcUiClient,
        on_event: Callable[[NgfwEvent], None],
        interval_sec: int = 10,
        lookback_sec: int = 60,
        page_limit: int = 300,
    ) -> None:
        self.client = client
        self.on_event = on_event
        self.interval = max(interval_sec, 1)
        self.lookback = max(lookback_sec, interval_sec)
        self.page_limit = page_limit
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._seen_ids: set[str] = set()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="fmc-ui-poller")
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
                log.exception("FMC UI poll failed")
            self._stop.wait(self.interval)

    def _poll_once(self) -> None:
        end = self.client.server_now_epoch()
        start = end - self.lookback
        rows = self.client.fetch_events(start, end, limit=self.page_limit)
        for row in rows:
            flat = _flatten(row)
            evt = _to_ngfw_event(flat)
            if not evt or evt.event_id in self._seen_ids:
                continue
            evt = self.client.normalize_event_time(evt)
            self._seen_ids.add(evt.event_id)
            try:
                self.on_event(evt)
            except Exception:
                log.exception("on_event callback failed")
        if len(self._seen_ids) > 50_000:
            self._seen_ids = set(list(self._seen_ids)[-25_000:])
