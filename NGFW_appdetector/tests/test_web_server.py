from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from ngfw_appdetector.config import AppConfig
from ngfw_appdetector import __version__
from ngfw_appdetector.models import CorrelatedSample, FiveTuple, LocalFlow, NgfwEvent
from ngfw_appdetector.ngfw_collector.ui_source import FmcUiClient
from ngfw_appdetector.web.server import (
    STATIC_DIR,
    TEMPLATE_DIR,
    GenerateRequest,
    StartRequest,
    create_app,
)


def _route_endpoint(app, path: str):
    return next(route.endpoint for route in app.routes if getattr(route, "path", None) == path)


def test_flows_api_returns_every_correlated_fmc_event(tmp_path: Path) -> None:
    app = create_app(AppConfig(), tmp_path)
    session = app.state.session
    now = datetime.now(timezone.utc)
    local_tuple = FiveTuple(
        src_ip="192.168.100.14",
        src_port=51000,
        dst_ip="203.0.113.10",
        dst_port=443,
        proto="tcp",
    )
    local = LocalFlow(
        five_tuple=local_tuple,
        first_seen=now,
        last_seen=now + timedelta(seconds=2),
        pid=42,
        process_name="TdxW.exe",
    )
    session._on_flow(local)

    for index, action in enumerate(("Allow", "Block"), start=1):
        event = NgfwEvent(
            event_id=f"event-{index}",
            timestamp=now + timedelta(seconds=index),
            five_tuple=local_tuple,
            web_application="CMS Securities",
            tls_sni="appstatic.cmschina.com",
            http_referrer="https://cmschina.com/",
            http_user_agent="test-agent",
            extras={
                "fw_rule_action": action,
                "fw_rule_name": f"Rule {index}",
                "fw_policy": "Access Control",
                "sensor": "FTD-01",
                "bytes_sent": str(index * 100),
                "bytes_recv": str(index * 200),
                "tlsfp_fingerprint": f"fingerprint-{index}",
                "web_app_tags": "finance",
                "detection_type": "Encrypted Visibility",
                "info": f"/event/{index}",
            },
        )
        session._on_match(CorrelatedSample(local=local, ngfw=event))

    rows = _route_endpoint(app, "/api/flows")(limit=50)

    assert len(rows) == 1
    correlations = rows[0]["correlations"]
    assert len(correlations) == 2
    assert {event["event_id"] for event in correlations} == {"event-1", "event-2"}
    assert {event["action"] for event in correlations} == {"Allow", "Block"}
    assert correlations[0]["src"] == "192.168.100.14:51000"
    assert correlations[0]["dst"] == "203.0.113.10:443"
    assert correlations[0]["proto"] == "tcp"
    assert correlations[0]["rule"] in {"Rule 1", "Rule 2"}
    assert correlations[0]["policy"] == "Access Control"
    assert correlations[0]["host"] == "appstatic.cmschina.com"
    assert correlations[0]["detection_type"] == "Encrypted Visibility"


def test_local_flow_template_renders_all_fmc_events_with_search_fields() -> None:
    template = (TEMPLATE_DIR / "index.html").read_text(encoding="utf-8")

    assert "corrs[0]" not in template
    assert "events.map((event, eventIndex)" in template
    assert "FMC EVENT" in template
    assert "table.sourceIp" in template
    assert "table.destinationIp" in template
    assert "table.action" in template
    assert "table.webApp" in template
    assert "table.rule" in template
    assert "table.policy" in template
    assert "toggleFlowFmcEvent" in template


def test_web_capture_uses_live_fmc_only() -> None:
    template = (TEMPLATE_DIR / "index.html").read_text(encoding="utf-8")

    assert "mock_fmc" not in StartRequest.model_fields
    assert "Mock FMC fixture" not in template
    assert 'name="mock_fmc"' not in template


def test_generate_api_explains_when_no_detector_is_ready(tmp_path: Path) -> None:
    app = create_app(AppConfig(), tmp_path)

    with pytest.raises(HTTPException) as exc_info:
        _route_endpoint(app, "/api/generate")(GenerateRequest(app_name="CMS_App"))

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == {
        "code": "not_ready",
        "min_samples": 3,
        "candidates": 0,
    }


def test_generate_api_returns_downloadable_file_names(tmp_path: Path) -> None:
    app = create_app(AppConfig(), tmp_path)
    session = app.state.session
    session.fingerprints = lambda: {"ready": [object()], "all": [object()]}
    session.generation_signals = lambda: []
    requested_names: list[str] = []
    session.generate_lua = lambda app_name, exclude_hosts: (
        requested_names.append(app_name) or [tmp_path / f"{app_name}.lua"]
    )

    result = _route_endpoint(app, "/api/generate")(
        GenerateRequest(app_name="CMS_Securities")
    )

    assert result == {"count": 1, "files": ["CMS_Securities.lua"]}
    assert requested_names == ["CMS_Securities"]


def test_generate_api_rejects_request_while_fmc_events_are_draining(tmp_path: Path) -> None:
    app = create_app(AppConfig(), tmp_path)
    app.state.session.state = "draining"

    with pytest.raises(HTTPException) as exc_info:
        _route_endpoint(app, "/api/generate")(GenerateRequest(app_name="CMS_App"))

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "fmc_draining"


