from datetime import datetime, timezone

from ngfw_appdetector.models import FiveTuple, NgfwEvent
from ngfw_appdetector.ngfw_collector import ui_source
from ngfw_appdetector.ngfw_collector.ui_source import FmcUiClient, _flatten


def _wrap(v: str) -> dict:
    return {"_0": {"v": v, "c": {}}}


def test_flatten_keeps_client_app_distinct_from_web_app() -> None:
    row = {
        "source": _wrap("192.168.1.10"),
        "destination": _wrap("157.240.1.35"),
        "sport": {"_0": {"v": "52555 / tcp", "c": {"src_port": "52555", "protocol": "tcp"}}},
        "dport": {"_0": {"v": "443 / tcp", "c": {"dst_port": "443", "protocol": "tcp"}}},
        "first_packet_unix": _wrap("1785000000"),
        "index": _wrap("evt-1"),
        "web_app": _wrap("Facebook"),
        "clientapp": _wrap("SSL client"),
    }

    flat = _flatten(row)

    assert flat["webApplication"] == "Facebook"
    assert flat["clientApplication"] == "SSL client"


def test_flatten_client_app_absent_stays_none() -> None:
    row = {
        "source": _wrap("192.168.1.10"),
        "destination": _wrap("157.240.1.35"),
        "sport": {"_0": {"v": "52555 / tcp", "c": {"src_port": "52555", "protocol": "tcp"}}},
        "dport": {"_0": {"v": "443 / tcp", "c": {"dst_port": "443", "protocol": "tcp"}}},
        "first_packet_unix": _wrap("1785000000"),
        "index": _wrap("evt-1"),
        "web_app": _wrap("Facebook"),
    }

    flat = _flatten(row)

    assert flat["webApplication"] == "Facebook"
    assert flat["clientApplication"] is None


def test_flatten_infers_protocol_from_port_text_when_metadata_missing() -> None:
    row = {
        "source": _wrap("192.168.100.14"),
        "destination": _wrap("203.0.113.7"),
        "sport": {"_0": {"v": "46618 / tcp", "c": {}}},
        "dport": {"_0": {"v": "80 (http) / tcp", "c": {}}},
        "first_packet_unix": _wrap("1785000000"),
        "index": _wrap("evt-2"),
    }

    flat = _flatten(row)

    assert flat["src_port"] == "46618"
    assert flat["dst_port"] == "80"
    assert flat["protocol"] == "tcp"


def test_flatten_parses_compact_port_proto_format() -> None:
    row = {
        "source": _wrap("192.168.100.14"),
        "destination": _wrap("203.0.113.7"),
        "sport": {"_0": {"v": "4462/tcp", "c": {}}},
        "dport": {"_0": {"v": "80/tcp", "c": {}}},
        "first_packet_unix": _wrap("1785000000"),
        "index": _wrap("evt-3"),
    }

    flat = _flatten(row)

    assert flat["src_port"] == "4462"
    assert flat["dst_port"] == "80"
    assert flat["protocol"] == "tcp"


def test_fmc_clock_offset_drives_queries_and_normalizes_events(monkeypatch) -> None:
    monkeypatch.setattr(ui_source.time, "time", lambda: 1_000.0)
    client = FmcUiClient("fmc.example.test", "user", "password")
    client.clock_offset_sec = 3_600.0
    event = NgfwEvent(
        event_id="event-1",
        timestamp=datetime.fromtimestamp(4_600, timezone.utc),
        five_tuple=FiveTuple(
            src_ip="192.168.100.14",
            src_port=12345,
            dst_ip="203.0.113.7",
            dst_port=80,
            proto="tcp",
        ),
    )

    normalized = client.normalize_event_time(event)

    assert client.server_now_epoch() == 4_600
    assert normalized.timestamp == datetime.fromtimestamp(1_000, timezone.utc)
