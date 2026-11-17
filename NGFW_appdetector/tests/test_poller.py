from ngfw_appdetector.ngfw_collector.poller import _to_ngfw_event


def test_to_ngfw_event_prefers_last_packet_timestamp():
    raw = {
        "id": "evt-1",
        "src_ip": "192.168.100.14",
        "dst_ip": "203.0.113.7",
        "src_port": 49992,
        "dst_port": 80,
        "protocol": "tcp",
        "firstPacketSecond": 100,
        "last_packet_unix": 200,
    }
    evt = _to_ngfw_event(raw)
    assert evt is not None
    assert int(evt.timestamp.timestamp()) == 200


def test_to_ngfw_event_parses_compact_port_proto_text():
    raw = {
        "id": "evt-2",
        "src_ip": "192.168.100.14",
        "dst_ip": "203.0.113.7",
        "src_port": "4462/tcp",
        "dst_port": "80/tcp",
        "protocol": "tcp",
        "firstPacketSecond": 100,
    }
    evt = _to_ngfw_event(raw)
    assert evt is not None
    assert evt.five_tuple.src_port == 4462
    assert evt.five_tuple.dst_port == 80
