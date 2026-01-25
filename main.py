"""Application entrypoint.

The legacy interactive CLI/TUI has been removed.

Running this module starts the FastAPI server defined in `api.py`.
"""

from __future__ import annotations

import os

import uvicorn

from logging_config import configure_logging


def main() -> None:
    # Keep log formatting consistent with the legacy CLI/TUI.
    configure_logging(component="VANNA API")

    host = os.getenv("HOST", "0.0.0.0")
    # Default to 8001.
    port = int(os.getenv("PORT", "8001"))

    # Use import string so uvicorn can reload if desired.
    # (reload is off by default here.)
    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        # Keep our shared formatting; don't let Uvicorn replace logging config.
        log_config=None,
        # We provide our own request logging middleware in `api.py`.
        access_log=False,
    )


if __name__ == "__main__":
    main()
