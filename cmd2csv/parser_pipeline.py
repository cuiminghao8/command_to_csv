from __future__ import annotations
from typing import Dict, List, Any
from collections import defaultdict
from datetime import datetime
import re
from pathlib import Path

from genie.metaparser.util.exceptions import SchemaEmptyParserError
from ntc_templates.parse import parse_output
import textfsm


def normalize_command(command: str) -> str:
    s = command.strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^\w]+", "_", s)
    return s.strip("_")


def flatten_one_level(d: dict) -> dict:
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, dict):
            for kk, vv in v.items():
                out[f"{k}_{kk}"] = vv
        else:
            out[k] = v
    return out


def genie_to_rows(parsed: Any) -> List[Dict[str, Any]] | None:
    if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
        return parsed

    if isinstance(parsed, dict):
        # 尝试识别「key -> dict」结构
        if all(isinstance(v, dict) for v in parsed.values()):
            rows: list[dict] = []
            for k, v in parsed.items():
                row = {"_key": k}
                row.update(flatten_one_level(v))
                rows.append(row)
            return rows
    return None


def try_genie_parse(device, command: str) -> List[Dict[str, Any]] | None:
    try:
        parsed = device.parse(command)
    except (SchemaEmptyParserError, Exception):
        return None
    return genie_to_rows(parsed)


def try_ntc_parse(ntc_platform: str, command: str, raw_output: str) -> List[Dict[str, Any]] | None:
    try:
        rows = parse_output(
            platform=ntc_platform,
            command=command,
            data=raw_output,
        )
        return rows or None
    except Exception:
        return None


def template_filename(ntc_platform: str, command: str) -> str:
    cmd_norm = normalize_command(command)
    return f"{ntc_platform}__{cmd_norm}.textfsm"


def try_textfsm_auto(templates_dir: str, ntc_platform: str, command: str, raw_output: str) -> List[Dict[str, Any]] | None:
    path = Path(templates_dir) / template_filename(ntc_platform, command)
    if not path.exists():
        return None

    with path.open() as f:
        fsm = textfsm.TextFSM(f)

    rows = fsm.ParseText(raw_output)
    headers = [h.lower() for h in fsm.header]

    result: list[dict] = []
    for r in rows:
        result.append(dict(zip(headers, r)))
    return result or None


def fallback_whitespace(raw_output: str) -> List[Dict[str, Any]]:
    rows: list[dict] = []
    for line in raw_output.splitlines():
        line = line.rstrip()
        if not line:
            continue
        cols = line.split()
        row = {f"col{i+1}": v for i, v in enumerate(cols)}
        rows.append(row)
    return rows


def process_one(
    device,
    dev_meta: Dict[str, Any],
    ntc_platform: str,
    command: str,
    templates_dir: str | None = None,
) -> tuple[str, List[Dict[str, Any]]]:
    entity_name = normalize_command(command)

    # 先试 Genie
    rows = try_genie_parse(device, command)
    parse_engine = None

    if rows:
        parse_engine = "genie"
    else:
        raw_output = device.execute(command)

        ntc_rows = try_ntc_parse(ntc_platform, command, raw_output)
        if ntc_rows:
            rows = ntc_rows
            parse_engine = "ntc"
        elif templates_dir:
            tfsm_rows = try_textfsm_auto(templates_dir, ntc_platform, command, raw_output)
            if tfsm_rows:
                rows = tfsm_rows
                parse_engine = "textfsm"
            else:
                rows = fallback_whitespace(raw_output)
                parse_engine = "raw_space"
        else:
            rows = fallback_whitespace(raw_output)
            parse_engine = "raw_space"

    out_rows: list[dict] = []
    for r in rows:
        row = {
            **dev_meta,
            "command": command,
            "parse_engine": parse_engine,
            **r,
        }
        out_rows.append(row)

    return entity_name, out_rows


def collect_from_testbed(
    testbed,
    hostnames: List[str],
    commands: List[str],
    templates_dir: str | None = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    返回: normalized_command -> List[rows]
    """
    entities: dict[str, list[dict]] = defaultdict(list)
    ts = datetime.utcnow().isoformat()

    # 只使用指定 hostnames
    devices = [
        dev for name, dev in testbed.devices.items()
        if (not hostnames) or (name in hostnames)
    ]

    for dev in devices:
        dev.connect(log_stdout=False)

        ntc_platform = dev.custom.get("ntc_platform", dev.os)
        dev_meta = {
            "timestamp": ts,
            "hostname": dev.name,
            "site": dev.custom.get("site", ""),
            "role": dev.custom.get("role", ""),
            "os": dev.os,
        }

        for cmd in commands:
            entity_name, rows = process_one(
                dev,
                dev_meta,
                ntc_platform,
                cmd,
                templates_dir=templates_dir,
            )
            entities[entity_name].extend(rows)

        dev.disconnect()

    return entities
