from datetime import datetime, timedelta, timezone

from ngfw_appdetector.config import AppConfig
from ngfw_appdetector.models import AppFingerprint
from ngfw_appdetector.web.session import CaptureSession, SessionState


class _FakeSource:
    def __init__(self, calls):
        self.calls = calls

    def stop(self) -> None:
        self.calls.append("local")


class _FakePoller:
    def __init__(self, calls):
        self.calls = calls

    def stop(self) -> None:
        self.calls.append("fmc")


def test_stop_halts_local_capture_before_finishing_fmc_drain(tmp_path) -> None:
    cfg = AppConfig()
    cfg.capture.fmc_drain_sec = 0
    session = CaptureSession(cfg, tmp_path)
    calls = []
    session.state = SessionState.RUNNING
    session._socket_src = _FakeSource(calls)
    session._poller = _FakePoller(calls)

    session.stop()
    session._drain_thread.join(timeout=2)

    assert calls == ["local", "fmc"]
    assert session.state == SessionState.STOPPED
    assert session.drain_until is None


def test_snapshot_reports_fmc_drain_countdown(tmp_path) -> None:
    session = CaptureSession(AppConfig(), tmp_path)
    session.state = SessionState.DRAINING
    session.drain_until = datetime.now(timezone.utc) + timedelta(seconds=30)

    snapshot = session.snapshot()

    assert snapshot["state"] == "draining"
    assert 29 <= snapshot["drain_remaining_sec"] <= 30
    assert snapshot["drain_until"] is not None


class _FakeAggregator:
    def __init__(self, fingerprint):
        self.fingerprint = fingerprint

    def ready(self):
        return [self.fingerprint]

    def all(self):
        return [self.fingerprint]


def test_generate_lua_removes_selected_cdn_and_overlapping_suffix(tmp_path) -> None:
    session = CaptureSession(AppConfig(), tmp_path)
    session._aggregator = _FakeAggregator(
        AppFingerprint(
            app_name="Original",
            process_name="Original.exe",
            proto="tcp",
            tls_snis=["app.example.com", "shared.example.com"],
            tls_host_suffixes=[".example.com"],
            http_hosts=["app.example.com", "shared.example.com"],
            sample_count=3,
        )
    )

    signals = session.generation_signals()
    assert {item["value"] for item in signals} == {
        "app.example.com",
        "shared.example.com",
        ".example.com",
    }

    [path] = session.generate_lua(
        app_name="LocalApp",
        exclude_hosts=["shared.example.com"],
    )
    generated = path.read_text(encoding="utf-8")

    assert 'name = "LocalApp"' in generated
    assert '"app.example.com"' in generated
    assert "shared.example.com" not in generated
    assert '"example.com"' not in generated
