"""Render LUA detectors from AppFingerprints using a Jinja2 template."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .. import __version__
from ..models import AppFingerprint

log = logging.getLogger(__name__)


def host_patterns(fp: AppFingerprint) -> list[str]:
    """Unique host patterns in priority order (SNI, cert CN, suffix, HTTP host)."""
    seen: set[str] = set()
    out: list[str] = []
    candidates = [
        *fp.tls_snis,
        *fp.tls_cnames,
        *(suffix[1:] if suffix.startswith(".") else suffix for suffix in fp.tls_host_suffixes),
        *fp.http_hosts,
    ]
    for host in candidates:
        key = host.casefold()
        if key not in seen:
            seen.add(key)
            out.append(host)
    return out


class LuaRenderer:
    def __init__(self, output_dir: Union[str, Path], template_dir: Optional[Union[str, Path]] = None) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        tdir = Path(template_dir) if template_dir else Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(tdir)),
            autoescape=select_autoescape(disabled_extensions=("lua", "j2")),
            keep_trailing_newline=True,
        )

    def render(self, fp: AppFingerprint, app_id: int = 9000, service_app_id: int = 9001) -> Path:
        tpl = self.env.get_template("detector.lua.j2")
        content = tpl.render(
            fp=fp,
            host_patterns=host_patterns(fp),
            app_id=app_id,
            service_app_id=service_app_id,
            generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            version=__version__,
        )
        out = self.output_dir / f"{fp.app_name}.lua"
        out.write_text(content)
        log.info("Wrote %s (%d samples)", out, fp.sample_count)
        return out
