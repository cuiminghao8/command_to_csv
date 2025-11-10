# cmd2csv

`cmd2csv` connects to a network device inventory (NDB), builds a dynamic
[pyATS](https://developer.cisco.com/docs/pyats/) testbed, executes commands on the
selected devices, parses the output via Genie, NTC TextFSM templates, or custom
TextFSM templates, and finally exports the structured data as CSV files grouped by
command.

## Project layout

```
cmd2csv/
  requirements.txt
  cmd2csv/
    __init__.py
    cli.py
    ndb_client.py
    devices.py
    parser_pipeline.py
    exporter.py
```

If you want to provide additional TextFSM templates, place them under
`cmd2csv/templates/` using the file naming pattern
`<ntc_platform>__<normalized_command>.textfsm`.

## Installation

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python -m cmd2csv.cli \
  --hosts R1,R2 \
  --commands "show ip interface brief,show interface status" \
  --ndb-url https://ndb.example.com/api \
  --ndb-token YOUR_TOKEN \
  --username admin \
  --password cisco \
  --output-dir ./output
```

### Arguments

- `--hosts` – comma separated list of hostnames to target.
- `--commands` – comma separated list of commands to run on each device.
- `--ndb-url` and `--ndb-token` – connection information for the NDB API.
- `--username` / `--password` – device login credentials.
- `--templates-dir` – optional directory containing extra TextFSM templates.
- `--output-dir` – directory where the CSV files will be written (defaults to `./output`).

Each command results in a CSV file named after the normalized command (spaces and
special characters converted to underscores). Rows are annotated with metadata
such as hostname, site, role, timestamp, and parsing engine.

### Extending the parser

1. Update `OS_MAP` in `cmd2csv/devices.py` to map additional vendor/OS
   combinations to their pyATS OS and NTC platform identifiers.
2. Drop custom TextFSM templates into `cmd2csv/templates/` when Genie or NTC does
   not provide a parser.
3. Adjust `NdbClient.fetch_devices_by_names` to match your actual NDB API schema.

With these adjustments you can iteratively extend the tool to support your
network environment.
