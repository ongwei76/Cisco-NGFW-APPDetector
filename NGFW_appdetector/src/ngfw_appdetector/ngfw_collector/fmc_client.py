"""Minimal Cisco FMC REST API client.

Auth flow:
  POST /api/fmc_platform/v1/auth/generatetoken  → X-auth-access-token (valid 30min)

Connection events historically live under the analytics path; on newer FMC builds
they are also exposed via the "/api/fmc_config/v1/domain/{uuid}/events/connectionevents"
endpoint. The exact path/version may differ per FMC release — this client centralizes
the URL so it's easy to retarget.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional
from urllib.parse import urljoin

import requests
import urllib3

log = logging.getLogger(__name__)


class FmcAuthError(RuntimeError):
    pass


class FmcClient:
    TOKEN_TTL_SEC = 25 * 60  # FMC token TTL is ~30 min; refresh a little early

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        verify_tls: bool = False,
        timeout: int = 30,
    ) -> None:
        self.base = f"https://{host}"
        self.username = username
        self.password = password
        self.verify_tls = verify_tls
        self.timeout = timeout

        if not verify_tls:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self._session = requests.Session()
        self._session.verify = verify_tls
        self._token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_ts: float = 0.0
        self._domain_uuid: Optional[str] = None
        self._lock = threading.Lock()

    # ── auth ─────────────────────────────────────────────────────────────────
    def login(self) -> None:
        url = urljoin(self.base, "/api/fmc_platform/v1/auth/generatetoken")
        r = self._session.post(
            url, auth=(self.username, self.password), timeout=self.timeout
        )
        if r.status_code != 204:
            raise FmcAuthError(f"FMC login failed: HTTP {r.status_code} {r.text[:200]}")
        self._token = r.headers.get("X-auth-access-token")
        self._refresh_token = r.headers.get("X-auth-refresh-token")
        # FMC returns one or more domain UUIDs in DOMAINS header (JSON list)
        domains = r.headers.get("DOMAINS")
        if domains:
            import json
            try:
                parsed = json.loads(domains)
                if isinstance(parsed, list) and parsed:
                    self._domain_uuid = parsed[0].get("uuid")
            except Exception:
                log.debug("Could not parse DOMAINS header: %r", domains)
        if not self._token:
            raise FmcAuthError("FMC login: no token in response headers")
        self._token_ts = time.time()
        log.info("FMC authenticated (domain=%s)", self._domain_uuid)

    def _ensure_token(self) -> None:
        with self._lock:
            if not self._token or (time.time() - self._token_ts) > self.TOKEN_TTL_SEC:
                self.login()

    @property
    def domain_uuid(self) -> str:
        self._ensure_token()
        if not self._domain_uuid:
            raise FmcAuthError("FMC domain UUID unknown — set fmc.domain_uuid in config.")
        return self._domain_uuid

    def set_domain_uuid(self, uuid: str) -> None:
        self._domain_uuid = uuid

    # ── HTTP ────────────────────────────────────────────────────────────────
    def _request(self, method: str, path: str, **kw: Any) -> requests.Response:
        self._ensure_token()
        headers = kw.pop("headers", {}) or {}
        headers["X-auth-access-token"] = self._token or ""
        headers.setdefault("Content-Type", "application/json")
        url = urljoin(self.base, path)
        r = self._session.request(method, url, headers=headers, timeout=self.timeout, **kw)
        if r.status_code == 401:
            # token may have expired — refresh and retry once
            log.info("FMC 401, re-authenticating")
            self.login()
            headers["X-auth-access-token"] = self._token or ""
            r = self._session.request(method, url, headers=headers, timeout=self.timeout, **kw)
        r.raise_for_status()
        return r

    def get(self, path: str, params: Optional[dict] = None) -> dict:
        r = self._request("GET", path, params=params)
        return r.json() if r.content else {}

    # ── high-level helpers ──────────────────────────────────────────────────
    def list_connection_events(
        self,
        start_time: int,
        end_time: int,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """Return raw FMC connection-events page.

        NOTE: Endpoint path varies by FMC version. Override here if your FMC
        publishes events under a different route.
        """
        path = (
            f"/api/fmc_config/v1/domain/{self.domain_uuid}/events/connectionevents"
        )
        params = {
            "limit": limit,
            "offset": offset,
            "filter": f"startTime:{start_time};endTime:{end_time}",
        }
        return self.get(path, params=params)