@pytest.mark.parametrize(
    "app_name",
    ["TdxW1", "招商证券", "Tdx-W", "Tdx W", "", "SixteenLetters___"],
)
def test_generate_request_rejects_invalid_app_names(app_name: str) -> None:
    with pytest.raises(ValidationError):
        GenerateRequest(app_name=app_name)


def test_fmc_constraints_include_exact_web_app_filter() -> None:
    constraints = FmcUiClient.build_tuple_constraints(
        src_ip="192.0.2.10",
        protocol="tcp",
        web_app="CMS_App",
    )

    assert constraints == 'and(eq(source,"192.0.2.10"),eq(web_app,"CMS_App"))'


def test_cdn_history_warns_before_reusing_previously_excluded_signal(
    tmp_path: Path,
) -> None:
    app = create_app(AppConfig(), tmp_path)
    session = app.state.session
    session.fingerprints = lambda: {"ready": [object()], "all": [object()]}
    session.generation_signals = lambda: [
        {
            "type": "tls_sni",
            "type_label": "TLS SNI",
            "value": "shared.example.net",
        }
    ]
    session.generate_lua = lambda app_name, exclude_hosts: [
        tmp_path / f"{app_name}.lua"
    ]
    generate = _route_endpoint(app, "/api/generate")

    first = generate(
        GenerateRequest(
            app_name="LocalApp",
            exclude_hosts=["shared.example.net"],
        )
    )
    assert first["files"] == ["LocalApp.lua"]
    history = (tmp_path / "cdn_history.json").read_text(encoding="utf-8")
    assert "shared.example.net" in history

    with pytest.raises(HTTPException) as exc_info:
        generate(GenerateRequest(app_name="LocalApp"))

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == {
        "code": "cdn_history_warning",
        "hosts": ["shared.example.net"],
    }

    kept = generate(
        GenerateRequest(
            app_name="LocalApp",
            acknowledged_history_hosts=["shared.example.net"],
        )
    )
    assert kept["files"] == ["LocalApp.lua"]


def test_generate_rejects_excluding_every_usable_signal(tmp_path: Path) -> None:
    app = create_app(AppConfig(), tmp_path)
    session = app.state.session
    session.fingerprints = lambda: {"ready": [object()], "all": [object()]}
    session.generation_signals = lambda: [
        {
            "type": "tls_sni",
            "type_label": "TLS SNI",
            "value": "only.example.net",
        }
    ]
    session.generate_lua = lambda app_name, exclude_hosts: []

    with pytest.raises(HTTPException) as exc_info:
        _route_endpoint(app, "/api/generate")(
            GenerateRequest(
                app_name="LocalApp",
                exclude_hosts=["only.example.net"],
            )
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == {"code": "no_signals_after_exclusion"}
    assert not (tmp_path / "cdn_history.json").exists()


def test_templates_include_freeze_language_and_context_help() -> None:
    index = (TEMPLATE_DIR / "index.html").read_text(encoding="utf-8")
    fmc = (TEMPLATE_DIR / "fmc.html").read_text(encoding="utf-8")
    javascript = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert "dataset.captureState === 'running'" in index
    assert "dataset.captureState === 'draining'" in index
    assert "document.body.dataset.captureState = 'draining'" in index
    assert "await refreshCaptureResults()" in index
    assert "session.drainCountdown" in index
    assert 'id="generateButton"' in index
    assert 'data-i18n="nav.language"' in index
    assert 'data-i18n="nav.language"' in fmc
    assert 'data-page="overview"' in index
    assert 'data-page="fmc"' in fmc
    assert "End-to-end workflow" in javascript
    assert "端到端使用步骤" in javascript
    assert "FMC Connection Search help" in javascript
    assert "FMC 连接事件查询帮助" in javascript


def test_templates_include_product_ui_enhancements() -> None:
    index = (TEMPLATE_DIR / "index.html").read_text(encoding="utf-8")
    fmc = (TEMPLATE_DIR / "fmc.html").read_text(encoding="utf-8")
    javascript = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert "process-picker-row" in index
    assert 'id="generateModal"' in index
    assert 'pattern="[A-Za-z_]{1,15}"' in index
    assert 'class="generate-form" novalidate' in index
    assert "input.value = '';" in index
    assert "app_name: appName" in index
    assert 'id="luaHistorySelect"' in index
    assert 'id="luaContent"' in index
    assert 'id="luaFiles"' not in index
    assert "appI18n.openHelp('import-lua')" in index
    assert "/api/generation-signals" in index
    assert "cdn-signal-checkbox" in index
    assert "resolveHistoricalCdn(true)" in index
    assert "acknowledged_history_hosts" in index
    assert 'name="web_app"' in fmc
    assert "web_app: f.web_app.value.trim() || null" in fmc
    assert "如何在 FMC 导入 Lua Local App Detector" in javascript
    assert "Enablement and business-impact guidance" in javascript
    assert "共享 CDN 域名可能把无关应用错误识别为该应用" in javascript
    assert 'id="fingerprints"' not in index
    assert "renderFingerprints" not in index
    assert "v{{ app_version }}" in index
    assert __version__ == "1.2.0"
    assert 'src="/static/htmx.min.js"' in index
    assert 'src="/static/htmx.min.js"' in fmc
    assert (STATIC_DIR / "htmx.min.js").is_file()
    assert (STATIC_DIR / "htmx.LICENSE").is_file()
