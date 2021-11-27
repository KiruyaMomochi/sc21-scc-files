# Code borrowed from https://github.com/Azure/WALinuxAgent
# Copyright 2018 Microsoft Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#

import xml.dom.minidom as minidom
import os
import re
import subprocess
import threading

_running_commands = []
_running_commands_lock = threading.RLock()

def _popen(*args, **kwargs):
    with _running_commands_lock:
        process = subprocess.Popen(*args, **kwargs)
        _running_commands.append(process.pid)
        return process


def _on_command_completed(pid):
    with _running_commands_lock:
        _running_commands.remove(pid)

def __format_command(command):
    """
    Formats the command taken by run_command/run_pipe.

    Examples:
        > __format_command("sort")
        'sort'
        > __format_command(["sort", "-u"])
        'sort -u'
        > __format_command([["sort"], ["unique", "-n"]])
        'sort | unique -n'
    """
    if isinstance(command, list):
        if command and isinstance(command[0], list):
            return " | ".join([" ".join(cmd) for cmd in command])
        return " ".join(command)
    return command


def __encode_command_output(output):
    """
    Encodes the stdout/stderr returned by subprocess.communicate()
    """
    return output if output is not None else b''


class CommandError(Exception):
    """
    Exception raised by run_command/run_pipe when the command returns an error
    """
    @staticmethod
    def _get_message(command, return_code, stderr):
        command_name = command[0] if isinstance(command, list) and len(command) > 0 else command
        return "'{0}' failed: {1} ({2})".format(command_name, return_code, stderr.rstrip())

    def __init__(self, command, return_code, stdout, stderr):
        super(Exception, self).__init__(CommandError._get_message(command, return_code, stderr))  # pylint: disable=E1003
        self.command = command
        self.returncode = return_code
        self.stdout = stdout
        self.stderr = stderr

def __run_command(command_action, command, log_error, encode_output):
    """
    Executes the given command_action and returns its stdout. The command_action is a function that executes a command/pipe
    and returns its exit code, stdout, and stderr.

    If there are any errors executing the command it raises a RunCommandException; if 'log_error'
    is True, it also logs details about the error.

    If encode_output is True the stdout is returned as a string, otherwise it is returned as a bytes object.
    """
    try:
        return_code, stdout, stderr = command_action()

        if encode_output:
            stdout = __encode_command_output(stdout)
            stderr = __encode_command_output(stderr)

        if return_code != 0:
            if log_error:
                logger.error(
                    "Command: [{0}], return code: [{1}], stdout: [{2}] stderr: [{3}]",
                    __format_command(command),
                    return_code,
                    stdout,
                    stderr)
            raise CommandError(command=__format_command(command), return_code=return_code, stdout=stdout, stderr=stderr)

        return stdout

    except CommandError:
        raise
    except Exception as exception:
        if log_error:
            logger.error(u"Command [{0}] raised unexpected exception: [{1}]", __format_command(command), exception)
        raise


# W0622: Redefining built-in 'input'  -- disabled: the parameter name mimics subprocess.communicate()
def run_command(command, input=None, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, log_error=False, encode_input=True, encode_output=True, track_process=True):  # pylint:disable=W0622
    """
        Executes the given command and returns its stdout.

        If there are any errors executing the command it raises a RunCommandException; if 'log_error'
        is True, it also logs details about the error.

        If encode_output is True the stdout is returned as a string, otherwise it is returned as a bytes object.

        If track_process is False the command is not added to list of running commands

        This function is a thin wrapper around Popen/communicate in the subprocess module:
           * The 'input' parameter corresponds to the same parameter in communicate
           * The 'stdin' parameter corresponds to the same parameters in Popen
           * Only one of 'input' and 'stdin' can be specified
           * The 'stdout' and 'stderr' parameters correspond to the same parameters in Popen, except that they
             default to subprocess.PIPE instead of None
           * If the output of the command is redirected using the 'stdout' or 'stderr' parameters (i.e. if the
             value for these parameters is anything other than the default (subprocess.PIPE)), then the corresponding
             values returned by this function or the CommandError exception will be empty strings.

        Note: This is the preferred method to execute shell commands over `azurelinuxagent.common.utils.shellutil.run` function.
    """
    if input is not None and stdin is not None:
        raise ValueError("The input and stdin arguments are mutually exclusive")

    def command_action():
        popen_stdin = communicate_input = None
        if input is not None:
            popen_stdin = subprocess.PIPE
            communicate_input = input.encode() if encode_input and isinstance(input, str) else input  # communicate() needs an array of bytes
        if stdin is not None:
            popen_stdin = stdin
            communicate_input = None

        if track_process:
            process = _popen(command, stdin=popen_stdin, stdout=stdout, stderr=stderr, shell=False)
        else:
            process = subprocess.Popen(command, stdin=popen_stdin, stdout=stdout, stderr=stderr, shell=False)

        command_stdout, command_stderr = process.communicate(input=communicate_input)
        if track_process:
            _on_command_completed(process.pid)

        return process.returncode, command_stdout, command_stderr

    return __run_command(command_action=command_action, command=command, log_error=log_error, encode_output=encode_output)

