from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

logger = logging.getLogger(__name__)

META_FIELDS: Sequence[str] = (
    "hostname",
    "site",
    "role",
    "os",
    "timestamp",
    "command",
    "parse_engine",
)

SUPPORTED_FORMATS = frozenset({"csv", "json"})


def _stringify(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple, set)):
        return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)
    return value


def _fieldnames_for(rows: List[Dict[str, Any]]) -> List[str]:
    all_keys: set[str] = set()
    for r in rows:
        all_keys.update(r.keys())
    meta = [f for f in META_FIELDS if f in all_keys]
    other = sorted(k for k in all_keys if k not in meta)
    return meta + other


def _sorted_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(rows, key=lambda r: (r.get("hostname", ""), r.get("command", "")))


def export_csv(entities: Dict[str, List[dict]], output_dir: str) -> List[str]:
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    written: List[str] = []
    for cmd_name, rows in entities.items():
        if not rows:
            continue
        fieldnames = _fieldnames_for(rows)
        sorted_rows = _sorted_rows(rows)
        csv_path = out_path / f"{cmd_name}.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in sorted_rows:
                w.writerow({k: _stringify(r.get(k, "")) for k in fieldnames})
        written.append(str(csv_path))
        logger.info("Wrote %d rows -> %s", len(sorted_rows), csv_path)
    return written


def export_json(entities: Dict[str, List[dict]], output_dir: str) -> List[str]:
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    written: List[str] = []
    for cmd_name, rows in entities.items():
        if not rows:
            continue
        sorted_rows = _sorted_rows(rows)
        json_path = out_path / f"{cmd_name}.json"
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(sorted_rows, f, ensure_ascii=False, indent=2, default=str)
        written.append(str(json_path))
        logger.info("Wrote %d rows -> %s", len(sorted_rows), json_path)
    return written


def export(
    entities: Dict[str, List[dict]],
    output_dir: str,
    formats: Iterable[str] = ("csv",),
) -> List[str]:
    """Write entities in every requested format. Returns paths of all files written."""
    written: List[str] = []
    requested = [f.lower() for f in formats]
    unknown = [f for f in requested if f not in SUPPORTED_FORMATS]
    if unknown:
        raise ValueError(
            f"Unsupported format(s): {unknown}. Supported: {sorted(SUPPORTED_FORMATS)}"
        )
    if "csv" in requested:
        written.extend(export_csv(entities, output_dir))
    if "json" in requested:
        written.extend(export_json(entities, output_dir))
    return written


def export_per_command_as_csv(
    entities: Dict[str, List[dict]], output_dir: str
) -> None:
    """Kept for backwards compatibility with earlier callers."""
    export_csv(entities, output_dir)
