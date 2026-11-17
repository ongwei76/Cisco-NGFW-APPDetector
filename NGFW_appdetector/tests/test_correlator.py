from datetime import datetime, timedelta, timezone

from ngfw_appdetector.correlator import Correlator
from ngfw_appdetector.models import FiveTuple, LocalFlow, NgfwEvent


def _flow(ts):
    return LocalFlow(
        five_tuple=FiveTuple(src_ip="10.0.0.1", src_port=5555, dst_ip="1.2.3.4", dst_port=443, proto="tcp"),
        first_seen=ts,
        last_seen=ts,
        pid=123,
        process_name="MyApp",
    )


def _event(ts, sni="example.com"):
    return NgfwEvent(
        event_id=f"e-{ts.timestamp()}",
        timestamp=ts,
        five_tuple=FiveTuple(src_ip="10.0.0.1", src_port=5555, dst_ip="1.2.3.4", dst_port=443, proto="tcp"),
        tls_sni=sni,
    )


def test_match_within_window():
    matches = []
    c = Correlator(on_match=matches.append, time_window_sec=5)
    t = datetime.now(timezone.utc)
    c.add_local(_flow(t))
    c.add_ngfw(_event(t + timedelta(seconds=2)))
    assert len(matches) == 1
    assert matches[0].ngfw.tls_sni == "example.com"
    assert matches[0].local.process_name == "MyApp"


def test_no_match_outside_window():
    matches = []
    c = Correlator(on_match=matches.append, time_window_sec=2)
    t = datetime.now(timezone.utc)
    c.add_local(_flow(t))
    c.add_ngfw(_event(t + timedelta(seconds=10)))
    assert matches == []


def test_either_direction():
    matches = []
    c = Correlator(on_match=matches.append, time_window_sec=5, direction="either")
    t = datetime.now(timezone.utc)
    f = _flow(t)
    # Swap endpoints on the NGFW side
    evt = NgfwEvent(
        event_id="x",
        timestamp=t,
        five_tuple=FiveTuple(src_ip="1.2.3.4", src_port=443, dst_ip="10.0.0.1", dst_port=5555, proto="tcp"),
        tls_sni="example.com",
    )
    c.add_local(f)
    c.add_ngfw(evt)
    assert len(matches) == 1


def test_long_lived_flow_emits_each_event_once():
    matches = []
    c = Correlator(on_match=matches.append, time_window_sec=60)
    t = datetime.now(timezone.utc)
    evt = _event(t)
    c.add_ngfw(evt)
    for i in range(10):
        c.add_local(_flow(t + timedelta(seconds=i)))
    assert len(matches) == 1


def test_distinct_events_on_same_flow_all_emit():
    matches = []
    c = Correlator(on_match=matches.append, time_window_sec=60)
    t = datetime.now(timezone.utc)
    c.add_local(_flow(t))
    c.add_ngfw(_event(t + timedelta(seconds=1), sni="a.example.com"))
    c.add_ngfw(_event(t + timedelta(seconds=2), sni="b.example.com"))
    assert len(matches) == 2
    assert {m.ngfw.tls_sni for m in matches} == {"a.example.com", "b.example.com"}