class logger(object):
    def __init__(self):
        pass

    @staticmethod
    def verbose(*args, **kwargs):
        print(args, kwargs)

    @staticmethod
    def error(*args, **kwargs):
        print(args, kwargs)

    @staticmethod
    def info(*args, **kwargs):
        print(args, kwargs)

def parse_doc(xml_text):
    """
    Parse xml document from string
    """
    # The minidom lib has some issue with unicode in python2.
    # Encode the string into utf-8 first
    xml_text = xml_text.encode('utf-8')
    return minidom.parseString(xml_text)


def find(root, tag, namespace=None):
    """
    Get first node by tag and namespace under Node root.
    """
    nodes = findall(root, tag, namespace=namespace)
    if nodes is not None and len(nodes) >= 1:
        return nodes[0]
    else:
        return None

def gettext(node):
    """
    Get node text
    """
    if node is None:
        return None

    for child in node.childNodes:
        if child.nodeType == child.TEXT_NODE:
            return child.data
    return None


def findtext(root, tag, namespace=None):
    """
    Get text of node by tag and namespace under Node root.
    """
    node = find(root, tag, namespace=namespace)
    return gettext(node)


def getattrib(node, attr_name):
    """
    Get attribute of xml node
    """
    if node is not None:
        return node.getAttribute(attr_name)
    else:
        return None

def findall(root, tag, namespace=None):
    """
    Get all nodes by tag and namespace under Node root.
    """
    if root is None:
        return []

    if namespace is None:
        return root.getElementsByTagName(tag)
    else:
        return root.getElementsByTagNameNS(namespace, tag)

def setup_rdma_device(nd_version, shared_conf):
    logger.verbose("Parsing SharedConfig XML contents for RDMA details")
    xml_doc = parse_doc(shared_conf)
    if xml_doc is None:
        logger.error("Could not parse SharedConfig XML document")
        return
    instance_elem = find(xml_doc, "Instance")
    if not instance_elem:
        logger.error("Could not find <Instance> in SharedConfig document")
        return

    rdma_ipv4_addr = getattrib(instance_elem, "rdmaIPv4Address")
    if not rdma_ipv4_addr:
        logger.error(
            "Could not find rdmaIPv4Address attribute on Instance element of SharedConfig.xml document")
        return

    rdma_mac_addr = getattrib(instance_elem, "rdmaMacAddress")
    if not rdma_mac_addr:
        logger.error(
            "Could not find rdmaMacAddress attribute on Instance element of SharedConfig.xml document")
        return

    # add colons to the MAC address (e.g. 00155D33FF1D ->
    # 00:15:5D:33:FF:1D)
    # rdma_mac_addr = ':'.join([rdma_mac_addr[i:i + 2]
    #                           for i in range(0, len(rdma_mac_addr), 2)])
    print("Found RDMA details. IPv4={0} MAC={1}".format(
        rdma_ipv4_addr, rdma_mac_addr))

    update_iboip_interfaces([(rdma_mac_addr, rdma_ipv4_addr)])

    logger.info("RDMA: device is set up")
    return

def update_iboip_interfaces(mac_ip_array):

    net_dir = "/sys/class/net"
    nics = os.listdir(net_dir)
    count = 0

    for nic in nics:
        # look for IBoIP interface of format ibXXX
        if not re.match(r"ib\w+", nic):
            continue

        mac_addr = None
        with open(os.path.join(net_dir, nic, "address")) as address_file:
            mac_addr = address_file.read()

        if not mac_addr:
            logger.error("RDMA: can't read address for device {0}".format(nic))
            continue

        mac_addr = mac_addr.upper()

        match = re.match(r".+(\w\w):(\w\w):(\w\w):\w\w:\w\w:(\w\w):(\w\w):(\w\w)\n", mac_addr)
        if not match:
            logger.error("RDMA: failed to parse address for device {0} address {1}".format(nic, mac_addr))
            continue

        # format an MAC address without :
        mac_addr = ""
        mac_addr = mac_addr.join(match.groups(0))

        for mac_ip in mac_ip_array:
            print('mac_ip', mac_ip)
            if mac_ip[0] == mac_addr:
                ret = 0
                try:
                    # bring up the interface and set its IP address
                    ip_command = ["ip", "link", "set", nic, "up"]
                    print(ip_command)
                    run_command(ip_command)

                    ip_command = ["ip", "addr", "add", "{0}/16".format(mac_ip[1]), "dev", nic]
                    print(ip_command)
                    run_command(ip_command)
                except CommandError as error:
                    ret = error.returncode

                if ret == 0:
                    logger.info("RDMA: set address {0} to device {1}".format(mac_ip[1], nic))

                if ret and ret != 2:
                    # return value 2 means the address is already set
                    logger.error("RDMA: failed to set IP address {0} on device {1}".format(mac_ip[1], nic))
                else:
                    count += 1

                break

    return count

shared_conf = "/var/lib/waagent/SharedConfig.xml"
with open(shared_conf) as f:
    shared_conf_text = f.read()
    setup_rdma_device(2, shared_conf_text)
