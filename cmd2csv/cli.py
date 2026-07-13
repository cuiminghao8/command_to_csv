from __future__ import annotations

import argparse
import getpass
import logging
import os
import sys
from typing import List, Optional

from . import __version__
from .config import AppConfig, load_config, load_lines
from .devices import build_testbed_from_devices, classify_device, register_os_mapping
from .exporter import export
from .logging_setup import configure_logging
from .ndb_client import NdbClient
from .notifier import send_email
from .runner import run_commands

logger = logging.getLogger("cmd2csv.cli")


def _parse_comma_list(s: Optional[str]) -> List[str]:
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


def _first(*values: Optional[str]) -> Optional[str]:
    for v in values:
        if v not in (None, ""):
            return v
    return None


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cmd2csv",
        description="Run commands on network devices and export parsed results as CSV/JSON.",
    )
    p.add_argument("--version", action="version", version=f"cmd2csv {__version__}")
    p.add_argument("-c", "--config", help="Path to YAML config file")

    p.add_argument("--hosts", help="Comma separated hostnames, e.g. R1,R2,R3")
    p.add_argument("--hosts-file", help="File containing one hostname per line")
    p.add_argument(
        "--commands",
        help='Comma separated commands, e.g. "show ip int brief,show ip bgp summary"',
    )
    p.add_argument("--commands-file", help="File containing one command per line")

    p.add_argument("--ndb-url", help="NDB base URL, e.g. https://ndb.example.com/api")
    p.add_argument("--ndb-token", help="NDB API token (or set CMD2CSV_NDB_TOKEN)")
    p.add_argument("--ndb-timeout", type=float, help="NDB HTTP timeout seconds (default 10)")
    p.add_argument(
        "--ndb-insecure",
        action="store_true",
        help="Disable TLS verification against the NDB API",
    )
    p.add_argument(
        "--ndb-ca-bundle",
        help="Path to a CA bundle used to verify NDB API TLS",
    )

    p.add_argument("--username", help="Device login username")
    p.add_argument(
        "--password",
        help="Device password (or CMD2CSV_PASSWORD env var; prompts if omitted)",
    )
    p.add_argument(
        "--enable-password",
        help="Enable secret (or CMD2CSV_ENABLE_PASSWORD env var; optional)",
    )
    p.add_argument(
        "--ask-enable",
        action="store_true",
        help="Prompt for enable password interactively",
    )
    p.add_argument("--default-port", type=int, help="Default SSH port (default 22)")

    p.add_argument("--templates-dir", help="Optional TextFSM templates directory")
    p.add_argument("--output-dir", help="Output directory for exports (default: output)")
    p.add_argument(
        "--formats",
        help="Comma separated output formats: csv,json (default csv)",
    )

    p.add_argument("--workers", type=int, help="Parallel device workers (default 4)")
    p.add_argument(
        "--connect-retries", type=int, help="SSH connect retries per device (default 2)"
    )

    p.add_argument(
        "--log-level",
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Console log level (default INFO)",
    )
    p.add_argument("--log-file", help="Optional path for a DEBUG-level log file")
    p.add_argument("--quiet", action="store_true", help="Silence console log output")

    p.add_argument(
        "--email",
        action="store_true",
        help="Send an email with the outputs and summary (uses config values)",
    )

    return p


def _resolve_config(args: argparse.Namespace) -> AppConfig:
    cfg = load_config(args.config) if args.config else AppConfig()

    cli_hosts = _parse_comma_list(args.hosts)
    if args.hosts_file:
        cli_hosts.extend(load_lines(args.hosts_file))
    if cli_hosts:
        cfg.hosts = cli_hosts

    cli_cmds = _parse_comma_list(args.commands)
    if args.commands_file:
        cli_cmds.extend(load_lines(args.commands_file))
    if cli_cmds:
        cfg.commands = cli_cmds

    if args.ndb_url:
        cfg.ndb_url = args.ndb_url
    if args.ndb_timeout is not None:
        cfg.ndb_timeout = args.ndb_timeout
    if args.ndb_ca_bundle:
        cfg.ndb_verify = args.ndb_ca_bundle
    if args.ndb_insecure:
        cfg.ndb_verify = False

    cfg.ndb_token = _first(
        args.ndb_token, cfg.ndb_token, os.environ.get("CMD2CSV_NDB_TOKEN")
    )

    if args.username:
        cfg.username = args.username
    if args.default_port is not None:
        cfg.default_port = args.default_port

    cfg.password = _first(
        args.password, cfg.password, os.environ.get("CMD2CSV_PASSWORD")
    )
    cfg.enable_password = _first(
        args.enable_password,
        cfg.enable_password,
        os.environ.get("CMD2CSV_ENABLE_PASSWORD"),
    )

    if args.templates_dir:
        cfg.templates_dir = args.templates_dir
    if args.output_dir:
        cfg.output_dir = args.output_dir
    if args.formats:
        cfg.formats = _parse_comma_list(args.formats) or cfg.formats
    if args.workers is not None:
        cfg.workers = args.workers
    if args.connect_retries is not None:
        cfg.connect_retries = args.connect_retries
    if args.log_level:
        cfg.log_level = args.log_level
    if args.log_file:
        cfg.log_file = args.log_file
    if args.email:
        cfg.email.enabled = True

    return cfg


