"""Typer-based CLI entry point."""

from __future__ import annotations

import json
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from .config import AppConfig, load_config
from .correlator import Correlator
from .flow_monitor import SocketFlowSource
from .logbook import write_flows_jsonl, write_proc_snapshot_jsonl
from .lua_generator import FingerprintAggregator, LuaRenderer
from .models import CorrelatedSample, FiveTuple, LocalFlow, NgfwEvent
from .ngfw_collector import EventPoller, FmcClient, FmcUiClient, FmcUiEventPoller, MockEventPoller
from .ngfw_collector.ui_source import _flatten
from .ngfw_collector.poller import _to_ngfw_event

app = typer.Typer(
    help="Local automated Cisco NGFW LUA app detector generator.",
    no_args_is_help=True,
)
console = Console()


def _setup_logging(cfg: AppConfig) -> None:
    level = getattr(logging, cfg.logging.level.upper(), logging.INFO)
    handlers: list[logging.Handler] = [RichHandler(console=console, show_path=False)]
    if cfg.logging.file:
        handlers.append(logging.FileHandler(cfg.logging.file))
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=handlers,
        force=True,
    )


def _load(config_path: Optional[Path]) -> AppConfig:
    cfg = load_config(config_path)
    _setup_logging(cfg)
    return cfg


# ── commands ────────────────────────────────────────────────────────────────


@app.command("fmc-test")
def fmc_test(
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config.yaml"),
) -> None:
    """Verify FMC credentials and list one page of connection events."""
    cfg = _load(config)
    client = FmcClient(
        host=cfg.fmc.host,
        username=cfg.fmc.username,
        password=cfg.fmc.password,
        verify_tls=cfg.fmc.verify_tls,
    )
    if cfg.fmc.domain_uuid:
        client.set_domain_uuid(cfg.fmc.domain_uuid)
    client.login()
    console.print(f"[green]Authenticated.[/] domain_uuid={client.domain_uuid}")
    end = int(time.time())
    start = end - cfg.fmc.poll_lookback_sec
    try:
        page = client.list_connection_events(start, end, limit=5)
    except Exception as e:
        console.print(f"[red]Connection event query failed:[/] {e}")
        raise typer.Exit(1)
    items = page.get("items") or page.get("events") or []
    console.print(f"Got {len(items)} event(s) in last {cfg.fmc.poll_lookback_sec}s")
    for it in items[:5]:
        console.print_json(data=it)


def _parse_since(s: str) -> int:
    """Parse '90s', '15m', '2h', '1d' or a bare integer (seconds)."""
    s = s.strip().lower()
    if s[-1:] in "smhd":
        n, unit = int(s[:-1]), s[-1]
        return n * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
    return int(s)


