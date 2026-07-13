from __future__ import annotations

import logging
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .parser_pipeline import process_one, utc_timestamp

logger = logging.getLogger(__name__)


@dataclass
class DeviceResult:
    hostname: str
    ok: bool
    commands_ok: int = 0
    commands_failed: int = 0
    error: Optional[str] = None
    elapsed: float = 0.0
    command_errors: Dict[str, str] = field(default_factory=dict)


@dataclass
class RunSummary:
    entities: Dict[str, List[Dict[str, Any]]]
    results: List[DeviceResult]

    @property
    def total_rows(self) -> int:
        return sum(len(v) for v in self.entities.values())

    @property
    def ok_count(self) -> int:
        return sum(1 for r in self.results if r.ok)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if not r.ok)

    def format_report(self) -> str:
        lines = [
            "cmd2csv run summary",
            "-" * 40,
            f"devices ok:     {self.ok_count}",
            f"devices failed: {self.failed_count}",
            f"total rows:     {self.total_rows}",
            f"entities:       {len(self.entities)}",
            "",
        ]
        for r in sorted(self.results, key=lambda x: x.hostname):
            status = "OK" if r.ok else "FAIL"
            lines.append(
                f"  [{status:4}] {r.hostname:24s} "
                f"cmd_ok={r.commands_ok} cmd_fail={r.commands_failed} "
                f"elapsed={r.elapsed:.1f}s"
            )
            if r.error:
                lines.append(f"          error: {r.error}")
            for cmd, err in r.command_errors.items():
                lines.append(f"          cmd {cmd!r}: {err}")
        return "\n".join(lines)


def _connect_with_retry(device, retries: int) -> None:
    last_exc: Optional[Exception] = None
    for attempt in range(1, retries + 2):
        try:
            device.connect(log_stdout=False)
            return
        except Exception as exc:
            last_exc = exc
            if attempt > retries:
                break
            delay = 2 ** attempt
            logger.warning(
                "Connect to %s failed (attempt %d/%d): %s; retrying in %ds",
                device.name, attempt, retries + 1, exc, delay,
            )
            time.sleep(delay)
    raise last_exc  # type: ignore[misc]


def _process_device(
    dev,
    commands: List[str],
    templates_dir: Optional[str],
    timestamp: str,
    connect_retries: int,
) -> Tuple[DeviceResult, Dict[str, List[Dict[str, Any]]]]:
    start = time.monotonic()
    result = DeviceResult(hostname=dev.name, ok=False)
    per_device_entities: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    try:
        _connect_with_retry(dev, connect_retries)
    except Exception as exc:
        result.error = f"connect failed: {exc}"
        result.elapsed = time.monotonic() - start
        logger.error("Device %s: %s", dev.name, result.error)
        return result, per_device_entities

    ntc_platform = dev.custom.get("ntc_platform", dev.os)
    dev_meta = {
        "timestamp": timestamp,
        "hostname": dev.name,
        "site": dev.custom.get("site", ""),
        "role": dev.custom.get("role", ""),
        "os": dev.os,
    }

    try:
        for cmd in commands:
            try:
                entity_name, rows = process_one(
                    dev, dev_meta, ntc_platform, cmd, templates_dir=templates_dir
                )
                per_device_entities[entity_name].extend(rows)
                result.commands_ok += 1
            except Exception as exc:
                result.commands_failed += 1
                result.command_errors[cmd] = str(exc)
                logger.error("Device %s command %r failed: %s", dev.name, cmd, exc)
        result.ok = result.commands_failed == 0
    finally:
        try:
            dev.disconnect()
        except Exception as exc:
            logger.warning("Disconnect from %s raised: %s", dev.name, exc)
        result.elapsed = time.monotonic() - start

    return result, per_device_entities


def run_commands(
    testbed,
    hostnames: List[str],
    commands: List[str],
    *,
    templates_dir: Optional[str] = None,
    workers: int = 4,
    connect_retries: int = 2,
) -> RunSummary:
    """Execute ``commands`` on each device in ``hostnames`` in parallel.

    Failures are isolated per device and per command; the summary lists all
    successes and failures so one bad device never aborts the whole run.
    """
    timestamp = utc_timestamp()
    wanted = set(hostnames)
    devices = [dev for name, dev in testbed.devices.items() if not wanted or name in wanted]

    if not devices:
        logger.warning("No devices to run against; nothing to do")
        return RunSummary(entities={}, results=[])

    effective_workers = max(1, min(workers, len(devices)))
    logger.info(
        "Running %d commands on %d devices with %d workers",
        len(commands), len(devices), effective_workers,
    )

    merged: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    results: List[DeviceResult] = []

    with ThreadPoolExecutor(max_workers=effective_workers) as pool:
        futures = {
            pool.submit(
                _process_device, dev, commands, templates_dir, timestamp, connect_retries
            ): dev
            for dev in devices
        }
        for fut in as_completed(futures):
            dev = futures[fut]
            try:
                result, per_device = fut.result()
            except Exception as exc:
                logger.exception("Unexpected error processing %s", dev.name)
                results.append(DeviceResult(hostname=dev.name, ok=False, error=str(exc)))
                continue
            results.append(result)
            for k, rows in per_device.items():
                merged[k].extend(rows)

    return RunSummary(entities=dict(merged), results=results)