def _prompt_missing_credentials(cfg: AppConfig, ask_enable: bool) -> None:
    if not cfg.username:
        cfg.username = input("Device username: ").strip()
    if not cfg.password:
        cfg.password = getpass.getpass(f"Password for {cfg.username}: ")
    if ask_enable and not cfg.enable_password:
        cfg.enable_password = getpass.getpass("Enable secret: ")


def _validate(cfg: AppConfig) -> None:
    problems: List[str] = []
    if not cfg.hosts:
        problems.append("no hosts provided (use --hosts, --hosts-file, or config)")
    if not cfg.commands:
        problems.append("no commands provided (use --commands, --commands-file, or config)")
    if not cfg.ndb_url:
        problems.append("--ndb-url is required")
    if not cfg.ndb_token:
        problems.append("--ndb-token or CMD2CSV_NDB_TOKEN is required")
    if not cfg.username:
        problems.append("username is required")
    if problems:
        for line in problems:
            logger.error("config error: %s", line)
        raise SystemExit(2)


def _apply_os_mappings(cfg: AppConfig) -> None:
    for entry in cfg.os_mappings:
        try:
            register_os_mapping(
                vendor=entry["vendor"],
                os_name=entry["os"],
                pyats_os=entry["pyats_os"],
                ntc_platform=entry["ntc_platform"],
            )
        except KeyError as exc:
            logger.warning("os_mappings entry missing key %s: %r", exc, entry)


def _email_body(summary_text: str, cfg: AppConfig) -> str:
    return (
        f"cmd2csv v{__version__} run report\n"
        f"output_dir: {cfg.output_dir}\n"
        f"formats:    {', '.join(cfg.formats)}\n\n"
        f"{summary_text}\n"
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    cfg = _resolve_config(args)
    configure_logging(level=cfg.log_level, log_file=cfg.log_file, quiet=args.quiet)

    _prompt_missing_credentials(cfg, args.ask_enable)
    _validate(cfg)
    _apply_os_mappings(cfg)

    logger.info(
        "cmd2csv %s: %d host(s), %d command(s), formats=%s, workers=%d",
        __version__, len(cfg.hosts), len(cfg.commands),
        ",".join(cfg.formats), cfg.workers,
    )

    ndb = NdbClient(
        cfg.ndb_url or "",
        cfg.ndb_token or "",
        timeout=cfg.ndb_timeout,
        verify=cfg.ndb_verify,
    )
    raw_devices = ndb.fetch_devices_by_names(cfg.hosts)
    if not raw_devices:
        logger.error("NDB returned no devices for the requested hostnames")
        return 3

    classified = []
    for d in raw_devices:
        try:
            classified.append(classify_device(d))
        except ValueError as exc:
            logger.warning("Skipping %s: %s", d.hostname, exc)
    if not classified:
        logger.error("No devices could be classified; aborting")
        return 4

    testbed = build_testbed_from_devices(
        classified,
        username=cfg.username or "",
        password=cfg.password or "",
        enable_password=cfg.enable_password,
        default_port=cfg.default_port,
    )

    summary = run_commands(
        testbed=testbed,
        hostnames=cfg.hosts,
        commands=cfg.commands,
        templates_dir=cfg.templates_dir,
        workers=cfg.workers,
        connect_retries=cfg.connect_retries,
    )

    output_files = export(summary.entities, cfg.output_dir, formats=cfg.formats)
    report = summary.format_report()
    logger.info("Wrote %d output file(s) under %s", len(output_files), cfg.output_dir)
    sys.stderr.write("\n" + report + "\n")

    if cfg.email.enabled:
        send_email(cfg.email, _email_body(report, cfg), attachments=output_files)

    if summary.failed_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
