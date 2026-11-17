"""Group CorrelatedSamples per process and distill an AppFingerprint.

Heuristics included:
  - Common DNS suffix detection across collected SNIs/hosts → host_suffix patterns
  - URI prefix trimming (keep first 2 path segments) → reduce cardinality
  - User-supplied exclusion list applied at aggregation time
"""

from __future__ import annotations

import ipaddress
import math
import os
from collections import Counter
from typing import Iterable, Optional

from ..models import AppFingerprint, CorrelatedSample


def _add_unique(lst: list[str], val: Optional[str], cap: int = 32) -> None:
    if not val:
        return
    if val in lst:
        return
    if len(lst) >= cap:
        return
    lst.append(val)


def _normalize_host(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    out = value.strip().strip(".").lower()
    if out.startswith("http://"):
        out = out.split("://", 1)[1]
    if out.startswith("https://"):
        out = out.split("://", 1)[1]
    out = out.split("/", 1)[0]
    if out.startswith("[") and "]" in out:
        out = out[1:out.index("]")]
    elif out.count(":") == 1:
        host, port = out.rsplit(":", 1)
        if port.isdigit():
            out = host
    out = out.rstrip(".")
    if out.startswith("*."):
        out = out[2:]
    if not out:
        return None
    try:
        ipaddress.ip_address(out)
    except ValueError:
        return out
    return None


def _uri_prefix(uri: str, keep_segments: int = 2) -> str:
    """/assets/v2/manifest.json → /assets/v2"""
    if not uri.startswith("/"):
        uri = "/" + uri
    parts = uri.split("?", 1)[0].split("/")
    parts = [p for p in parts if p]
    return "/" + "/".join(parts[:keep_segments]) if parts else "/"


def _common_suffix(hosts: list[str], min_share: float = 0.6, min_labels: int = 2) -> Optional[str]:
    """If >= `min_share` of hosts share a DNS suffix of >= `min_labels` labels, return it."""
    if not hosts:
        return None
    label_lists = [h.lower().split(".") for h in hosts if h]
    if not label_lists:
        return None
    suffix_counts: Counter = Counter()
    for labels in label_lists:
        for i in range(min_labels, len(labels) + 1):
            suffix_counts[tuple(labels[-i:])] += 1
    threshold = max(2, math.ceil(len(label_lists) * min_share))
    candidates = [s for s, c in suffix_counts.items() if c >= threshold]
    if not candidates:
        return None
    candidates.sort(key=len, reverse=True)
    return "." + ".".join(candidates[0])


class FingerprintAggregator:
    """Accumulates samples and produces one AppFingerprint per process_name."""

    def __init__(
        self,
        min_samples: int = 3,
        excluded_hosts: Optional[Iterable[str]] = None,
    ) -> None:
        self.min_samples = min_samples
        self.excluded_hosts = {
            normalized
            for host in (excluded_hosts or [])
            if (normalized := _normalize_host(host))
        }
        self._by_app: dict[str, AppFingerprint] = {}

    def add(self, sample: CorrelatedSample) -> None:
        proc = sample.local.process_name or "unknown"
        proto = sample.local.five_tuple.proto
        fp = self._by_app.get(proc)
        if fp is None:
            fp = AppFingerprint(
                app_name=_sanitize_app_name(proc),
                process_name=proc,
                proto=proto,
                excluded_hosts=sorted(self.excluded_hosts),
            )
            self._by_app[proc] = fp

        def _ok(host: Optional[str]) -> Optional[str]:
            host = _normalize_host(host)
            if not host:
                return None
            if host in self.excluded_hosts:
                return None
            return host

        tls_sni = _ok(sample.ngfw.tls_sni)
        tls_cname = _ok(sample.ngfw.tls_cname)
        http_host = _ok(sample.ngfw.http_host)
        payload_hex = sample.ngfw.payload_hex
        if not any((tls_sni, tls_cname, http_host, payload_hex)):
            return

        fp.sample_count += 1
        _add_unique(fp.tls_snis, tls_sni)
        _add_unique(fp.tls_cnames, tls_cname)
        _add_unique(fp.http_hosts, http_host)
        if sample.ngfw.http_uri:
            _add_unique(fp.http_uri_prefixes, _uri_prefix(sample.ngfw.http_uri))
        if payload_hex:
            _add_unique(fp.payload_patterns_hex, payload_hex.lower(), cap=8)

    def finalize(self) -> None:
        """Derive aggregate features (common suffixes) after all samples are added."""
        for fp in self._by_app.values():
            all_hosts = fp.tls_snis + fp.http_hosts + fp.tls_cnames
            suffix = _common_suffix(all_hosts)
            if suffix and suffix not in fp.tls_host_suffixes:
                _add_unique(fp.tls_host_suffixes, suffix)

    def ready(self) -> Iterable[AppFingerprint]:
        self.finalize()
        ready: list[AppFingerprint] = []
        for fp in self._by_app.values():
            if fp.sample_count < self.min_samples:
                continue
            strong_signals = [
                value
                for value in fp.tls_snis + fp.tls_cnames + fp.http_hosts
                if value
            ]
            if not strong_signals and not fp.payload_patterns_hex:
                continue
            ready.append(fp)
        return ready

    def all(self) -> Iterable[AppFingerprint]:
        self.finalize()
        return list(self._by_app.values())


def _sanitize_app_name(name: str) -> str:
    """Make a valid LUA identifier-ish name."""
    stem = os.path.splitext(name)[0]
    out = "".join(c if c.isalnum() else "_" for c in stem)
    if out and out[0].isdigit():
        out = "_" + out
    return out or "UnknownApp"
