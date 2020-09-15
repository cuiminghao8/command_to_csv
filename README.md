# command_to_csv
 - This is a python Script to parse command output of multi-vendor networking devices and convert it to wonderful csv file then send by mail.<br />
 - Supported commands are listed [Here](https://github.com/networktocode/ntc-templates/tree/master/templates)
 - Supported OS are listed [Here](https://github.com/networktocode/ntc-templates/blob/master/tests/test_index_order.py#L59)
<br />

### Prerequisites and Installation
 - Python3.7 and above
 - Running on a specific Python3.7 Virtual environment is preferred
```
$ git clone https://github.com/cuiminghao8/command_to_csv.git
$
$ pip install -r requirements.txt
$

```
### How to use 
```
usage: command_to_csv.py [-h] -H HOSTNAME [HOSTNAME ...] -U USERNAME [-S] -C COMMAND [COMMAND ...] [-R RECIPIENT]

Python Script to parse command output of networking devices and convert it to wonderful csv file then send by mail.

optional arguments:
  -h, --help            show this help message and exit
  -H HOSTNAME [HOSTNAME ...], --hostname HOSTNAME [HOSTNAME ...]
                        Remote hostname
  -U USERNAME, --username USERNAME
                        SSH username
  -S, --secret          Option to enter privilege mode. Caution to use and make sure what the commend will do.
  -C COMMAND [COMMAND ...], --command COMMAND [COMMAND ...]
                        Commands to be executed. Quote by "" and separated by space
  -R RECIPIENT, --recipient RECIPIENT
                        Email address of recipient of csv output file. Optional. Multiple array should be split by ";"


```
### Example 
 - Running command "show cdp neighbor"
```
$
$ python command_to_csv.py -H sw1 -U username -C "show cdp neighbor" -R cuiminghao8@gmail.com
$
```
