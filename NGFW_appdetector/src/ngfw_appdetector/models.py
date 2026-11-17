"""Shared data models used across modules."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

Protocol = Literal["tcp", "udp"]


class FiveTuple(BaseModel):
    """Canonical 5-tuple. Always store as (src_ip, src_port, dst_ip, dst_port, proto)."""

    src_ip: str
    src_port: int
    dst_ip: str
    dst_port: int
    proto: Protocol

    def key(self, directional: bool = True) -> tuple:
        """Hashable key. When directional=False, normalize endpoint order."""
        if directional:
            return (self.src_ip, self.src_port, self.dst_ip, self.dst_port, self.proto)
        a = (self.src_ip, self.src_port)
        b = (self.dst_ip, self.dst_port)
        lo, hi = sorted([a, b])
        return (*lo, *hi, self.proto)


class LocalFlow(BaseModel):
    """A flow observed locally on the Mac, with the originating process."""

    five_tuple: FiveTuple
    first_seen: datetime
    last_seen: datetime
    pid: Optional[int] = None
    process_name: Optional[str] = None
    process_path: Optional[str] = None
    bundle_id: Optional[str] = None  # macOS app bundle, optional
    bytes_sent: int = 0
    bytes_recv: int = 0


class NgfwEvent(BaseModel):
    """A connection event pulled from FMC (already parsed by Snort)."""

    event_id: str
    timestamp: datetime
    five_tuple: FiveTuple
    application_protocol: Optional[str] = None  # e.g. HTTPS
    client_application: Optional[str] = None    # Snort's guess
    web_application: Optional[str] = None
    tls_sni: Optional[str] = None
    tls_cname: Optional[str] = None             # cert CN/SAN
    http_host: Optional[str] = None
    http_uri: Optional[str] = None
    http_user_agent: Optional[str] = None
    http_referrer: Optional[str] = None
    payload_hex: Optional[str] = None           # first-N bytes of client payload, hex
    # Free-form bag for anything else FMC returns
    extras: dict = Field(default_factory=dict)


class CorrelatedSample(BaseModel):
    """A LocalFlow ↔ NgfwEvent match, used as training input for LUA generation."""

    local: LocalFlow
    ngfw: NgfwEvent
    confidence: float = 1.0  # placeholder for future scoring


class AppFingerprint(BaseModel):
    """Aggregated fingerprint for one application, distilled from N samples."""

    app_name: str                     # canonical name (e.g. "MyApp")
    process_name: str                 # source: psutil
    proto: Protocol
    tls_snis: list[str] = Field(default_factory=list)
    tls_cnames: list[str] = Field(default_factory=list)
    tls_host_suffixes: list[str] = Field(default_factory=list)  # e.g. ".weirdapp.io"
    http_hosts: list[str] = Field(default_factory=list)
    http_uri_prefixes: list[str] = Field(default_factory=list)
    http_user_agents: list[str] = Field(default_factory=list)
    payload_patterns_hex: list[str] = Field(default_factory=list)
    dst_ports: list[int] = Field(default_factory=list)
    excluded_hosts: list[str] = Field(default_factory=list)     # never-match safety list
    sample_count: int = 0
