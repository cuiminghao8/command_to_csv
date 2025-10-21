# command_to_csv

`command_to_csv.py` connects to one or more network devices, runs TextFSM-enabled commands, saves the structured data as CSV files, and can optionally e-mail the results. The script leans on the community-maintained NTC templates so it can handle output from a wide range of network operating systems and commands.

## Features

- **Multi-device automation** – supply multiple hostnames and the script will run the requested commands against each device sequentially.
- **Multiple commands per device** – pass several commands in the same run; the CSV output is generated for every `<hostname>_<command>.csv` pair.
- **Automatic platform detection** – Netmiko's `SSHDetect` is used to discover the correct device type before the command is executed, reducing per-device configuration.
- **Structured parsing with TextFSM** – results are normalized with `pandas.json_normalize` and saved as CSVs that are ready for spreadsheets or downstream tools.
- **Email delivery** – if recipients are provided, the generated CSV files are attached to an e-mail sent via SMTP.

Supported commands are listed in the [NTC template repository](https://github.com/networktocode/ntc-templates/tree/master/templates), and the supported platforms are maintained in the [NTC template index](https://github.com/networktocode/ntc-templates/blob/master/tests/test_index_order.py#L59).

## Prerequisites and Installation

- Python 3.7 or later (a virtual environment is recommended)
- Access to devices reachable via SSH
- Ability to reach your SMTP server if you plan to e-mail the results

```bash
git clone https://github.com/cuiminghao8/command_to_csv.git
cd command_to_csv
pip install -r requirements.txt
```

The script automatically sets the `NET_TEXTFSM` environment variable so the NTC templates installed from `requirements.txt` are discovered without additional configuration.

## Usage

Run `python command_to_csv.py --help` to see the complete CLI reference:

```
usage: command_to_csv.py [-h] -H HOSTNAME [HOSTNAME ...] -U USERNAME [-S]
                         -C COMMAND [COMMAND ...] [-R RECIPIENT]

Python Script to parse command output of networking devices and convert it to
wonderful csv file then send by mail.

optional arguments:
  -h, --help            show this help message and exit
  -H HOSTNAME [HOSTNAME ...], --hostname HOSTNAME [HOSTNAME ...]
                        Remote hostname
  -U USERNAME, --username USERNAME
                        SSH username
  -S, --secret          Option to enter privilege mode. Caution to use and make
                        sure what the command will do.
  -C COMMAND [COMMAND ...], --command COMMAND [COMMAND ...]
                        Commands to be executed. Quote by "" and separated by
                        space
  -R RECIPIENT, --recipient RECIPIENT
                        Email address of recipient of csv output file.
                        Optional. Multiple addresses should be separated by ";"
```

When you start the script you will be prompted for the SSH password. The CLI also accepts `--secret`, but the provided enable password is not used by the script when executing commands.

### Example

Run two commands against two switches and e-mail the results:

```bash
python command_to_csv.py \
    -H sw1 sw2 \
    -U username \
    -C "show cdp neighbor" "show interface status" \
    -R ops@example.com
```

The generated CSV files are written to the current working directory using the pattern `<hostname>_<command>.csv`. After the e-mail is sent, the CSV files are deleted automatically.

### Email configuration

The script currently expects you to provide SMTP details directly in the `email_alert` call inside `command_to_csv.py`. Update the following arguments before running the tool so that it can deliver the results:

```python
email_alert(
    smtp_server="smtp.example.com",
    sender="command-reports@example.com",
    recipient=args.recipient,
    results=file_name,
)
```

The script always calls `email_alert`, so be sure to configure valid SMTP settings and pass `--recipient` when running it. If you prefer to inspect the CSV files locally, comment out or remove the `email_alert` invocation in `command_to_csv.py` before execution.
