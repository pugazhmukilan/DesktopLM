"""
Single application logging setup: detailed logs under DESKTOPLM_DATA_DIR/logs/desktoplm.log.
Console shows WARNING+ only; LangGraph tool steps also print [tool] lines from trace_callbacks.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

_configured = False


def _log_dir():
    from MemoryManager.settings import get_data_dir

    d = get_data_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def configure_logging(*, quiet: bool = False):
    """
    Idempotent. Returns path to the main log file.
    - File: DEBUG, rotating desktoplm.log
    - Console: WARNING (or ERROR if quiet); suppresses httpx INFO spam
    """
    global _configured
    log_path = _log_dir() / "desktoplm.log"

    if _configured:
        if quiet:
            _apply_quiet_console()
        return log_path

    detail_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_fmt = logging.Formatter("%(levelname)s %(name)s: %(message)s")

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.DEBUG)

    fh = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(detail_fmt)
    root.addHandler(fh)

    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.ERROR if quiet else logging.WARNING)
    ch.setFormatter(console_fmt)
    root.addHandler(ch)

    for name in (
        "httpx",
        "httpcore",
        "chromadb",
        "chromadb.telemetry",
        "openai",
        "urllib3",
    ):
        logging.getLogger(name).setLevel(logging.WARNING)

    _configured = True
    logging.getLogger("desktoplm").info("Logging initialized; log file: %s", log_path.resolve())
    return log_path


def _apply_quiet_console() -> None:
    root = logging.getLogger()
    for h in root.handlers:
        if isinstance(h, logging.StreamHandler) and h.stream in (sys.stderr, sys.stdout):
            h.setLevel(logging.ERROR)


def get_trace_logger() -> logging.Logger:
    return logging.getLogger("desktoplm.trace")
