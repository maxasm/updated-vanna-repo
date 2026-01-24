"""Shared logging configuration.

We want consistent application logs regardless of whether the app is started
from the old CLI entrypoint or via Uvicorn. The TUI previously used a simple
logging.basicConfig() format; we replicate that style here and make Uvicorn
loggers propagate to the root logger so they share the same formatting.
"""

from __future__ import annotations

import logging
import os
from typing import Optional


def configure_logging(component: str, level: Optional[int] = None) -> None:
    """Configure root logging and align Uvicorn loggers with it."""

    env_level = os.getenv("LOG_LEVEL", "INFO").upper().strip()
    resolved_level = getattr(logging, env_level, logging.INFO)
    if level is not None:
        resolved_level = level

    # force=True ensures we replace any prior logging config (including Uvicorn's
    # defaults), giving consistent formatting like the old TUI.
    logging.basicConfig(
        level=resolved_level,
        format=f"%(asctime)s [{component}] %(levelname)s: %(message)s",
        force=True,
    )

    # Make Uvicorn loggers propagate into root so they share our handler/format.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers = []
        uv_logger.propagate = True
