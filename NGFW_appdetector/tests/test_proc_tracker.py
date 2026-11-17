from ngfw_appdetector.flow_monitor.proc_tracker import (
    ProcessTracker,
    _parse_endpoint,
    _parse_lsof_name,
)


def test_parse_endpoint_ipv4():
    assert _parse_endpoint("10.0.0.1:443") == ("10.0.0.1", 443)


def test_parse_endpoint_ipv6():
    assert _parse_endpoint("[::1]:8080") == ("::1", 8080)


def test_parse_endpoint_invalid():
    assert _parse_endpoint("") is None
    assert _parse_endpoint("nocolon") is None
    assert _parse_endpoint("[::1]") is None
    assert _parse_endpoint("host:notaport") is None


def test_parse_lsof_name_tcp():
    out = _parse_lsof_name("10.0.0.5:51234->1.2.3.4:443")
    assert out == ("tcp", ("10.0.0.5", 51234), ("1.2.3.4", 443))


def test_parse_lsof_name_listener_skipped():
    assert _parse_lsof_name("*:5353") is None


def test_tracker_starts_and_stops_cleanly():
    t = ProcessTracker(refresh_ms=200, enable_lsof_fallback=False)
    t.start()
    # Lookup something that almost certainly won't match — verify no crash.
    assert t.lookup("tcp", "203.0.113.1", 12345, "198.51.100.1", 443) is None
    t.stop()
    s = t.stats()
    assert s["lookups"] >= 1
