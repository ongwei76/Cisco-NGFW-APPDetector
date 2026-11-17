import base64
import io
import json
import zipfile
from pathlib import Path
from typing import Any, Optional

import pytest
import requests
from fastapi import HTTPException

from ngfw_appdetector import __version__
from ngfw_appdetector.config import AppConfig
from ngfw_appdetector.web import sharing
from ngfw_appdetector.web.server import TEMPLATE_DIR, ShareSubmissionRequest, create_app
from ngfw_appdetector.web.sharing import (
    LibraryLocation,
    SharingError,
    build_submission,
    extract_host_patterns,
    normalize_email,
    normalize_nickname,
    parse_branch_head,
    sanitize_index_entry,
    sha256_hex,
)

LUA = b'''require "DetectorCommon"
DetectorPackageInfo = { name = "TdxW" }
gHostPatternList = {
    "hq.cmschina.com",
    "tdx.cmschina.com",
}
'''
CDN_LUA = LUA.replace(b'"tdx.cmschina.com"', b'"img.akamaized.net"')
LOCATION = LibraryLocation(owner="org", repo="lib")


class _Resp:
    def __init__(self, status: int, payload: Any = None, content: Optional[bytes] = None) -> None:
        self.status_code = status
        self._payload = payload
        self.content = content if content is not None else json.dumps(payload).encode()

    def json(self) -> Any:
        return self._payload


