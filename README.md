# cmd2csv

`cmd2csv` connects to a network device inventory (NDB), builds a dynamic
[pyATS](https://developer.cisco.com/docs/pyats/) testbed, executes commands on the
selected devices **in parallel**, parses the output through Genie, NTC TextFSM
templates, or your own TextFSM templates, and finally exports the structured data
as CSV and/or JSON files grouped by command. Optionally, it can email the outputs
and a summary report when the run finishes.

## Features

- Multi-vendor support (Cisco IOS/IOS-XE/NX-OS/IOS-XR/ASA, Arista EOS,
  Juniper Junos, HP Comware, Huawei VRP) with a pluggable OS map.
- Parallel per-device execution with a configurable worker pool.
- Fault-isolated runner: one bad device or command never aborts the whole run;
  successes and failures are reported side by side.
- SSH connect retries with exponential backoff.
- Multi-engine parser pipeline (Genie → NTC-templates → custom TextFSM →
  whitespace fallback).
- YAML configuration file with CLI/env overrides.
- Credentials from env vars (`CMD2CSV_PASSWORD`, `CMD2CSV_ENABLE_PASSWORD`,
  `CMD2CSV_NDB_TOKEN`) or interactive `getpass` prompts — no secrets on the
  command line.
- NDB API client with request retries, custom timeout, and TLS options
  (`--ndb-insecure`, `--ndb-ca-bundle`).
- Multi-format export: `csv`, `json` (comma-separated, e.g. `--formats csv,json`).
- Structured logging with adjustable console level and optional debug log file.
- Optional SMTP notification with attachments (STARTTLS + auth supported).
- Console entry point (`cmd2csv`) via `pyproject.toml`.

## Project layout

```
command_to_csv/
├── cmd2csv/
│   ├── __init__.py
│   ├── cli.py               # argparse + orchestration
│   ├── config.py            # YAML config, dataclasses
│   ├── devices.py           # OS map + pyATS testbed builder
│   ├── exporter.py          # CSV / JSON exporters
│   ├── logging_setup.py     # structured logging config
│   ├── ndb_client.py        # NDB HTTP client with retries
│   ├── notifier.py          # SMTP email notifier
│   ├── parser_pipeline.py   # Genie / NTC / TextFSM / fallback parsing
│   └── runner.py            # parallel runner + per-device summary
├── examples/
│   └── cmd2csv.example.yaml
├── tests/
├── pyproject.toml
├── requirements.txt
└── README.md
```

Custom TextFSM templates live under `--templates-dir` and use the naming
pattern `<ntc_platform>__<normalized_command>.textfsm` (e.g.
`cisco_ios__show_ip_interface_brief.textfsm`).

## Installation

```bash
python -m venv venv
source venv/bin/activate
pip install -e .              # installs the `cmd2csv` console script
# or:  pip install -r requirements.txt
```

## Usage

### With CLI flags

```bash
export CMD2CSV_NDB_TOKEN=xxxxx
export CMD2CSV_PASSWORD=xxxxx

cmd2csv \
  --hosts R1,R2,SW1 \
  --commands "show ip interface brief,show interface status" \
  --ndb-url https://ndb.example.com/api \
  --username admin \
  --output-dir ./output \
  --formats csv,json \
  --workers 8
```

If `--password` and `--username` are omitted and no env var is set, they are
prompted for interactively with `getpass`.

### With a YAML config file

```bash
cp examples/cmd2csv.example.yaml cmd2csv.yaml
$EDITOR cmd2csv.yaml
cmd2csv -c cmd2csv.yaml
```

CLI flags override values in the YAML file.

### Hosts / commands from files

```bash
cmd2csv --hosts-file hosts.txt --commands-file cmds.txt ...
```

Both files ignore blank lines and lines starting with `#`.

## Arguments (highlights)

| Flag | Purpose |
| --- | --- |
| `-c/--config` | Load a YAML config file (overridden by CLI flags). |
| `--hosts` / `--hosts-file` | Devices to target. |
| `--commands` / `--commands-file` | Commands to run on each device. |
| `--ndb-url` / `--ndb-token` | NDB API base URL and token. |
| `--ndb-insecure` / `--ndb-ca-bundle` | TLS options for the NDB API. |
| `--username` / `--password` | Device SSH credentials (env vars preferred). |
| `--ask-enable` / `--enable-password` | Enable-mode secret (Cisco). |
| `--templates-dir` | Optional custom TextFSM templates. |
| `--output-dir` | Output root. |
| `--formats` | Comma-separated: `csv`, `json`. |
| `--workers` | Parallel device workers (default 4). |
| `--connect-retries` | SSH connect retries per device (default 2). |
| `--log-level` / `--log-file` / `--quiet` | Logging controls. |
| `--email` | Send SMTP notification (config drives server/recipients). |

Each command becomes one output file per format, named after the normalized
command (whitespace and special characters mapped to `_`). Rows are annotated
with metadata: `hostname`, `site`, `role`, `os`, `timestamp`, `command`,
`parse_engine`.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | All devices succeeded. |
| 1 | Some devices or commands failed (details in the run summary). |
| 2 | Configuration error (missing required inputs). |
| 3 | NDB returned no matching devices. |
| 4 | No devices could be classified against `OS_MAP`. |

## Extending the parser

1. Register additional vendor/OS combinations either via the `os_mappings`
   section of the YAML config or, in code, by calling
   `cmd2csv.devices.register_os_mapping()`.
2. Drop custom TextFSM templates into your `--templates-dir` when Genie or NTC
   does not provide a parser.
3. Adjust `NdbClient._parse_device()` to match your NDB API schema.

## Development

```bash
pip install -e .[dev]
pytest
```

Pure functions (parsers, exporters, config loader) are covered by unit tests;
the runner and NDB client are network-dependent and mocked at the seams.

## Legacy script

The original single-file `command_to_csv.py` (netmiko + SMTP mail) is preserved
at the repo root for reference. New work should target the `cmd2csv/` package.
