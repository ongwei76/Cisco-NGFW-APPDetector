"""Windows-specific SocketFlowSource wrapper."""

from __future__ import annotations

from typing import Callable

from ..models import LocalFlow
from .socket_source import SocketFlowSource


class SocketFlowSourceWindows(SocketFlowSource):
    """Windows defaults: use netstat fallback path via ProcessTracker."""

    PIPELINE_NAME = "windows: psutil + netstat fallback"

    def __init__(
        self,
        on_flow: Callable[[LocalFlow], None],
        proc_refresh_ms: int = 250,
        enable_lsof_fallback: bool = False,
        skip_loopback: bool = True,
        reemit_interval_s: float = 5.0,
    ) -> None:
        super().__init__(
            on_flow=on_flow,
            proc_refresh_ms=proc_refresh_ms,
            enable_lsof_fallback=enable_lsof_fallback,
            skip_loopback=skip_loopback,
            reemit_interval_s=reemit_interval_s,
        )
