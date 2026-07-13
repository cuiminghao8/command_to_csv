from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def normalize_command(command: str) -> str:
    s = command.strip().lower()
    s = re.sub(r"[^\w]+", "_", s)
    return s.strip("_")


def flatten_one_level(d: dict) -> dict:
    out: Dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, dict):
            for kk, vv in v.items():
                out[f"{k}_{kk}"] = vv
        else:
            out[k] = v
    return out


def genie_to_rows(parsed: Any) -> Optional[List[Dict[str, Any]]]:
    if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
        return parsed
    if isinstance(parsed, dict) and parsed:
        if all(isinstance(v, dict) for v in parsed.values()):
            rows: List[Dict[str, Any]] = []
            for k, v in parsed.items():
                row = {"_key": k}
                row.update(flatten_one_level(v))
                rows.append(row)
            return rows
    return None


def _genie_parse_errors() -> Tuple[type, ...]:
    from genie.metaparser.util.exceptions import SchemaEmptyParserError

    errors: Tuple[type, ...] = (SchemaEmptyParserError,)
    try:
        from genie.libs.parser.utils.common import ParserNotFound  # type: ignore

        errors = (SchemaEmptyParserError, ParserNotFound)
    except Exception:  # pragma: no cover - older genie versions
        pass
    return errors


def try_genie_parse(
    device, command: str, raw_output: Optional[str] = None
) -> Optional[List[Dict[str, Any]]]:
    try:
        expected = _genie_parse_errors()
    except Exception:
        expected = (Exception,)
    try:
        if raw_output is not None:
            parsed = device.parse(command, output=raw_output)
        else:
            parsed = device.parse(command)
    except expected as exc:
        logger.debug("Genie parser unavailable for %r: %s", command, exc)
        return None
    except Exception as exc:
        logger.warning("Genie parse failed for %r: %s", command, exc)
        return None
    return genie_to_rows(parsed)


def try_ntc_parse(
    ntc_platform: str, command: str, raw_output: str
) -> Optional[List[Dict[str, Any]]]:
    try:
        from ntc_templates.parse import parse_output
    except Exception as exc:  # pragma: no cover - dep missing
        logger.warning("ntc-templates not available: %s", exc)
        return None
    try:
        rows = parse_output(platform=ntc_platform, command=command, data=raw_output)
    except Exception as exc:
        logger.debug("NTC parse failed for %s/%r: %s", ntc_platform, command, exc)
        return None
    return rows or None


def template_filename(ntc_platform: str, command: str) -> str:
    cmd_norm = normalize_command(command)
    return f"{ntc_platform}__{cmd_norm}.textfsm"


def try_textfsm_auto(
    templates_dir: str, ntc_platform: str, command: str, raw_output: str
) -> Optional[List[Dict[str, Any]]]:
    path = Path(templates_dir) / template_filename(ntc_platform, command)
    if not path.exists():
        return None
    try:
        import textfsm

        with path.open() as f:
            fsm = textfsm.TextFSM(f)
        rows = fsm.ParseText(raw_output)
    except Exception as exc:
        logger.warning("TextFSM template %s failed: %s", path, exc)
        return None

    headers = [h.lower() for h in fsm.header]
    return [dict(zip(headers, r)) for r in rows] or None


def fallback_whitespace(raw_output: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in raw_output.splitlines():
        line = line.rstrip()
        if not line:
            continue
        cols = line.split()
        rows.append({f"col{i + 1}": v for i, v in enumerate(cols)})
    return rows


def process_one(
    device,
    dev_meta: Dict[str, Any],
    ntc_platform: str,
    command: str,
    templates_dir: Optional[str] = None,
) -> Tuple[str, List[Dict[str, Any]]]:
    entity_name = normalize_command(command)

    raw_output = device.execute(command)
    rows = try_genie_parse(device, command, raw_output=raw_output)
    parse_engine = "genie" if rows else None

    if not rows:
        ntc_rows = try_ntc_parse(ntc_platform, command, raw_output)
        if ntc_rows:
            rows, parse_engine = ntc_rows, "ntc"

    if not rows and templates_dir:
        tfsm_rows = try_textfsm_auto(templates_dir, ntc_platform, command, raw_output)
        if tfsm_rows:
            rows, parse_engine = tfsm_rows, "textfsm"

    if not rows:
        rows = fallback_whitespace(raw_output)
        parse_engine = "raw_space"

    out_rows = [{**dev_meta, "command": command, "parse_engine": parse_engine, **r} for r in rows]
    return entity_name, out_rows


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
