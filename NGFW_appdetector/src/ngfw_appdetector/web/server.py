"""FastAPI app exposing the capture session over HTTP + SSE for the HTMX UI."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .. import __version__
from ..config import AppConfig, FmcConfig, save_fmc_section
from .session import CaptureSession
from .sharing import (
    APP_NAME_RE,
    DEFAULT_CATEGORY,
    DEFAULT_RELEVANCE,
    DEFAULT_RISK,
    FMC_CATEGORIES,
    LibraryLocation,
    SharingError,
    SharingStore,
    build_submission,
)

log = logging.getLogger(__name__)

PKG_DIR = Path(__file__).parent
TEMPLATE_DIR = PKG_DIR / "templates"
STATIC_DIR = PKG_DIR / "static"

PASSWORD_PLACEHOLDER = "********"


def _serialize_ngfw_event(event: Any) -> Dict[str, Any]:
    extras = event.extras

    def extra(*names: str) -> Any:
        for name in names:
            value = extras.get(name)
            if value not in (None, ""):
                return value
        return ""

    five_tuple = event.five_tuple
    return {
        "time": event.timestamp.isoformat(),
        "src": f"{five_tuple.src_ip}:{five_tuple.src_port}",
        "dst": f"{five_tuple.dst_ip}:{five_tuple.dst_port}",
        "proto": five_tuple.proto,
        "web_app": event.web_application or "",
        "app_name": (
            event.web_application
            or event.application_protocol
            or event.client_application
            or ""
        ),
        "action": extra("fw_rule_action"),
        "rule": extra("fw_rule_name"),
        "policy": extra("fw_policy"),
        "sensor": extra("sensor"),
        "event_id": event.event_id,
        "bytes_sent": extra("bytes_sent"),
        "bytes_recv": extra("bytes_recv"),
        "tls_fingerprint": extra("tlsfp_fingerprint"),
        "user_agent": event.http_user_agent or extra("userAgent"),
        "referer": event.http_referrer or extra("httpReferrer"),
        "host": (
            event.tls_sni
            or event.http_host
            or event.tls_cname
            or extra("referenced_host", "host", "sni")
        ),
        "web_app_tags": extra("web_app_tags"),
        "detection_type": extra("detection_type"),
        "info": event.http_uri or extra("info"),
    }


class StartRequest(BaseModel):
    exclude_host: list[str] = []
    process_name: Optional[str] = None


class FmcConfigUpdate(BaseModel):
    host: str
    username: str
    password: str = ""  # empty / placeholder = keep existing
    verify_tls: bool = False
    domain_uuid: Optional[str] = None
    poll_interval_sec: int = 10
    poll_lookback_sec: int = 60
    persist: bool = False  # also write to config.yaml


class FmcSearchRequest(BaseModel):
    src: Optional[str] = None
    dst: Optional[str] = None
    sport: Optional[int] = None
    dport: Optional[int] = None
    web_app: Optional[str] = None
    proto: str = "tcp"
    since_sec: int = 3600  # lookback window in seconds
    limit: int = 100


class GenerateRequest(BaseModel):
    app_name: str = Field(min_length=1, max_length=15, pattern=r"^[A-Za-z_]+$")
    exclude_hosts: list[str] = Field(default_factory=list)
    acknowledged_history_hosts: list[str] = Field(default_factory=list)


class ShareSubmissionRequest(BaseModel):
    lua_name: str = Field(pattern=r"^[A-Za-z_]{1,15}\.lua$")
    nickname: str = Field(min_length=1, max_length=64)
    email: str = Field(min_length=3, max_length=320)
    notes: str = Field(default="", max_length=2000)
    fmc_version: str = Field(default="", max_length=64)
    category: str = Field(min_length=1, max_length=64)
    risk: int = Field(default=DEFAULT_RISK, ge=1, le=5)
    business_relevance: int = Field(default=DEFAULT_RELEVANCE, ge=1, le=5)


class ShareImportItem(BaseModel):
    app_name: str = Field(pattern=r"^[A-Za-z_]{1,15}$")
    version: int = Field(ge=1, le=9999)


class ShareImportRequest(BaseModel):
    items: list[ShareImportItem] = Field(min_length=1, max_length=200)


def _parse_since(text: Union[str, int]) -> int:
    if isinstance(text, int):
        return text
    s = str(text).strip().lower()
    if s and s[-1] in "smhd":
        return int(s[:-1]) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[s[-1]]
    return int(s)


def create_app(
    cfg: AppConfig, output_dir: Path, config_path: Optional[Path] = None
) -> FastAPI:
    output_dir.mkdir(parents=True, exist_ok=True)
    cdn_history_path = output_dir / "cdn_history.json"
    session = CaptureSession(cfg=cfg, output_dir=output_dir)
    share_cfg = cfg.sharing
    sharing = SharingStore(
        output_dir / "sharing_settings.json",
        LibraryLocation(
            owner=share_cfg.github_owner,
            repo=share_cfg.github_repo,
            branch=share_cfg.branch,
            directory=share_cfg.library_dir,
            mirror_fallback=share_cfg.mirror_fallback,
        ),
    )
    templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
    # Changes on every upgrade so browsers never keep a stale app.js / app.css.
    asset_stamp = max(int(f.stat().st_mtime) for f in STATIC_DIR.glob("app.*"))
    templates.env.globals["asset_version"] = f"{__version__}-{asset_stamp}"

    app = FastAPI(title="NGFW App Detector", version=__version__)
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    def load_cdn_history() -> dict[str, dict[str, Any]]:
        if not cdn_history_path.exists():
            return {}
        data = json.loads(cdn_history_path.read_text(encoding="utf-8"))
        hosts = data.get("hosts")
        if not isinstance(hosts, dict):
            raise ValueError("cdn_history.json must contain a hosts object")
        return hosts

    def record_cdn_hosts(hosts: list[str]) -> None:
        history = load_cdn_history()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for host in hosts:
            key = host.strip().casefold()
            if not key:
                continue
            previous = history.get(key, {})
            history[key] = {
                "value": host.strip(),
                "selection_count": int(previous.get("selection_count", 0)) + 1,
                "last_selected_at": now,
            }
        payload = {"version": 1, "hosts": history}
        temporary = cdn_history_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        temporary.replace(cdn_history_path)

    # ── pages ──────────────────────────────────────────────────────────────
    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> Any:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"cfg": cfg, "output_dir": str(output_dir), "app_version": __version__},
        )

    @app.get("/fmc", response_class=HTMLResponse)
    def fmc_page(request: Request) -> Any:
        return templates.TemplateResponse(
            request=request,
            name="fmc.html",
            context={"cfg": cfg, "output_dir": str(output_dir)},
        )

    @app.get("/share", response_class=HTMLResponse)
    def share_page(request: Request) -> Any:
        return templates.TemplateResponse(
            request=request,
            name="share.html",
            context={
                "app_version": __version__,
                "maintainer_email": share_cfg.maintainer_email,
                "library_url": sharing.location.repo_url,
                "fmc_categories": list(FMC_CATEGORIES),
                "default_category": DEFAULT_CATEGORY,
                "fmc_host": cfg.fmc.host if cfg.fmc.host != "fmc.example.local" else "",
            },
        )

    # ── REST ───────────────────────────────────────────────────────────────
    @app.get("/api/status")
    def api_status() -> Dict[str, Any]:
        return session.snapshot()

    @app.post("/api/run/start")
    def api_start(body: StartRequest) -> Dict[str, Any]:
        try:
            session.start(
                exclude_host=body.exclude_host,
                process_name=body.process_name,
            )
        except RuntimeError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except Exception as e:
            log.exception("start failed")
            raise HTTPException(status_code=500, detail=str(e))
        return session.snapshot()

    @app.get("/api/processes")
    def api_processes() -> List[Dict[str, Union[int, str]]]:
        if sys.platform == "win32":
            from .process_candidates_windows import (
                discover_windows_socket_process_counts,
                running_process_name_candidates,
            )

            counts = discover_windows_socket_process_counts()
        else:
            from .process_candidates_mac import (
                discover_mac_socket_process_counts,
                running_process_name_candidates,
            )

            counts = discover_mac_socket_process_counts()
        candidates = {
            str(item["process_name"]): item for item in running_process_name_candidates()
        }
        for name, count in counts.items():
            candidates[name] = {"process_name": name, "connections": count}
        return sorted(
            candidates.values(),
            key=lambda item: (-int(item["connections"]), str(item["process_name"]).casefold()),
        )

    @app.post("/api/run/stop")
    def api_stop() -> dict[str, Any]:
        session.stop()
        return session.snapshot()

    # ── FMC config ─────────────────────────────────────────────────────────
    @app.get("/api/config/fmc")
    def api_get_fmc() -> Dict[str, Any]:
        f = cfg.fmc
        return {
            "host": f.host,
            "username": f.username,
            "password_set": bool(f.password and f.password != "REPLACE_ME"),
            "verify_tls": f.verify_tls,
            "domain_uuid": f.domain_uuid,
            "poll_interval_sec": f.poll_interval_sec,
            "poll_lookback_sec": f.poll_lookback_sec,
            "config_path": str(config_path) if config_path else None,
        }

    @app.post("/api/config/fmc")
    def api_set_fmc(body: FmcConfigUpdate) -> Dict[str, Any]:
        # Empty or placeholder password → keep existing
        new_password = body.password
        if not new_password or new_password == PASSWORD_PLACEHOLDER:
            new_password = cfg.fmc.password
        cfg.fmc = FmcConfig(
            host=body.host.strip(),
            username=body.username.strip(),
            password=new_password,
            verify_tls=body.verify_tls,
            domain_uuid=(body.domain_uuid or None),
            poll_interval_sec=body.poll_interval_sec,
            poll_lookback_sec=body.poll_lookback_sec,
        )
        persisted = False
        if body.persist:
            target = config_path or Path("config.yaml")
            try:
                save_fmc_section(target, cfg.fmc)
                persisted = True
            except Exception as e:
                log.exception("save_fmc_section failed")
                raise HTTPException(status_code=500, detail=f"save failed: {e}")
        return {"ok": True, "persisted": persisted, "path": str(config_path) if config_path else None}

    @app.post("/api/fmc/test")
    def api_fmc_test() -> Dict[str, Any]:
        from ..ngfw_collector import FmcUiClient
        f = cfg.fmc
        if not f.host or f.host == "fmc.example.local":
            raise HTTPException(status_code=400, detail="FMC host not configured")
        if not f.password or f.password == "REPLACE_ME":
            raise HTTPException(status_code=400, detail="FMC password not set")
        client = FmcUiClient(
            host=f.host, username=f.username, password=f.password,
            verify_tls=f.verify_tls, timeout=15,
        )
        try:
            client.login()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"login failed: {e}")
        return {
            "ok": True,
            "host": f.host,
            "message": f"Authenticated to {f.host} connection-events UI",
        }

    # Cached UI-scrape client (one cookie session, re-login on 403).
    _ui_state: dict[str, Any] = {"client": None, "host": None, "user": None}

    def _get_ui_client():
        from ..ngfw_collector import FmcUiClient
        f = cfg.fmc
        if not f.host or f.host == "fmc.example.local":
            raise HTTPException(status_code=400, detail="FMC host not configured")
        if not f.password or f.password == "REPLACE_ME":
            raise HTTPException(status_code=400, detail="FMC password not set")
        cached = _ui_state["client"]
        if cached and _ui_state["host"] == f.host and _ui_state["user"] == f.username:
            return cached
        client = FmcUiClient(
            host=f.host, username=f.username, password=f.password,
            verify_tls=f.verify_tls, timeout=20,
        )
        client.login()
        _ui_state.update({"client": client, "host": f.host, "user": f.username})
        return client

    @app.post("/api/fmc/search")
    def api_fmc_search(body: FmcSearchRequest) -> Dict[str, Any]:
        from ..ngfw_collector.poller import _to_ngfw_event
        from ..ngfw_collector.ui_source import _flatten

        client = _get_ui_client()
        end = client.server_now_epoch()
        start = end - max(int(body.since_sec), 1)
        try:
            constraints = client.build_tuple_constraints(
                src_ip=body.src or None,
                dst_ip=body.dst or None,
                src_port=body.sport,
                dst_port=body.dport,
                protocol=body.proto or "tcp",
                web_app=(body.web_app or "").strip() or None,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"bad filter: {e}")
        try:
            rows = client.fetch_events(
                start, end, constraints=constraints, limit=max(1, min(body.limit, 1000)),
            )
        except Exception as e:
            log.exception("fmc search failed")
            # Drop cache so next attempt re-logs in.
            _ui_state["client"] = None
            raise HTTPException(status_code=502, detail=f"search failed: {e}")

        out_rows: List[Dict[str, Any]] = []
        for r in rows:
            flat = _flatten(r)
            evt = _to_ngfw_event(flat)
            if evt:
                out_rows.append(_serialize_ngfw_event(evt))
            else:
                out_rows.append({
                    "time": None, "src": f"{flat.get('src_ip')}:{flat.get('src_port')}",
                    "dst": f"{flat.get('dst_ip')}:{flat.get('dst_port')}",
                    "proto": flat.get("protocol") or "?",
                    "web_app": "", "rule": flat.get("fw_rule_name") or "",
                    "policy": flat.get("fw_policy") or "",
                    "sensor": flat.get("sensor") or "",
                    "event_id": flat.get("id") or "",
                    "_unparsed": True,
                    "action": flat.get("fw_rule_action") or "",
                    "bytes_sent": flat.get("bytes_sent") or "",
                    "bytes_recv": flat.get("bytes_recv") or "",
                    "tls_fingerprint": flat.get("tlsfp_fingerprint") or "",
                    "user_agent": flat.get("userAgent") or "",
                    "referer": flat.get("httpReferrer") or "",
                    "host": flat.get("referenced_host") or "",
                    "web_app_tags": flat.get("web_app_tags") or "",
                    "detection_type": flat.get("detection_type") or "",
                    "info": flat.get("info") or "",
                })
        return {
            "count": len(out_rows),
            "start": start,
            "end": end,
            "constraints": constraints,
            "rows": out_rows,
        }

    @app.get("/api/flows")
    def api_flows(limit: int = 100) -> List[Dict[str, Any]]:
        sample_map: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
        for sample in session.samples(limit=1000):
            key = sample.local.five_tuple.key(directional=False)
            sample_map.setdefault(key, []).append(_serialize_ngfw_event(sample.ngfw))

        rows: List[Dict[str, Any]] = []
        for flow in session.flows(limit=limit):
            key = flow.five_tuple.key(directional=False)
            rows.append({
                "process_name": flow.process_name,
                "pid": flow.pid,
                "proto": flow.five_tuple.proto,
                "src": f"{flow.five_tuple.src_ip}:{flow.five_tuple.src_port}",
                "dst": f"{flow.five_tuple.dst_ip}:{flow.five_tuple.dst_port}",
                "first_seen": flow.first_seen.isoformat(),
                "last_seen": flow.last_seen.isoformat(),
                "correlations": sample_map.get(key, []),
            })
        return rows

    @app.get("/api/samples")
    def api_samples(limit: int = 100) -> List[Dict[str, Any]]:
        return [
            {
                "process_name": s.local.process_name,
                "src": f"{s.local.five_tuple.src_ip}:{s.local.five_tuple.src_port}",
                "dst": f"{s.local.five_tuple.dst_ip}:{s.local.five_tuple.dst_port}",
                "proto": s.local.five_tuple.proto,
                "tls_sni": s.ngfw.tls_sni,
                "http_host": s.ngfw.http_host,
                "app_name_ngfw": (
                    s.ngfw.web_application
                    or s.ngfw.application_protocol
                    or s.ngfw.client_application
                ),
                "matched_at": s.ngfw.timestamp.isoformat(),
            }
            for s in session.samples(limit=limit)
        ]

    @app.get("/api/fingerprints")
    def api_fingerprints() -> Dict[str, Any]:
        data = session.fingerprints()
        def serialize(fp: Any) -> dict[str, Any]:
            return {
                "app_name": fp.app_name,
                "sample_count": fp.sample_count,
                "tls_snis": fp.tls_snis,
                "tls_host_suffixes": fp.tls_host_suffixes,
                "http_hosts": fp.http_hosts,
                "http_uri_prefixes": fp.http_uri_prefixes,
                "http_user_agents": fp.http_user_agents,
                "dst_ports": fp.dst_ports,
            }
        return {
            "ready": [serialize(fp) for fp in data["ready"]],
            "all": [serialize(fp) for fp in data["all"]],
        }

    @app.get("/api/generation-signals")
    def api_generation_signals() -> Dict[str, Any]:
        try:
            history = load_cdn_history()
        except (OSError, ValueError, json.JSONDecodeError) as e:
            log.exception("Failed to read CDN history")
            raise HTTPException(status_code=500, detail=f"CDN history read failed: {e}")
        signals = session.generation_signals()
        return {
            "signals": [
                {
                    **signal,
                    "historical_cdn": signal["value"].casefold() in history,
                }
                for signal in signals
            ],
            "history_count": len(history),
        }

    @app.post("/api/generate")
    def api_generate(body: GenerateRequest) -> Dict[str, Any]:
        snapshot = session.snapshot()
        if snapshot["state"] == "running":
            raise HTTPException(
                status_code=409,
                detail={"code": "capture_running"},
            )
        if snapshot["state"] == "draining":
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "fmc_draining",
                    "remaining": snapshot["drain_remaining_sec"],
                },
            )
        fingerprints = session.fingerprints()
        if not fingerprints["ready"]:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "not_ready",
                    "min_samples": cfg.generator.min_samples,
                    "candidates": len(fingerprints["all"]),
                },
            )
        candidate_values = {
            signal["value"].casefold(): signal["value"]
            for signal in session.generation_signals()
        }
        excluded = {
            value.strip().casefold()
            for value in body.exclude_hosts
            if value.strip().casefold() in candidate_values
        }
        acknowledged = {
            value.strip().casefold()
            for value in body.acknowledged_history_hosts
        }
        try:
            history = load_cdn_history()
        except (OSError, ValueError, json.JSONDecodeError) as e:
            log.exception("Failed to read CDN history")
            raise HTTPException(status_code=500, detail=f"CDN history read failed: {e}")
        historical_warnings = sorted(
            (
                candidate_values[value]
                for value in set(history).intersection(candidate_values)
                if value not in excluded and value not in acknowledged
            ),
            key=str.casefold,
        )
        if historical_warnings:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "cdn_history_warning",
                    "hosts": historical_warnings,
                },
            )
        selected_hosts = sorted(
            (candidate_values[value] for value in excluded),
            key=str.casefold,
        )
        try:
            paths = session.generate_lua(
                app_name=body.app_name,
                exclude_hosts=selected_hosts,
            )
        except Exception as e:
            log.exception("Lua generation failed")
            raise HTTPException(status_code=500, detail=f"Lua generation failed: {e}")
        if not paths:
            raise HTTPException(
                status_code=409,
                detail={"code": "no_signals_after_exclusion"},
            )
        try:
            record_cdn_hosts(selected_hosts)
        except (OSError, ValueError, json.JSONDecodeError) as e:
            log.exception("Failed to save CDN history")
            raise HTTPException(status_code=500, detail=f"CDN history save failed: {e}")
        return {"count": len(paths), "files": [p.name for p in paths]}

    @app.get("/api/lua")
    def api_list_lua() -> list[str]:
        if not output_dir.exists():
            return []
        return sorted(p.name for p in output_dir.glob("*.lua"))

    @app.get("/api/lua/{name}")
    def api_get_lua(name: str) -> Any:
        # Prevent path traversal.
        if "/" in name or ".." in name or not name.endswith(".lua"):
            raise HTTPException(status_code=400, detail="invalid name")
        path = output_dir / name
        if not path.exists():
            raise HTTPException(status_code=404)
        return FileResponse(path, media_type="text/plain", filename=name)

    # ── Shared Lua library (read-only for everyone) ───────────────────────
    def lookup(app_name: str, version: int) -> tuple[bytes, Dict[str, Any], bool]:
        if not APP_NAME_RE.match(app_name) or not 1 <= version <= 9999:
            raise HTTPException(status_code=400, detail="invalid detector reference")
        try:
            return sharing.client.read_lua(app_name, version)
        except SharingError as e:
            raise HTTPException(status_code=502, detail=str(e))

    @app.get("/api/share/library")
    def api_share_library(refresh: bool = False) -> Dict[str, Any]:
        try:
            entries, source = sharing.client.entries(force=refresh)
        except SharingError as e:
            raise HTTPException(status_code=502, detail=str(e))
        return {"entries": entries, "source": source}

    @app.get("/api/share/lua")
    def api_share_lua(app_name: str, version: int) -> Dict[str, Any]:
        data, entry, verified = lookup(app_name, version)
        return {"content": data.decode("utf-8", errors="replace"), "verified": verified, "entry": entry}

    @app.get("/api/share/lua/download")
    def api_share_lua_download(app_name: str, version: int) -> Response:
        data, entry, verified = lookup(app_name, version)
        if not verified:
            raise HTTPException(status_code=409, detail="SHA256 mismatch; download refused")
        return Response(
            content=data,
            media_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="{entry["app_name"]}.lua"'},
        )

    @app.get("/api/share/submitter")
    def api_share_submitter() -> Dict[str, Any]:
        return sharing.load()

    def default_importer_factory() -> Any:
        from ..ngfw_collector.fmc_import import FmcDetectorImporter

        client = _get_ui_client()
        return FmcDetectorImporter(base=client.base, session=client.http_session, relogin=client.login)

    app.state.fmc_importer_factory = default_importer_factory
    import_lock = threading.Lock()

    @app.post("/api/share/import-fmc")
    def api_share_import_fmc(body: ShareImportRequest) -> Dict[str, Any]:
        from ..ngfw_collector.fmc_import import DetectorSpec, FmcImportError

        if not import_lock.acquire(blocking=False):
            raise HTTPException(status_code=409, detail="an FMC import is already running")
        try:
            try:
                importer = app.state.fmc_importer_factory()
                importer.connect()
            except HTTPException:
                raise
            except Exception as e:
                log.exception("FMC import login failed")
                raise HTTPException(status_code=502, detail=f"FMC login failed: {e}")
            results: list[Dict[str, Any]] = []
            seen: set[str] = set()
            for item in body.items:
                result: Dict[str, Any] = {"app_name": item.app_name, "version": item.version}
                results.append(result)
                if item.app_name.casefold() in seen:
                    result.update(status="skipped", message="another version of this application is already selected")
                    continue
                seen.add(item.app_name.casefold())
                try:
                    data, entry, verified = sharing.client.read_lua(item.app_name, item.version)
                    if not verified:
                        raise SharingError("SHA256 mismatch; import refused")
                    result.update(importer.import_detector(DetectorSpec(
                        app_name=entry["app_name"],
                        lua=data,
                        description=f"NGFW shared Lua library v{entry['version']} ({entry['nickname']})"[:200],
                        category=entry.get("category") or DEFAULT_CATEGORY,
                        risk=entry.get("risk") or DEFAULT_RISK,
                        business_relevance=entry.get("business_relevance") or DEFAULT_RELEVANCE,
                    )))
                except (SharingError, FmcImportError, requests.RequestException) as e:
                    result.update(status="error", message=str(e))
                except Exception as e:
                    log.exception("FMC import of %s failed", item.app_name)
                    result.update(status="error", message=f"{e.__class__.__name__}: {e}")
            return {"fmc_host": cfg.fmc.host, "results": results}
        finally:
            import_lock.release()

    @app.post("/api/share/submission")
    def api_share_submission(body: ShareSubmissionRequest) -> Dict[str, Any]:
        path = output_dir / body.lua_name
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Lua file not found")
        try:
            filename, data, manifest = build_submission(
                app_name=body.lua_name[:-4],
                lua_bytes=path.read_bytes(),
                nickname=body.nickname,
                email=body.email,
                fmc_version=body.fmc_version,
                notes=body.notes,
                tool_version=__version__,
                category=body.category,
                risk=body.risk,
                business_relevance=body.business_relevance,
            )
        except SharingError as e:
            raise HTTPException(status_code=400, detail=str(e))
        submitter = manifest["submitter"]
        sharing.remember_submitter(submitter["nickname"], submitter["email"])
        saved = output_dir / "submissions" / filename
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_bytes(data)
        return {
            "filename": filename,
            "saved_path": str(saved.resolve()),
            "zip_b64": base64.b64encode(data).decode("ascii"),
            "maintainer_email": share_cfg.maintainer_email,
            "manifest": manifest,
        }

    # ── SSE: live status stream for the UI to auto-refresh ─────────────────
    @app.get("/api/events")
    async def api_events(request: Request) -> StreamingResponse:
        async def gen():
            while True:
                if await request.is_disconnected():
                    break
                payload = json.dumps(session.snapshot())
                yield f"data: {payload}\n\n"
                await asyncio.sleep(1.0)
        return StreamingResponse(gen(), media_type="text/event-stream")

    @app.get("/healthz")
    def healthz() -> Dict[str, str]:
        return {"status": "ok"}

    # Expose for tests / introspection.
    app.state.session = session
    app.state.cfg = cfg
    app.state.sharing = sharing
    return app
