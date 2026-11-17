"""Tests for SocketFlowSource. Drives the subscriber callback directly,
bypassing ProcessTracker's polling thread so the test is deterministic.
"""

from __future__ import annotations

from ngfw_appdetector.flow_monitor.proc_tracker import ProcInfo
from ngfw_appdetector.flow_monitor.socket_source import SocketFlowSource


def test_subscriber_emits_new_flow():
    seen = []
    src = SocketFlowSource(on_flow=seen.append, proc_refresh_ms=100)
    info = ProcInfo(pid=123, name="curl", exe="/usr/bin/curl")
    src._on_socket("tcp", ("10.0.0.5", 51234), ("1.2.3.4", 443), info, 1.0)
    assert len(seen) == 1
    f = seen[0]
    assert f.pid == 123
    assert f.process_name == "curl"
    assert f.five_tuple.src_port == 51234
    assert f.five_tuple.dst_ip == "1.2.3.4"


def test_subscriber_updates_existing_flow():
    seen = []
    # reemit_interval_s=0 -> every observation re-emits, simplest to assert.
    src = SocketFlowSource(on_flow=seen.append, proc_refresh_ms=100, reemit_interval_s=0.0)
    info = ProcInfo(pid=123, name="curl", exe="/usr/bin/curl")
    src._on_socket("tcp", ("10.0.0.5", 51234), ("1.2.3.4", 443), info, 1.0)
    first_last_seen = seen[0].last_seen
    src._on_socket("tcp", ("10.0.0.5", 51234), ("1.2.3.4", 443), info, 2.0)
    # Same underlying flow object, last_seen advanced.
    assert seen[1] is seen[0]
    assert seen[1].last_seen >= first_last_seen
    assert len(src.flows) == 1


def test_emit_throttle_suppresses_repeats_within_window():
    seen = []
    src = SocketFlowSource(on_flow=seen.append, proc_refresh_ms=100, reemit_interval_s=5.0)
    info = ProcInfo(pid=1, name="x", exe=None)
    src._on_socket("tcp", ("10.0.0.5", 1), ("1.2.3.4", 443), info, 0.0)   # first -> emit
    src._on_socket("tcp", ("10.0.0.5", 1), ("1.2.3.4", 443), info, 1.0)   # within window -> skip
    src._on_socket("tcp", ("10.0.0.5", 1), ("1.2.3.4", 443), info, 4.99)  # within window -> skip
    src._on_socket("tcp", ("10.0.0.5", 1), ("1.2.3.4", 443), info, 5.0)   # boundary -> emit
    assert len(seen) == 2
    # But the flow's last_seen is still updated on every observation.
    key = next(iter(src.flows))
    assert src.flows[key].last_seen is not None


def test_subscriber_skips_loopback():
    seen = []
    src = SocketFlowSource(on_flow=seen.append, proc_refresh_ms=100)
    info = ProcInfo(pid=1, name="x", exe=None)
    src._on_socket("tcp", ("127.0.0.1", 1), ("127.0.0.1", 2), info, 1.0)
    src._on_socket("tcp", ("::1", 1), ("::1", 2), info, 1.0)
    assert seen == []


def test_proc_tracker_subscribe_registers_callback():
    from ngfw_appdetector.flow_monitor.proc_tracker import ProcessTracker

    t = ProcessTracker(refresh_ms=100, enable_lsof_fallback=False)
    called = []
    t.subscribe(lambda *a: called.append(a))
    info = ProcInfo(pid=9, name="x", exe=None)
    # Direct invocation of internal notifier — verifies wiring.
    t._notify("tcp", ("a", 1), ("b", 2), info, 1.0)
    assert len(called) == 1
    assert called[0][0] == "tcp"


def test_subscribe_swallows_callback_exception():
    from ngfw_appdetector.flow_monitor.proc_tracker import ProcessTracker

    t = ProcessTracker(refresh_ms=100, enable_lsof_fallback=False)
    t.subscribe(lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
    ok = []
    t.subscribe(lambda *a: ok.append(a))
    info = ProcInfo(pid=9, name="x", exe=None)
    t._notify("tcp", ("a", 1), ("b", 2), info, 1.0)  # must not raise
    assert len(ok) == 1