@app.command("fmc-search")
def fmc_search(
    src: Optional[str] = typer.Option(None, "--src", help="Source IP filter"),
    dst: Optional[str] = typer.Option(None, "--dst", help="Destination IP filter"),
    sport: Optional[int] = typer.Option(None, "--sport", help="Source port filter"),
    dport: Optional[int] = typer.Option(None, "--dport", help="Destination port filter"),
    proto: str = typer.Option("tcp", "--proto", help="Protocol for port filters (tcp|udp)"),
    since: str = typer.Option("1h", "--since", help="Lookback window: e.g. 90s, 15m, 2h, 1d"),
    limit: int = typer.Option(50, "--limit", help="Max rows to fetch"),
    raw: bool = typer.Option(False, "--raw", help="Print raw JSON rows instead of a table"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    """Ad-hoc search of FMC connection events via the Web UI endpoint."""
    cfg = _load(config)
    ui = FmcUiClient(
        host=cfg.fmc.host,
        username=cfg.fmc.username,
        password=cfg.fmc.password,
        verify_tls=cfg.fmc.verify_tls,
    )
    ui.login()

    end = int(time.time())
    start = end - _parse_since(since)
    constraints = ui.build_tuple_constraints(
        src_ip=src, dst_ip=dst, src_port=sport, dst_port=dport, protocol=proto,
    )
    console.print(
        f"[dim]window={since} start={start} end={end} "
        f"constraints={constraints or '(none)'} limit={limit}[/]"
    )
    rows = ui.fetch_events(start, end, constraints=constraints, limit=limit)
    console.print(f"[green]Got {len(rows)} row(s)[/]")

    if raw:
        for r in rows:
            console.print_json(data=r)
        return

    table = Table(title=f"FMC events ({len(rows)})")
    for col in ("Time (UTC)", "Src", "Dst", "Proto", "Web app", "Rule", "Policy"):
        table.add_column(col, overflow="fold")
    for r in rows:
        flat = _flatten(r)
        evt = _to_ngfw_event(flat)
        if not evt:
            continue
        ft = evt.five_tuple
        table.add_row(
            evt.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            f"{ft.src_ip}:{ft.src_port}",
            f"{ft.dst_ip}:{ft.dst_port}",
            ft.proto,
            evt.web_application or "",
            (flat.get("fw_rule_name") or "")[:32],
            (flat.get("fw_policy") or "")[:40],
        )
    console.print(table)


@app.command("run")
def run_pipeline(
    duration: int = typer.Option(60, "--duration", "-d", help="Run duration in seconds"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
    samples_out: Optional[Path] = typer.Option(
        None, "--samples-out", help="Write correlated samples as JSONL"
    ),
    generate: bool = typer.Option(True, "--generate/--no-generate", help="Render LUA at the end"),
    mock_fmc: Optional[Path] = typer.Option(
        None, "--mock-fmc", help="Replay NGFW events from a JSONL fixture instead of calling FMC"
    ),
    mock_mode: str = typer.Option(
        "burst", "--mock-mode", help="burst | realtime (only with --mock-fmc)"
    ),
    exclude_host: list[str] = typer.Option(
        [], "--exclude-host", help="Hostnames to never claim (repeatable)"
    ),
    flows_out: Optional[Path] = typer.Option(
        None, "--flows-out", help="Write every observed local flow (with process info) as JSONL"
    ),
    proc_snapshot_out: Optional[Path] = typer.Option(
        None, "--proc-snapshot-out",
        help="On exit, dump the proc-tracker socket-table cache as JSONL",
    ),
) -> None:
    """End-to-end: discover local flows + poll FMC (or replay fixture) + correlate + render LUA."""
    cfg = _load(config)

    aggregator = FingerprintAggregator(
        min_samples=cfg.generator.min_samples,
        excluded_hosts=exclude_host,
    )
    samples: list[CorrelatedSample] = []
    local_flows: dict[tuple, LocalFlow] = {}

    def on_match(s: CorrelatedSample) -> None:
        samples.append(s)
        aggregator.add(s)
        console.log(
            f"[cyan]MATCH[/] proc={s.local.process_name} "
            f"{s.local.five_tuple.src_ip}:{s.local.five_tuple.src_port}→"
            f"{s.local.five_tuple.dst_ip}:{s.local.five_tuple.dst_port} "
            f"sni={s.ngfw.tls_sni} host={s.ngfw.http_host}"
        )

    correlator = Correlator(
        on_match=on_match,
        time_window_sec=cfg.correlator.time_window_sec,
        direction=cfg.correlator.match_direction,
    )

    def on_flow(fl: LocalFlow) -> None:
        local_flows[fl.five_tuple.key(directional=False)] = fl
        correlator.add_local(fl)

    socket_src = SocketFlowSource(
        on_flow=on_flow,
        proc_refresh_ms=cfg.capture.proc_refresh_ms,
    )

    poller: object
    if mock_fmc:
        poller = MockEventPoller(
            fixture=mock_fmc,
            on_event=correlator.add_ngfw,
            mode=mock_mode,
            retime=True,
        )
        fmc_label = f"mock:{mock_fmc.name}"
    else:
        ui = FmcUiClient(
            host=cfg.fmc.host,
            username=cfg.fmc.username,
            password=cfg.fmc.password,
            verify_tls=cfg.fmc.verify_tls,
        )
        ui.login()
        poller = FmcUiEventPoller(
            client=ui,
            on_event=correlator.add_ngfw,
            interval_sec=cfg.fmc.poll_interval_sec,
            lookback_sec=cfg.fmc.poll_lookback_sec,
        )
        fmc_label = f"{cfg.fmc.host} (ui-scrape)"

    # ── go ──
    socket_src.start()
    poller.start()  # type: ignore[attr-defined]
    console.print(f"[green]Running for {duration}s[/] fmc={fmc_label}")

    interrupted = {"v": False}

    def _on_sigint(signum, frame):  # noqa: ANN001
        interrupted["v"] = True

    signal.signal(signal.SIGINT, _on_sigint)
    end_at = time.time() + duration
    try:
        while time.time() < end_at and not interrupted["v"]:
            time.sleep(0.5)
    finally:
        poller.stop()  # type: ignore[attr-defined]
        socket_src.stop()

    console.print(f"\n[bold]Captured[/] {len(samples)} correlated samples, {len(local_flows)} local flow(s).")

    if flows_out:
        n = write_flows_jsonl(flows_out, local_flows.values())
        console.print(f"Wrote {n} local flow(s) → {flows_out}")

    if proc_snapshot_out:
        with socket_src.proc._lock:
            items = list(socket_src.proc._cache.items())
        n = write_proc_snapshot_jsonl(proc_snapshot_out, items)
        console.print(f"Wrote {n} proc-tracker cache entries → {proc_snapshot_out}")

    stats = socket_src.proc.stats()
    console.print(
        f"[dim]proc-tracker: {stats['hits']}/{stats['lookups']} cached, "
        f"+{stats['miss_refresh_hits']} via refresh, "
        f"+{stats['lsof_hits']} via lsof "
        f"(hit_rate={stats['hit_rate']:.0%}, cache={stats['cache_size']})[/]"
    )

    if samples_out:
        samples_out.parent.mkdir(parents=True, exist_ok=True)
        with samples_out.open("w") as f:
            for s in samples:
                f.write(s.model_dump_json() + "\n")
        console.print(f"Wrote samples → {samples_out}")

    if generate:
        renderer = LuaRenderer(cfg.generator.output_dir)
        written = 0
        for fp in aggregator.ready():
            renderer.render(fp)
            written += 1
        console.print(f"Generated {written} LUA detector(s) → {cfg.generator.output_dir}")


@app.command("generate")
def generate_only(
    input_file: Path = typer.Option(..., "--input", "-i", help="JSONL of CorrelatedSample"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
    output_dir: Optional[Path] = typer.Option(None, "--out", "-o"),
    exclude_host: list[str] = typer.Option(
        [], "--exclude-host", help="Hostnames to never claim (repeatable)"
    ),
) -> None:
    """Generate LUA from a previously-captured samples JSONL."""
    cfg = _load(config)
    out = output_dir or Path(cfg.generator.output_dir)
    agg = FingerprintAggregator(min_samples=cfg.generator.min_samples, excluded_hosts=exclude_host)

    with input_file.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            sample = CorrelatedSample.model_validate_json(line)
            agg.add(sample)

    renderer = LuaRenderer(out)
    table = Table(title="Generated detectors")
    table.add_column("App")
    table.add_column("Samples", justify="right")
    table.add_column("File")
    for fp in agg.ready():
        path = renderer.render(fp)
        table.add_row(fp.app_name, str(fp.sample_count), str(path))
    console.print(table)


@app.command("capture")
def capture_only(
    duration: int = typer.Option(30, "--duration", "-d"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
    flows_out: Optional[Path] = typer.Option(
        None, "--flows-out", help="Write every observed local flow as JSONL"
    ),
    proc_snapshot_out: Optional[Path] = typer.Option(
        None, "--proc-snapshot-out", help="Dump proc-tracker cache on exit as JSONL"
    ),
) -> None:
    """Observe local flows (no FMC) and print them. Uses socket-table polling — no root needed."""
    cfg = _load(config)

    seen: dict[tuple, LocalFlow] = {}

    def on_flow(f: LocalFlow) -> None:
        seen[f.five_tuple.key(directional=False)] = f

    socket_src = SocketFlowSource(
        on_flow=on_flow,
        proc_refresh_ms=cfg.capture.proc_refresh_ms,
    )

    socket_src.start()
    console.print(f"[green]Observing socket table for {duration}s…[/]")
    try:
        time.sleep(duration)
    except KeyboardInterrupt:
        pass
    finally:
        socket_src.stop()

    table = Table(title=f"Local flows ({len(seen)})")
    for col in ("Proc", "PID", "Proto", "Src", "Dst", "Bytes"):
        table.add_column(col)
    for f in list(seen.values())[:50]:
        table.add_row(
            f.process_name or "-",
            str(f.pid or "-"),
            f.five_tuple.proto,
            f"{f.five_tuple.src_ip}:{f.five_tuple.src_port}",
            f"{f.five_tuple.dst_ip}:{f.five_tuple.dst_port}",
            str(f.bytes_sent),
        )
    console.print(table)

    stats = socket_src.proc.stats()
    console.print(
        f"[dim]proc-tracker: {stats['hits']}/{stats['lookups']} cached, "
        f"+{stats['miss_refresh_hits']} via refresh, "
        f"+{stats['lsof_hits']} via lsof "
        f"(hit_rate={stats['hit_rate']:.0%}, cache={stats['cache_size']})[/]"
    )

    if flows_out:
        n = write_flows_jsonl(flows_out, seen.values())
        console.print(f"Wrote {n} local flow(s) → {flows_out}")
    if proc_snapshot_out:
        with socket_src.proc._lock:
            items = list(socket_src.proc._cache.items())
        n = write_proc_snapshot_jsonl(proc_snapshot_out, items)
        console.print(f"Wrote {n} proc-tracker cache entries → {proc_snapshot_out}")


@app.command("demo")
def demo(
    fixture: Path = typer.Option(
        Path("examples/mock_fmc_events.jsonl"),
        "--fixture",
        "-f",
        help="JSONL of mock FMC events",
    ),
    process_name: str = typer.Option(
        "WeirdApp", "--proc", help="Pretend this process produced the local flows"
    ),
    output_dir: Path = typer.Option(Path("./generated_detectors"), "--out", "-o"),
    min_samples: int = typer.Option(1, "--min-samples"),
    exclude_host: list[str] = typer.Option(
        [], "--exclude-host", help="Hostnames to never claim (repeatable)"
    ),
) -> None:
    """Fully offline end-to-end demo: no root, no FMC, no real traffic.

    Reads a mock FMC fixture, fabricates matching LocalFlows tagged with --proc,
    runs them through the correlator + LUA generator, and writes detectors.
    """
    cfg = _load(None)
    cfg.generator.min_samples = min_samples
    cfg.generator.output_dir = str(output_dir)

    aggregator = FingerprintAggregator(min_samples=min_samples, excluded_hosts=exclude_host)
    samples: list[CorrelatedSample] = []

    def on_match(s: CorrelatedSample) -> None:
        samples.append(s)
        aggregator.add(s)

    correlator = Correlator(on_match=on_match, time_window_sec=3600, direction="either")

    # Replay events; for each, fabricate a matching LocalFlow first.
    from .ngfw_collector.mock import _load_events

    events = _load_events(fixture, retime=True)
    for evt in events:
        flow = LocalFlow(
            five_tuple=evt.five_tuple,
            first_seen=evt.timestamp,
            last_seen=evt.timestamp,
            pid=4242,
            process_name=process_name,
            process_path=f"/Applications/{process_name}.app/Contents/MacOS/{process_name}",
        )
        correlator.add_local(flow)
        correlator.add_ngfw(evt)

    console.print(f"[bold]Demo:[/] {len(samples)} correlated samples")

    renderer = LuaRenderer(output_dir)
    table = Table(title="Generated detectors")
    table.add_column("App")
    table.add_column("Samples", justify="right")
    table.add_column("File")
    for fp in aggregator.ready():
        path = renderer.render(fp)
        table.add_row(fp.app_name, str(fp.sample_count), str(path))
    console.print(table)


@app.command("inspect")
def inspect(
    file: Path = typer.Argument(..., help="JSONL file written by --flows-out / --samples-out / --proc-snapshot-out"),
    proc: Optional[str] = typer.Option(None, "--proc", help="Filter by process name substring"),
    ip: Optional[str] = typer.Option(None, "--ip", help="Filter by IP (src or dst)"),
    port: Optional[int] = typer.Option(None, "--port", help="Filter by port (src or dst)"),
    proto: Optional[str] = typer.Option(None, "--proto", help="tcp | udp"),
    limit: int = typer.Option(50, "--limit", "-n"),
    raw: bool = typer.Option(False, "--raw", help="Print matching JSON lines verbatim"),
) -> None:
    """Query a JSONL log written by run / capture.

    Auto-detects record shape (LocalFlow, CorrelatedSample, proc-snapshot)."""
    _load(None)  # init logging only
    if not file.exists():
        console.print(f"[red]File not found:[/] {file}")
        raise typer.Exit(1)

    matches: list[dict] = []
    with file.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            flat = _flatten_record(rec)
            if proc and proc.lower() not in (flat.get("process_name") or "").lower():
                continue
            if proto and flat.get("proto") != proto.lower():
                continue
            if ip and ip not in (flat.get("src_ip"), flat.get("dst_ip"),
                                 flat.get("local_ip"), flat.get("remote_ip")):
                continue
            if port is not None and port not in (
                flat.get("src_port"), flat.get("dst_port"),
                flat.get("local_port"), flat.get("remote_port"),
            ):
                continue
            matches.append(flat if not raw else rec)
            if len(matches) >= limit:
                break

    console.print(f"[bold]{len(matches)}[/] record(s) matched (showing up to {limit})")
    if raw:
        for r in matches:
            console.print_json(data=r)
        return

    table = Table(show_lines=False)
    for col in ("Proc", "PID", "Proto", "Local", "Remote", "Extra"):
        table.add_column(col, overflow="fold")
    for r in matches:
        local = f"{r.get('src_ip') or r.get('local_ip') or '-'}:{r.get('src_port') or r.get('local_port') or '-'}"
        remote = f"{r.get('dst_ip') or r.get('remote_ip') or '-'}:{r.get('dst_port') or r.get('remote_port') or '-'}"
        extra = r.get("tls_sni") or r.get("http_host") or r.get("snapped_at") or ""
        table.add_row(
            str(r.get("process_name") or "-"),
            str(r.get("pid") or "-"),
            str(r.get("proto") or "-"),
            local,
            remote,
            str(extra),
        )
    console.print(table)


def _flatten_record(rec: dict) -> dict:
    """Project a LocalFlow / CorrelatedSample / proc-snapshot dict into a flat view."""
    out: dict = {}
    # proc-snapshot rows are already flat
    if "local_ip" in rec or "remote_ip" in rec:
        return rec
    # CorrelatedSample → use the local side, then attach ngfw bits
    if "local" in rec and "ngfw" in rec:
        local = rec["local"]
        ngfw = rec["ngfw"]
        ft = local.get("five_tuple") or {}
        out.update({
            "process_name": local.get("process_name"),
            "pid": local.get("pid"),
            "proto": ft.get("proto"),
            "src_ip": ft.get("src_ip"),
            "src_port": ft.get("src_port"),
            "dst_ip": ft.get("dst_ip"),
            "dst_port": ft.get("dst_port"),
            "tls_sni": ngfw.get("tls_sni"),
            "http_host": ngfw.get("http_host"),
        })
        return out
    # LocalFlow
    ft = rec.get("five_tuple") or {}
    out.update({
        "process_name": rec.get("process_name"),
        "pid": rec.get("pid"),
        "proto": ft.get("proto"),
        "src_ip": ft.get("src_ip"),
        "src_port": ft.get("src_port"),
        "dst_ip": ft.get("dst_ip"),
        "dst_port": ft.get("dst_port"),
    })
    return out


@app.command("version")
def version() -> None:
    from . import __version__
    console.print(f"ngfw-appdetector {__version__}")


@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind address (default loopback only)"),
    port: int = typer.Option(8765, "--port", "-p"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
    output_dir: Optional[Path] = typer.Option(
        None, "--output-dir", "-o", help="Where rendered .lua files go (defaults to config)"
    ),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't auto-open the browser"),
) -> None:
    """Launch the local web GUI (default http://127.0.0.1:8765).

    Install the optional extra first: `pip install 'ngfw-appdetector[web]'`
    """
    try:
        import uvicorn
        from .web.server import create_app
    except ImportError as e:
        console.print(
            "[red]Web extra not installed.[/] Run: "
            "[bold]pip install 'ngfw-appdetector[web]'[/]"
        )
        raise typer.Exit(code=1) from e

    cfg = _load(config)
    out = Path(output_dir or cfg.generator.output_dir)
    fastapi_app = create_app(cfg=cfg, output_dir=out, config_path=config)
    url = f"http://{host}:{port}"
    console.print(f"[green]NGFW App Detector UI[/] → {url}  (output: {out})")

    if not no_browser:
        import threading, webbrowser
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    uvicorn.run(fastapi_app, host=host, port=port, log_level=cfg.logging.level.lower())


if __name__ == "__main__":
    app()
