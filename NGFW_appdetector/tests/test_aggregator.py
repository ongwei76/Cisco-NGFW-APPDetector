from datetime import datetime, timezone

from ngfw_appdetector.lua_generator.aggregator import (
    FingerprintAggregator,
    _common_suffix,
    _normalize_host,
    _uri_prefix,
)
from ngfw_appdetector.models import CorrelatedSample, FiveTuple, LocalFlow, NgfwEvent


def _sample(sni=None, host=None, uri=None, ua=None, cname=None, payload=None):
    t = datetime.now(timezone.utc)
    ft = FiveTuple(src_ip="10.0.0.1", src_port=1111, dst_ip="1.2.3.4", dst_port=443, proto="tcp")
    return CorrelatedSample(
        local=LocalFlow(five_tuple=ft, first_seen=t, last_seen=t, pid=1, process_name="MyApp"),
        ngfw=NgfwEvent(
            event_id="e", timestamp=t, five_tuple=ft,
            tls_sni=sni, http_host=host, http_uri=uri, http_user_agent=ua,
            tls_cname=cname, payload_hex=payload,
        ),
    )


def test_uri_prefix():
    assert _uri_prefix("/assets/v2/manifest.json") == "/assets/v2"
    assert _uri_prefix("api/v1/users?id=1") == "/api/v1"
    assert _uri_prefix("/") == "/"


def test_common_suffix_detected():
    s = _common_suffix(["a.weirdapp.io", "b.weirdapp.io", "c.weirdapp.io"])
    assert s == ".weirdapp.io"


def test_common_suffix_skipped_when_diverse():
    s = _common_suffix(["a.foo.com", "b.bar.net", "c.baz.org"])
    assert s is None


def test_exclude_hosts():
    agg = FingerprintAggregator(min_samples=1, excluded_hosts=["badcdn.example.com"])
    agg.add(_sample(sni="api.weirdapp.io"))
    agg.add(_sample(sni="badcdn.example.com"))
    agg.add(_sample(sni="telemetry.weirdapp.io"))
    fp = list(agg.ready())[0]
    assert "badcdn.example.com" not in fp.tls_snis
    assert "api.weirdapp.io" in fp.tls_snis
    assert "badcdn.example.com" in fp.excluded_hosts


def test_finalize_derives_suffix_and_uri():
    agg = FingerprintAggregator(min_samples=1)
    for sni in ["a.weirdapp.io", "b.weirdapp.io", "c.weirdapp.io"]:
        agg.add(_sample(sni=sni, uri="/api/v2/heartbeat"))
    fp = list(agg.ready())[0]
    assert ".weirdapp.io" in fp.tls_host_suffixes
    assert "/api/v2" in fp.http_uri_prefixes


def test_payload_hex_collected():
    agg = FingerprintAggregator(min_samples=1)
    agg.add(_sample(payload="DEADBEEFCAFE"))
    fp = list(agg.ready())[0]
    assert fp.payload_patterns_hex == ["deadbeefcafe"]


def test_user_agent_ignored_and_port_only_rejected():
    agg = FingerprintAggregator(min_samples=1)
    agg.add(_sample(host="proxy.example.net", ua="Mozilla/5.0 TdxW"))
    fp = list(agg.ready())[0]
    assert fp.http_user_agents == []
    assert "proxy.example.net" in fp.http_hosts

    agg2 = FingerprintAggregator(min_samples=1)
    agg2.add(_sample(ua="Mozilla/5.0 TdxW"))
    assert list(agg2.ready()) == []


def test_ip_proxy_endpoint_is_not_a_host_signal():
    agg = FingerprintAggregator(min_samples=1)
    agg.add(_sample(host="203.0.113.7:80"))
    assert list(agg.ready()) == []
    assert _normalize_host("https://[2001:db8::1]:443/path") is None


def test_weak_samples_do_not_satisfy_minimum():
    agg = FingerprintAggregator(min_samples=2)
    agg.add(_sample(ua="Mozilla/5.0"))
    agg.add(_sample(host="appstatic.cmschina.com:443"))
    assert list(agg.ready()) == []
    agg.add(_sample(sni="apprzfx.cmschina.com"))
    fp = list(agg.ready())[0]
    assert fp.sample_count == 2
    assert fp.dst_ports == []
