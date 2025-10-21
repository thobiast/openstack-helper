# -*- coding: utf-8 -*-
"""
openstack-helper - utils
"""
import ipaddress
import logging
import subprocess  # nosec B404
import uuid

try:
    from rich.console import Console, Group
    from rich.table import Table
    from rich.text import Text
    from rich.tree import Tree

    RICH_AVAILABLE = True
    __all__ = ["RICH_AVAILABLE", "Console", "Group", "Table", "Text", "Tree"]
except ImportError:
    RICH_AVAILABLE = False
    Console = None
    Group = None
    Table = None
    Text = None
    Tree = None
    __all__ = ["RICH_AVAILABLE", "Console", "Group", "Table", "Text", "Tree"]


def is_valid_uuid(uuid_str):
    """
    Check if uuid_str parameter is a valid UUID.

    Args:
        uuid_str (str): The value to check.

    Returns:
        bool: True if valid UUID, False otherwise.
    """
    try:
        uuid.UUID(str(uuid_str))
        return True
    except ValueError:
        return False


def is_valid_ip_address(address):
    """
    Check if the address parameter is a valid IP address.

    Args:
        address (str): The IP address to validate.

    Returns:
        bool: True if valid IP address, False otherwise.
    """
    try:
        ipaddress.ip_address(address)
        return True
    except ValueError:
        return False


def ping_ip_address(ip, timeout=1):
    """
    Ping an IP address to check if it is reachable.

    Args:
        ip (str): The IP address to ping.
        timeout (int): The timeout duration in seconds for the ping command.
                       Defaults to 1 second.

    Returns:
        bool: True if the IP address responds to ping, False otherwise.
    """
    logging.debug("Trying to ping: %s", ip)

    if not is_valid_ip_address(ip):
        logging.error("Invalid IP address: %s", ip)
        return False

    command = ["ping", "-c", "1", "-W", str(int(timeout)), ip]

    try:
        output = subprocess.run(
            command,
            shell=False,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )  # nosec B603
        return output.returncode == 0
    except (FileNotFoundError, PermissionError) as e:
        logging.error("Error executing ping command: %s", e)
        return False
    except OSError as e:
        logging.error("OS error occurred while pinging %s: %s", ip, e)
        return False


# vim: ts=4 sw=4 expandtab
