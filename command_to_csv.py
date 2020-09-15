# -*- coding: utf-8 -*-
# @Time    : 2020/9/14 13:23
# @Author  : Minghao Cui
# @FileName: command_to_csv_v2.py.py
# @Software: PyCharm
# @Email    ：cuiminghao8@gmail.com

import getpass
import paramiko
from netmiko import ConnectHandler, ssh_exception
from netmiko.ssh_autodetect import SSHDetect
from netmiko import Netmiko
import json
import argparse
import pandas as pd
import smtplib
import email.mime.multipart
import email.mime.text
from email.mime.application import MIMEApplication
from distutils.sysconfig import get_python_lib
from multiprocessing import Process
from datetime import datetime
import os
import time, threading
from multiprocessing import Process

MAX_DEPTH = 3
MAX_RETRY = 20
SLEEP_PERIOD = 5
LIB_DIR = get_python_lib()
os.environ["NET_TEXTFSM"] = str(LIB_DIR + "/ntc_templates/templates/")
parser = argparse.ArgumentParser(description='Python Script to parse command output of networking devices and convert '
                                             'it to wonderful csv file then send by mail.')
parser.add_argument('-H', '--hostname', help='Remote hostname', required=True, nargs='+')
parser.add_argument('-U', '--username', help='SSH username', required=True)
parser.add_argument('-S', '--secret', action="store_true", default=None, help='Option to enter privilege mode.Caution '
                                                                              'to use and make sure '
                                                                              'what the commend '
                                                                              'will do.')
parser.add_argument('-C', '--command', help='Commands to be executed. Quote by "" and separated by space',
                    required=True, nargs='+')
parser.add_argument('-R', '--recipient', help='Email address of recipient of csv output file. Optional. Multiple '
                                              'array should be '
                                              'split by ";" ')
args = parser.parse_args()


def email_alert(smtp_server, sender, recipient, results):
    """ Send email of result file in attachment"""
    msg = email.mime.multipart.MIMEMultipart()
    msg['Subject'] = 'Execution result of command output to csv script'
    msg['From'] = sender
    msg['To'] = recipient
    mailobj = smtplib.SMTP(smtp_server)
    for result in results:
        try:
            part = MIMEApplication(open(result, 'rb').read())
        except TypeError:
            return
        part.add_header('Content-Disposition', 'attachment', filename=result)
        msg.attach(part)
    try:
        mailobj.sendmail(sender, recipient, msg.as_string())
        print('Email is sent for the  result to %s' % recipient)
        mailobj.quit()
    except Exception as exc:
        print(str(exc))


class Connection_data(object):
    def __init__(self, username, password, secret):
        self.connections = {}
        self.username = username
        self.password = password
        self.secret = secret
        self.enabled = []

    def get_connection(self, hostname):
        if hostname not in self.connections:
            host_info = {
                'host': hostname,
                'username': self.username,
                'password': self.password,
                'port': 22,
                'device_type': "autodetect",
                'secret': self.secret,
                'banner_timeout': 30
            }
            guesser = SSHDetect(**host_info)
            best_match = guesser.autodetect()
            host_info['device_type'] = best_match
            self.connections[hostname] = Netmiko(**host_info)
        return self.connections[hostname]

    def delete_connection(self, hostname):
        self.connections.pop(hostname, None).disconnect()

    def clear_connection(self):
        keys = list(self.connections.keys())
        for key in keys:
            self.delete_connection(key)

    def get_command_result(self, hostname, command):
        conn = self.get_connection(hostname)
        try:
            output = json.loads(json.dumps(conn.send_command(command, use_textfsm=True), indent=2))
            return output
        except:
            print("Command execute in error")
            return ''

    def enable(self, hostname='', conn=None):
        if hostname in self.enabled:
            return True

        if not conn:
            conn = self.get_connection(hostname)
        for i in range(MAX_RETRY):
            try:
                print('Trying to enable...')
                conn.enable(cmd='enable', pattern='Secret:')
                self.enabled.append(hostname)
                return True
            except:
                if i == MAX_RETRY - 1:
                    print('Retry limit exceeded. Abort.')
                    return False
                else:
                    print('Enable Failed. Retrying in', str(SLEEP_PERIOD), 'seconds')
                    time.sleep(SLEEP_PERIOD)
                    continue


def init():
    global conn_table
    global args
    global user
    global password
    global secret
    LIB_DIR = get_python_lib()
    os.environ["NET_TEXTFSM"] = str(LIB_DIR + "/ntc_templates/templates/")
    parser = argparse.ArgumentParser(
        description='Python Script to parse command output of networking devices and convert '
                    'it to wonderful csv file then send by mail.')
    parser.add_argument('-H', '--hostname', help='Remote hostname', required=True, nargs='+')
    parser.add_argument('-U', '--username', help='SSH username', required=True)
    parser.add_argument('-S', '--secret', action="store_true", default=None,
                        help='Option to enter privilege mode.Caution '
                             'to use and make sure '
                             'what the commend '
                             'will do.')
    parser.add_argument('-C', '--command', help='Commands to be executed. Quote by "" and separated by space',
                        required=True, nargs='+')
    parser.add_argument('-R', '--recipient', help='Email address of recipient of csv output file. Optional. Multiple '
                                                  'array should be '
                                                  'split by ";" ')
    args = parser.parse_args()
    user = args.username
    password = getpass.getpass("Please input SSH password： ")
    if args.secret:
        secret = getpass.getpass("Please input enable password： ")
    else:
        secret = None
    conn_table = Connection_data(user, password, secret)


def abort():
    conn_table.clear_connection()
    exit(1)


def run_commands(hostname, commands):
    for command in commands:
        output = conn_table.get_command_result(hostname, command)
        if isinstance(output, str):
            print("="*10 +hostname+" "+command+" BEGIN "+"="*10)
            print("%s" % output)
            print("=" * 10 + hostname + " " + command + " ENDS " + "=" * 10)
            continue
        start_prompt_count = int(len(str(output[0])) / 2 - ((len(str(hostname)) + len(str(command))) + 8) / 2)
        end_prompt_count = int(len(str(output[-1])) / 2 - ((len(str(hostname)) + len(str(command))) + 8) / 2)
        print("=" * start_prompt_count + hostname + " " + " " + command + " BEGIN " + "=" * start_prompt_count)
        for info in output:
            print(info)
        print("=" * end_prompt_count + hostname + " " + " " + command + " END " + "=" * end_prompt_count)
        normalized_df = pd.json_normalize(output)
        normalized_df.to_csv(hostname + "_" + command + '.csv', index=False)


def name():
    file_name = []
    a = os.listdir()
    for j in a:
        if os.path.splitext(j)[1] == '.csv':
            file_name.append(j)
    return file_name


def main():
    start_time = datetime.now()
    init()
    for hostname in args.hostname:
        run_commands(hostname, args.command)
    file_name = name()
    #print(file_name)
    email_alert(smtp_server='', sender='', recipient=args.recipient,
                results=file_name)
    for filename in file_name:
        os.remove(filename)
    end_time = datetime.now()
    print("%s %s"%(start_time,end_time))
    abort()


if __name__ == "__main__":
    main()
