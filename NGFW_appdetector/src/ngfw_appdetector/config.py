"""Configuration loader (YAML + env overrides via pydantic-settings)."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, Union

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger(__name__)


class FmcConfig(BaseModel):
    host: str = "fmc.example.local"
    username: str = "api_user"
    password: str = "REPLACE_ME"
    verify_tls: bool = False
    domain_uuid: Optional[str] = None
    poll_interval_sec: int = 10
    poll_lookback_sec: int = 60


class CaptureConfig(BaseModel):
    proc_refresh_ms: int = 500
    fmc_drain_sec: int = 30


class CorrelatorConfig(BaseModel):
    time_window_sec: int = 5
    match_direction: str = "either"  # either | strict


class GeneratorConfig(BaseModel):
    output_dir: str = "./generated_detectors"
    min_samples: int = 3
    prefer_features: list[str] = Field(
        default_factory=lambda: ["tls_sni", "tls_cname", "http_host"]
    )


class SharingConfig(BaseModel):
    """Maintainer-curated Lua library published in a public GitHub repository."""

    github_owner: str = "ongwei76"
    github_repo: str = "Cisco-NGFW-APPDetector"
    branch: str = "main"
    library_dir: str = "library"
    maintainer_email: str = "yongwli@cisco.com"
    mirror_fallback: bool = True  # fall back to cdn.jsdelivr.net when GitHub is unreachable


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: Optional[str] = None


class AppConfig(BaseSettings):
    """Top-level config. Env vars override YAML: NGFW_APPDETECTOR_FMC__PASSWORD=..."""

    model_config = SettingsConfigDict(
        env_prefix="NGFW_APPDETECTOR_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    fmc: FmcConfig = Field(default_factory=FmcConfig)
    capture: CaptureConfig = Field(default_factory=CaptureConfig)
    correlator: CorrelatorConfig = Field(default_factory=CorrelatorConfig)
    generator: GeneratorConfig = Field(default_factory=GeneratorConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    sharing: SharingConfig = Field(default_factory=SharingConfig)


def _discover_config() -> Optional[Path]:
    """Search well-known locations for a config file when caller didn't specify one.

    Order: $NGFW_APPDETECTOR_CONFIG → ./config.yaml → ./config.yml →
    ~/.config/ngfw-appdetector/config.yaml. First existing wins.
    """
    env = os.environ.get("NGFW_APPDETECTOR_CONFIG")
    candidates: list[Path] = []
    if env:
        candidates.append(Path(env).expanduser())
    candidates += [
        Path.cwd() / "config.yaml",
        Path.cwd() / "config.yml",
        Path.home() / ".config" / "ngfw-appdetector" / "config.yaml",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def load_config(path: Optional[Union[str, Path]]) -> AppConfig:
    """Load config from YAML if provided, then apply env overrides.

    When `path` is None, search well-known locations so users don't end up with
    placeholder defaults silently. When `path` is given but missing, fail loudly.
    """
    data: dict = {}
    used: Optional[Path] = None
    if path is not None:
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"config file not found: {p}")
        used = p
    else:
        used = _discover_config()
    if used is not None:
        data = yaml.safe_load(used.read_text(encoding="utf-8-sig")) or {}
        log.debug("loaded config from %s", used)
    # pydantic-settings will overlay env vars on top of the YAML-derived defaults
    return AppConfig(**data)


def save_fmc_section(path: Union[str, Path], fmc: FmcConfig) -> None:
    """Merge fmc fields into an existing YAML config file (creating if missing)."""
    p = Path(path)
    data: dict = {}
    if p.exists():
        data = yaml.safe_load(p.read_text(encoding="utf-8-sig")) or {}
    data["fmc"] = fmc.model_dump()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