class _FakeGitHub:
    """Fake raw.githubusercontent.com / jsDelivr hosting of an in-memory file tree."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {"README.md": b"# lib\n"}
        self.ref_status = 200
        self.ref_down = False
        self.raw_down = False
        self.raw_index: Optional[bytes] = None
        self.calls: list[dict[str, Any]] = []
        self.head = "0" * 40
        self.snapshots: dict[str, dict[str, bytes]] = {self.head: dict(self.files)}

    def get(self, url: str, params: Any = None, headers: Any = None, timeout: float = 0) -> _Resp:
        self.calls.append({"url": url, "params": params, "headers": headers})
        if url == "https://github.com/org/lib.git/info/refs":
            if self.ref_down:
                raise requests.ConnectionError("blocked")
            if self.ref_status != 200:
                return _Resp(self.ref_status, {})
            packet = f"{self.head} refs/heads/main\n".encode()
            return _Resp(200, content=f"{len(packet) + 4:04x}".encode() + packet + b"0000")
        for prefix, source in (
            ("https://raw.githubusercontent.com/org/lib/", "github"),
            ("https://cdn.jsdelivr.net/gh/org/lib@", "jsdelivr"),
        ):
            if url.startswith(prefix):
                if source == "github" and self.raw_down:
                    raise requests.ConnectionError("blocked")
                revision, path = url[len(prefix):].split("/", 1)
                files = self.files if revision == "main" else self.snapshots[revision]
                if revision == "main" and path == "library/index.json" and self.raw_index is not None:
                    return _Resp(200, content=self.raw_index)
                return _Resp(200, content=files[path]) if path in files else _Resp(404, {})
        raise AssertionError(f"unexpected GET {url}")


def _endpoint(app, path: str, method: str = "GET"):
    return next(
        route.endpoint
        for route in app.routes
        if getattr(route, "path", None) == path and method in getattr(route, "methods", ())
    )


def _app(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    cfg = AppConfig()
    cfg.sharing.github_owner = "org"
    cfg.sharing.github_repo = "lib"
    output = tmp_path / "out"
    app = create_app(cfg, output)
    (output / "TdxW.lua").write_bytes(LUA)
    fake = _FakeGitHub()
    app.state.sharing.client.session = fake
    return app, output, fake


def test_submission_round_trip_extracts_patterns() -> None:
    filename, data, manifest = build_submission(
        app_name="TdxW", lua_bytes=LUA, nickname=" Yong  Li ", email="yong@example.com",
        fmc_version="7.4.2", notes="ok", tool_version="1.1.0", category="Financial", risk=1, business_relevance=4,
    )
    assert filename.startswith("NGFW-Lua-Submission-TdxW-") and filename.endswith(".zip")
    assert manifest["submitter"] == {"nickname": "Yong Li", "email": "yong@example.com"}
    assert (manifest["category"], manifest["risk"], manifest["business_relevance"]) == ("financial", 1, 4)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert sorted(zf.namelist()) == ["TdxW.lua", "submission.json"]
        assert zf.read("TdxW.lua") == LUA
        stored = json.loads(zf.read("submission.json"))
    assert stored == manifest
    assert manifest["kind"] == "ngfw-lua-submission" and manifest["sha256"] == sha256_hex(LUA)
    assert manifest["host_patterns"] == ["hq.cmschina.com", "tdx.cmschina.com"]
    with pytest.raises(SharingError):
        build_submission(app_name="../x", lua_bytes=LUA, nickname="Y", email="y@example.com",
                         fmc_version="", notes="", tool_version="1", category="financial")
    with pytest.raises(SharingError):
        build_submission(app_name="TdxW", lua_bytes=LUA, nickname="Y", email="y@example.com",
                         fmc_version="", notes="", tool_version="1", category="no such category")
    with pytest.raises(SharingError):
        build_submission(app_name="TdxW", lua_bytes=LUA, nickname="Y", email="y@example.com",
                         fmc_version="", notes="", tool_version="1", category="financial", risk=9)


def test_submission_endpoint_saves_package_and_remembers_submitter(tmp_path: Path, monkeypatch) -> None:
    app, output, _ = _app(tmp_path, monkeypatch)
    result = _endpoint(app, "/api/share/submission", "POST")(
        ShareSubmissionRequest(lua_name="TdxW.lua", nickname="Yong", email="yong@example.com", notes="n", category="financial")
    )
    assert result["maintainer_email"] == "yongwli@cisco.com"
    saved = Path(result["saved_path"])
    assert saved.parent == (output / "submissions").resolve()
    assert zipfile.ZipFile(saved).read("TdxW.lua") == LUA
    assert base64.b64decode(result["zip_b64"]) == saved.read_bytes()
    assert _endpoint(app, "/api/share/submitter")() == {"nickname": "Yong", "email": "yong@example.com"}
    with pytest.raises(HTTPException) as e:
        _endpoint(app, "/api/share/submission", "POST")(
            ShareSubmissionRequest(lua_name="TdxW.lua", nickname="Yong", email="bad", category="financial")
        )
    assert e.value.status_code == 400
    with pytest.raises(HTTPException) as e:
        _endpoint(app, "/api/share/submission", "POST")(
            ShareSubmissionRequest(lua_name="Nope.lua", nickname="Yong", email="yong@example.com", category="financial")
        )
    assert e.value.status_code == 404


def _publish(fake: _FakeGitHub, version: int, lua: bytes = LUA, note: str = "") -> None:
    """What the maintainer tool writes to the repository."""
    path = f"library/TdxW/{version}/TdxW.lua"
    fake.files[path] = lua
    entries = json.loads(fake.files.get("library/index.json", b'{"entries": []}'))["entries"]
    entries.append({
        "app_name": "TdxW", "version": version, "lua_path": path, "sha256": sha256_hex(lua),
        "nickname": "Yong", "review_note": note, "published_at": "2026-10-28T08:00:00+00:00",
        "host_patterns": extract_host_patterns(lua.decode()),
    })
    fake.files["library/index.json"] = json.dumps({"schema": 1, "entries": entries}).encode()
    fake.head = f"{len(fake.snapshots):040x}"
    fake.snapshots[fake.head] = dict(fake.files)


def test_library_read_verify_download_and_mirror_fallback(tmp_path: Path, monkeypatch) -> None:
    app, _, fake = _app(tmp_path, monkeypatch)
    _publish(fake, 1, note="tested on 7.4")
    _publish(fake, 2)
    library = _endpoint(app, "/api/share/library")(refresh=True)
    assert library["source"] == "github-commit"
    assert [(e["app_name"], e["version"]) for e in library["entries"]] == [("TdxW", 2), ("TdxW", 1)]
    assert library["entries"][1]["review_note"] == "tested on 7.4"
    assert library["entries"][0]["host_patterns"] == ["hq.cmschina.com", "tdx.cmschina.com"]

    viewed = _endpoint(app, "/api/share/lua")(app_name="TdxW", version=1)
    assert viewed["verified"] is True and viewed["content"] == LUA.decode()
    download = _endpoint(app, "/api/share/lua/download")(app_name="TdxW", version=1)
    assert download.body == LUA and 'filename="TdxW.lua"' in download.headers["content-disposition"]

    fake.raw_down = True
    assert _endpoint(app, "/api/share/library")(refresh=True)["source"] == "jsdelivr-commit"

    fake.files["library/TdxW/1/TdxW.lua"] = LUA + b"-- tampered"
    fake.snapshots[fake.head]["library/TdxW/1/TdxW.lua"] = LUA + b"-- tampered"
    assert _endpoint(app, "/api/share/lua")(app_name="TdxW", version=1)["verified"] is False
    with pytest.raises(HTTPException) as e:
        _endpoint(app, "/api/share/lua/download")(app_name="TdxW", version=1)
    assert e.value.status_code == 409


def test_library_unreachable_is_actionable(tmp_path: Path, monkeypatch) -> None:
    app, _, fake = _app(tmp_path, monkeypatch)
    assert _endpoint(app, "/api/share/library")(refresh=True) == {"entries": [], "source": "empty"}
    fake.raw_down = True
    fake.get = lambda url, **kw: (_ for _ in ()).throw(requests.ConnectionError("offline"))
    with pytest.raises(HTTPException) as e:
        _endpoint(app, "/api/share/library")(refresh=True)
    assert e.value.status_code == 502
    assert "github-head: ConnectionError" in e.value.detail
    assert "github: ConnectionError" in e.value.detail and "jsdelivr: ConnectionError" in e.value.detail
    with pytest.raises(HTTPException) as e:
        _endpoint(app, "/api/share/lua")(app_name="../x", version=1)
    assert e.value.status_code == 400


def test_refresh_bypasses_stale_raw_index_without_a_token(tmp_path: Path, monkeypatch) -> None:
    app, _, fake = _app(tmp_path, monkeypatch)
    _publish(fake, 1)
    fake.raw_index = fake.files["library/index.json"]
    endpoint = _endpoint(app, "/api/share/library")
    assert [e["version"] for e in endpoint()["entries"]] == [1]
    _publish(fake, 2, note="new review note")
    assert [e["version"] for e in endpoint()["entries"]] == [1]
    result = endpoint(refresh=True)
    assert result["source"] == "github-commit"
    assert [e["version"] for e in result["entries"]] == [2, 1]
    assert result["entries"][0]["review_note"] == "new review note"
    request = next(c for c in reversed(fake.calls) if c["url"].endswith("/info/refs"))
    assert request["params"] == {"service": "git-upload-pack"}
    assert request["headers"]["Cache-Control"] == "no-cache"
    assert "Authorization" not in request["headers"]
    assert f"/{fake.head}/library/index.json" in fake.calls[-1]["url"]


def test_lookup_refreshes_a_cached_index_when_version_is_missing(tmp_path: Path, monkeypatch) -> None:
    app, _, fake = _app(tmp_path, monkeypatch)
    _publish(fake, 1)
    _endpoint(app, "/api/share/library")()
    _publish(fake, 2, lua=LUA + b"-- version two\n")
    viewed = _endpoint(app, "/api/share/lua")(app_name="TdxW", version=2)
    assert viewed["verified"] is True
    assert viewed["entry"]["version"] == 2 and viewed["content"].endswith("-- version two\n")


def test_download_stays_at_the_index_commit_when_branch_moves(tmp_path: Path, monkeypatch) -> None:
    app, _, fake = _app(tmp_path, monkeypatch)
    _publish(fake, 1)
    _endpoint(app, "/api/share/library")(refresh=True)
    snapshot = fake.head
    fake.files["library/TdxW/1/TdxW.lua"] = LUA + b"-- changed on branch\n"
    _publish(fake, 2)
    viewed = _endpoint(app, "/api/share/lua")(app_name="TdxW", version=1)
    assert viewed["verified"] and viewed["content"] == LUA.decode()
    assert f"/{snapshot}/library/TdxW/1/TdxW.lua" in fake.calls[-1]["url"]


def test_unavailable_live_head_has_a_labeled_logged_fallback(tmp_path: Path, monkeypatch, caplog) -> None:
    app, _, fake = _app(tmp_path, monkeypatch)
    _publish(fake, 1)
    fake.ref_status = 403
    result = _endpoint(app, "/api/share/library")(refresh=True)
    assert result["source"] == "github" and result["entries"][0]["version"] == 1
    assert "github-head: HTTP 403" in caplog.text and "delayed changes" in caplog.text
    assert fake.calls[-1]["params"]["t"]


def test_authoritative_missing_index_does_not_resurrect_stale_entries(tmp_path: Path, monkeypatch) -> None:
    app, _, fake = _app(tmp_path, monkeypatch)
    _publish(fake, 1)
    fake.raw_index = fake.files.pop("library/index.json")
    fake.snapshots[fake.head].pop("library/index.json")
    assert _endpoint(app, "/api/share/library")(refresh=True) == {"entries": [], "source": "empty"}
    assert all("/main/library/index.json" not in c["url"] and "@main/library/index.json" not in c["url"] for c in fake.calls)


@pytest.mark.parametrize("bad", [b"", b"zzzz", b"0010short", b"0001"])
def test_git_branch_advertisement_rejects_malformed_or_missing_refs(bad: bytes) -> None:
    with pytest.raises(SharingError):
        parse_branch_head(bad, "main")


def test_git_branch_advertisement_matches_the_exact_branch() -> None:
    def packet(value: bytes) -> bytes:
        return f"{len(value) + 4:04x}".encode() + value
    advertisement = packet(b"# service=git-upload-pack\n") + b"0000"
    advertisement += packet(b"a" * 40 + b" HEAD\0multi_ack\n")
    advertisement += packet(b"b" * 40 + b" refs/heads/main-old\n")
    advertisement += packet(b"c" * 40 + b" refs/heads/main\n") + b"0000"
    assert parse_branch_head(advertisement, "main") == "c" * 40
    with pytest.raises(SharingError, match="not advertised"):
        parse_branch_head(advertisement, "missing")


def test_index_entries_are_sanitized() -> None:
    good = {"lua_path": "library/TdxW/3/TdxW.lua", "sha256": "a" * 64, "nickname": "<b>x</b>" * 10}
    entry = sanitize_index_entry(good, LOCATION)
    assert entry["version"] == 3 and len(entry["nickname"]) == 32
    assert sanitize_index_entry({**good, "lua_path": "library/TdxW/3/../../x.lua"}, LOCATION) is None
    assert sanitize_index_entry({**good, "lua_path": "library/TdxW/3/Other.lua"}, LOCATION) is None
    assert sanitize_index_entry({**good, "sha256": "zz"}, LOCATION) is None
    assert "email" not in entry
    assert (entry["category"], entry["risk"], entry["business_relevance"]) == ("", 0, 0)
    tagged = sanitize_index_entry({**good, "category": "Financial", "risk": 1, "business_relevance": 9}, LOCATION)
    assert (tagged["category"], tagged["risk"], tagged["business_relevance"]) == ("financial", 1, 0)
    assert sanitize_index_entry({**good, "category": "bogus"}, LOCATION)["category"] == ""
    with pytest.raises(SharingError):
        LibraryLocation(owner="bad/owner", repo="lib")


def test_contact_validation() -> None:
    assert normalize_nickname("  Yong   Li ") == "Yong Li"
    assert normalize_email(" a@b.co ") == "a@b.co"
    for bad in ["", "x" * 33, "<script>"]:
        with pytest.raises(SharingError):
            normalize_nickname(bad)
    with pytest.raises(SharingError):
        normalize_email("not-an-email")


def test_distributed_program_has_no_maintainer_or_github_write_code(tmp_path: Path, monkeypatch) -> None:
    share = (TEMPLATE_DIR / "share.html").read_text(encoding="utf-8")
    assert "github_pat" not in share and "/api/maintainer" not in share and "type=\"password\"" not in share
    assert "maintainer_email" in share and "/api/share/submission" in share
    assert not (TEMPLATE_DIR / "maintainer.html").exists()
    package = Path(sharing.__file__).resolve().parents[1]
    for path in package.rglob("*"):
        if path.suffix in {".py", ".html", ".js"}:
            text = path.read_text(encoding="utf-8")
            for marker in ("api.github.com", "MaintainerPublisher", "maintainer_mode", "/api/maintainer", "purge.jsdelivr", "NGFW_LUA_MAINTAINER_TOKEN"):
                assert marker not in text, f"{marker} in {path.name}"
    assert "Authorization" not in Path(sharing.__file__).read_text(encoding="utf-8")
    app, _, _ = _app(tmp_path, monkeypatch)
    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/maintainer" not in paths and not any(p.startswith("/api/maintainer") for p in paths)
    for page in ("index.html", "fmc.html", "share.html"):
        assert 'href="/share"' in (TEMPLATE_DIR / page).read_text(encoding="utf-8")


def test_system_proxy_used_when_only_no_proxy_is_set(monkeypatch):
    monkeypatch.setattr(sharing.os, "name", "nt")
    monkeypatch.setattr(sharing.urllib.request, "getproxies_environment", lambda: {"no": "127.0.0.1"})
    monkeypatch.setattr(
        sharing.urllib.request,
        "getproxies_registry",
        lambda: {"http": "http://proxy:80", "https": "http://proxy:80", "ftp": "http://proxy:80"},
        raising=False,
    )
    assert sharing.system_proxies() == {"http": "http://proxy:80", "https": "http://proxy:80"}
    assert sharing.new_http_session().proxies["https"] == "http://proxy:80"


def test_explicit_proxy_env_wins_over_registry(monkeypatch):
    monkeypatch.setattr(sharing.os, "name", "nt")
    monkeypatch.setattr(sharing.urllib.request, "getproxies_environment", lambda: {"https": "http://env:3128"})
    assert sharing.system_proxies() == {}


def test_extracts_patterns_from_legacy_generator_tables():
    lua = '''DetectorPackageInfo = { name = "TdxW" }
local gTlsExactHosts = {
    "apprzfx.cmschina.com",
    "xg.cmschina.com",
}
local gTlsCertCNs = {
}
local gTlsHostSuffixes = {     -- matched as ".example.com"-style suffix
    ".cmschina.com",
}
local gHttpHosts = {
    "apprzfx.cmschina.com",
}
'''
    assert extract_host_patterns(lua) == ["apprzfx.cmschina.com", "xg.cmschina.com", ".cmschina.com"]
    name, data, _ = build_submission(
        app_name="TdxW", lua_bytes=lua.encode(), nickname="Alice", email="alice@example.com",
        fmc_version="7.4", notes="", tool_version=__version__, category="financial",
    )
    assert json.loads(zipfile.ZipFile(io.BytesIO(data)).read("submission.json"))["host_patterns"] == [
        "apprzfx.cmschina.com", "xg.cmschina.com", ".cmschina.com",
    ]


class _FakeImporter:
    def __init__(self) -> None:
        self.specs: list[Any] = []

    def connect(self) -> None:
        pass

    def import_detector(self, spec: Any) -> dict[str, Any]:
        self.specs.append(spec)
        return {"status": "imported", "message": "imported (Inactive)", "category": spec.category}


def test_import_to_fmc_uses_library_lua_and_metadata(tmp_path: Path, monkeypatch) -> None:
    from ngfw_appdetector.web.server import ShareImportItem, ShareImportRequest

    app, _, fake = _app(tmp_path, monkeypatch)
    _publish(fake, 1)
    _publish(fake, 2, lua=LUA + b"-- v2\n")
    index = json.loads(fake.files["library/index.json"])
    index["entries"][1].update(category="financial", risk=1, business_relevance=5)
    fake.files["library/index.json"] = json.dumps(index).encode()
    fake.snapshots[fake.head] = dict(fake.files)
    importer = _FakeImporter()
    app.state.fmc_importer_factory = lambda: importer
    _endpoint(app, "/api/share/library")(refresh=True)

    result = _endpoint(app, "/api/share/import-fmc", "POST")(ShareImportRequest(items=[
        ShareImportItem(app_name="TdxW", version=2), ShareImportItem(app_name="TdxW", version=1),
    ]))
    assert [r["status"] for r in result["results"]] == ["imported", "skipped"]
    spec = importer.specs[0]
    assert spec.lua == LUA + b"-- v2\n" and (spec.category, spec.risk, spec.business_relevance) == ("financial", 1, 5)
    assert "v2" in spec.description

    importer.specs.clear()
    result = _endpoint(app, "/api/share/import-fmc", "POST")(ShareImportRequest(items=[ShareImportItem(app_name="TdxW", version=1)]))
    assert result["results"][0]["status"] == "imported"
    assert (importer.specs[0].category, importer.specs[0].risk, importer.specs[0].business_relevance) == ("others", 2, 3)

    fake.snapshots[fake.head]["library/TdxW/1/TdxW.lua"] = LUA + b"-- tampered"
    result = _endpoint(app, "/api/share/import-fmc", "POST")(ShareImportRequest(items=[ShareImportItem(app_name="TdxW", version=1)]))
    assert result["results"][0]["status"] == "error" and "SHA256" in result["results"][0]["message"]


def test_import_to_fmc_reports_login_failure(tmp_path: Path, monkeypatch) -> None:
    from ngfw_appdetector.web.server import ShareImportItem, ShareImportRequest

    app, _, _ = _app(tmp_path, monkeypatch)

    def broken():
        raise RuntimeError("bad password")
    app.state.fmc_importer_factory = broken
    with pytest.raises(HTTPException) as e:
        _endpoint(app, "/api/share/import-fmc", "POST")(ShareImportRequest(items=[ShareImportItem(app_name="TdxW", version=1)]))
    assert e.value.status_code == 502
