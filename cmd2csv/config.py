from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class EmailConfig:
    enabled: bool = False
    smtp_server: str = ""
    smtp_port: int = 25
    use_tls: bool = False
    username: Optional[str] = None
    password: Optional[str] = None
    sender: str = ""
    recipients: List[str] = field(default_factory=list)
    subject: str = "cmd2csv execution results"


@dataclass
class AppConfig:
    hosts: List[str] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)
    ndb_url: Optional[str] = None
    ndb_token: Optional[str] = None
    ndb_verify: bool | str = True
    ndb_timeout: float = 10.0
    username: Optional[str] = None
    password: Optional[str] = None
    enable_password: Optional[str] = None
    templates_dir: Optional[str] = None
    output_dir: str = "output"
    formats: List[str] = field(default_factory=lambda: ["csv"])
    workers: int = 4
    connect_retries: int = 2
    log_level: str = "INFO"
    log_file: Optional[str] = None
    default_port: int = 22
    os_mappings: List[Dict[str, str]] = field(default_factory=list)
    email: EmailConfig = field(default_factory=EmailConfig)


def _coerce_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [x.strip() for x in value.split(",") if x.strip()]
    raise TypeError(f"Expected list or comma string, got {type(value).__name__}")


def load_config(path: str) -> AppConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Config root must be a mapping, got {type(raw).__name__}")

    email_raw = raw.get("email") or {}
    email = EmailConfig(
        enabled=bool(email_raw.get("enabled", False)),
        smtp_server=email_raw.get("smtp_server", "") or "",
        smtp_port=int(email_raw.get("smtp_port", 25)),
        use_tls=bool(email_raw.get("use_tls", False)),
        username=email_raw.get("username"),
        password=email_raw.get("password"),
        sender=email_raw.get("sender", "") or "",
        recipients=_coerce_list(email_raw.get("recipients")),
        subject=email_raw.get("subject", "cmd2csv execution results"),
    )

    return AppConfig(
        hosts=_coerce_list(raw.get("hosts")),
        commands=_coerce_list(raw.get("commands")),
        ndb_url=raw.get("ndb_url"),
        ndb_token=raw.get("ndb_token"),
        ndb_verify=raw.get("ndb_verify", True),
        ndb_timeout=float(raw.get("ndb_timeout", 10.0)),
        username=raw.get("username"),
        password=raw.get("password"),
        enable_password=raw.get("enable_password"),
        templates_dir=raw.get("templates_dir"),
        output_dir=raw.get("output_dir", "output"),
        formats=_coerce_list(raw.get("formats")) or ["csv"],
        workers=int(raw.get("workers", 4)),
        connect_retries=int(raw.get("connect_retries", 2)),
        log_level=str(raw.get("log_level", "INFO")),
        log_file=raw.get("log_file"),
        default_port=int(raw.get("default_port", 22)),
        os_mappings=list(raw.get("os_mappings") or []),
        email=email,
    )


def load_lines(path: str) -> List[str]:
    """Load newline-separated non-empty entries from a file."""
    lines: List[str] = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    return lines
