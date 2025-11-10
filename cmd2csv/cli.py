from __future__ import annotations
import argparse
from typing import List

from .ndb_client import NdbClient
from .devices import classify_device, build_testbed_from_devices
from .parser_pipeline import collect_from_testbed
from .exporter import export_per_command_as_csv


def parse_comma_list(s: str | None) -> List[str]:
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cmd2csv",
        description="Run commands on network devices and export parsed results as CSV.",
    )
    p.add_argument(
        "--hosts",
        required=True,
        help="Comma separated hostnames, e.g. R1,R2,R3",
    )
    p.add_argument(
        "--commands",
        required=True,
        help='Comma separated commands, e.g. "show ip int brief,show ip bgp summary"',
    )
    p.add_argument(
        "--ndb-url",
        required=True,
        help="NDB base URL, e.g. https://ndb.example.com/api",
    )
    p.add_argument(
        "--ndb-token",
        required=True,
        help="NDB API token",
    )
    p.add_argument(
        "--username",
        required=True,
        help="Device login username",
    )
    p.add_argument(
        "--password",
        required=True,
        help="Device login password",
    )
    p.add_argument(
        "--templates-dir",
        default=None,
        help="Optional TextFSM templates directory (for auto lookup)",
    )
    p.add_argument(
        "--output-dir",
        default="output",
        help="Output directory for CSV files",
    )
    return p


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    hostnames = parse_comma_list(args.hosts)
    commands = parse_comma_list(args.commands)

    ndb = NdbClient(args.ndb_url, args.ndb_token)
    raw_devices = ndb.fetch_devices_by_names(hostnames)
    classified = [classify_device(d) for d in raw_devices]

    testbed = build_testbed_from_devices(
        classified, username=args.username, password=args.password
    )

    entities = collect_from_testbed(
        testbed=testbed,
        hostnames=hostnames,
        commands=commands,
        templates_dir=args.templates_dir,
    )

    export_per_command_as_csv(entities, args.output_dir)


if __name__ == "__main__":
    main()
