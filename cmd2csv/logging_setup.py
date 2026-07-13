from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

_FMT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"


def configure_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    quiet: bool = False,
) -> None:
    """Configure the root logger for cmd2csv.

    Parameters
    ----------
    level:
        Log level name (``DEBUG``/``INFO``/``WARNING``/``ERROR``).
    log_file:
        Optional path; when given, also logs to that file at DEBUG level.
    quiet:
        If true, silence stdout handler (file handler still active if configured).
    """
    numeric = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if log_file else numeric)

    for h in list(root.handlers):
        root.removeHandler(h)

    formatter = logging.Formatter(_FMT, datefmt=_DATEFMT)

    if not quiet:
        sh = logging.StreamHandler(sys.stderr)
        sh.setLevel(numeric)
        sh.setFormatter(formatter)
        root.addHandler(sh)

    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        root.addHandler(fh)

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("unicon").setLevel(logging.WARNING)
