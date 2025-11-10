from __future__ import annotations
from typing import Dict, List
from pathlib import Path
import csv

META_FIELDS = [
    "hostname",      # 第一列
    "site",
    "role",
    "os",
    "timestamp",
    "command",
    "parse_engine",
]


def export_per_command_as_csv(
    entities: Dict[str, List[dict]],
    output_dir: str,
) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for cmd_name, rows in entities.items():
        if not rows:
            continue

        all_keys = set()
        for r in rows:
            all_keys.update(r.keys())

        meta_fields = [f for f in META_FIELDS if f in all_keys]
        other_fields = sorted(k for k in all_keys if k not in meta_fields)

        fieldnames = meta_fields + other_fields

        # 按 hostname 排序，保证一个设备的行聚在一起
        rows_sorted = sorted(rows, key=lambda r: r.get("hostname", ""))

        csv_path = output_path / f"{cmd_name}.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows_sorted:
                w.writerow({k: r.get(k, "") for k in fieldnames})
