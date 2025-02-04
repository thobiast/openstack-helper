# -*- coding: utf-8 -*-
"""
openstack-helper - unused_ports command
"""
import concurrent.futures
import logging

from openstack_helper.common import ping_ip_address

try:
    from rich.console import Console
    from rich.tree import Tree

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


def ping_port_ip_addresses(port):
    """
    Check if any IP address associated with the port is reachable via ping.

    Args:
        port (Port): The OpenStack Port object containing a list of fixed IPs
            (port.fixed_ips).

    Returns:
        bool: True if any of the IPs are reachable, False otherwise.
    """
    ip_addr_list = [ip["ip_address"] for ip in port.fixed_ips]

    if not ip_addr_list:
        logging.debug("No IP addresses found to ping; skipping ping check")
        return False

    for ip in ip_addr_list:
        if ping_ip_address(ip):
            logging.info("Ping succeeded for IP address: %s", ip)
            return True
        logging.info("Ping failed for IP address: %s", ip)

    return False


def filter_ports_by_ping(eligible_ports, max_workers):
    """
    Perform ping checks on eligible ports and remove ports whose IP addresses
    are reachable via ping.

    Args:
        eligible_ports (list): Ports to check for reachability.
        max_workers (int): Maximum number of worker threads for concurrent ping operations.

    Returns:
        list: Ports whose IP addresses are not reachable via ping.
    """
    if not eligible_ports:
        logging.debug("No eligible ports to ping")
        return []

    logging.debug("Starting concurrent ping checks on eligible ports")

    num_workers = min(max_workers, len(eligible_ports))
    logging.debug("Using %s threads", num_workers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        future_to_port = {
            executor.submit(ping_port_ip_addresses, port): port for port in eligible_ports
        }

        # Collect ports that remain eligible after ping checks
        final_eligible_ports = []
        for future in concurrent.futures.as_completed(future_to_port):
            port = future_to_port[future]
            try:
                is_port_ip_reachable = future.result()
                if not is_port_ip_reachable:
                    final_eligible_ports.append(port)
            except concurrent.futures.TimeoutError as e:
                logging.error("Error processing port %s: %s", port.id, e)

    return final_eligible_ports


def is_port_eligible(port, device_owner):
    """
    Check if a port is eligible for deletion based on status,
    binding details, and device owner.

    Args:
        port (Port): An OpenStack port object to evaluate.
        device_owner (str): Expected device owner to filter ports.

    Returns:
        bool: True if the port is eligible for deletion, False otherwise.
    """
    checks = [
        (port.status.upper() == "DOWN", f"Port status is DOWN. Value: '{port.status}'"),
        (
            not port.binding_host_id,
            f"Port has no binding_host_id. Value: '{port.binding_host_id}'",
        ),
        (
            not port.binding_vif_details,
            f"Port has no binding_vif_details. Value: '{port.binding_vif_details}'",
        ),
        (
            port.binding_vif_type == "unbound",
            f"Port binding_vif_type is 'unbound'. Value: '{port.binding_vif_type}'",
        ),
        (
            port.device_owner == device_owner,
            f"Port device_owner matches expected. Value: '{port.device_owner}'",
        ),
    ]

    is_eligible = True

    logging.debug("#####################################################")
    logging.debug("### Checking port: %s (%s)", port.id, port.name)

    for condition, message in checks:
        if condition:
            logging.debug("Check Passed: %s", message)
        else:
            logging.debug("Check Failed: %s", message)
            is_eligible = False

    if is_eligible:
        logging.debug("Port eligible for deletion after initial checks")

    return is_eligible


def filter_unused_ports(ports, device_owner, ping=False, max_workers=20):
    """
    Identify ports that are unused and eligible for deletion.

    Args:
        ports (list): List of ports to check.
        device_owner (str): Expected device owner to filter ports.
        ping (bool): Whether to perform a ping check on the port's IP addresses.
        max_workers (int): Maximum number of worker threads for concurrent ping operations.
                           Defaults to 20.

    Returns:
        List of ports eligible for deletion.
    """

    # Step 1: Initial Filtering
    eligible_ports = [port for port in ports if is_port_eligible(port, device_owner)]

    # Step 2: Ping Check (if enabled)
    if ping and eligible_ports:
        eligible_ports = filter_ports_by_ping(eligible_ports, max_workers)

    return eligible_ports


def show_unused_ports(eligible_ports):
    """
    Display the details of OpenStack ports that are eligible for deletion.

    This function presents a list of ports in a human-readable format.
    If the 'rich' library is available, the output is displayed as a rich
    hierarchical tree structure with detailed attributes. If 'rich' is not
    available, it prints a simple textual representation.

    Args:
        eligible_ports (list): A list of OpenStack port objects that are
                               eligible for deletion, as determined by prior
                               filtering.

    Returns:
        None: The function prints the output directly to stdout.
    """
    port_attributes = [
        "id",
        "name",
        "description",
        "status",
        "binding_host_id",
        "binding_vif_details",
        "binding_vif_type",
        "device_owner",
        "dns_assignment",
        "fixed_ips",
        "updated_at",
    ]

    if RICH_AVAILABLE:
        console = Console()
        tree = Tree("Ports Eligible for Deletion")

        for port in eligible_ports:
            port_id = f"[bold cyan]{port.id}[/bold cyan]"
            port_tree = tree.add(port_id)
            for attr in port_attributes:
                value = getattr(port, attr, "")
                attr_name = attr.replace("_", " ").title()
                port_tree.add(f"[green]{attr_name}[/green]: {value}")

        console.print(tree)
    else:
        for port in eligible_ports:
            print(f"-- {port.id}")
            for attr in port_attributes:
                value = getattr(port, attr, None)
                print(f"   |-- {attr}: {value}")


def handle_unused_ports_cmd(openstack_api, args):
    """
    Handle the 'unused_ports' subcommand.

    Args:
        openstack_api (OpenStackAPI): Instance of OpenStackAPI.
        args (argparse.Namespace): Parsed command-line arguments.

    Raises:
        ValueError: If --max-workers is set to a value outside the range 1-100.
    """
    if args.max_workers < 1 or args.max_workers > 100:
        raise ValueError("Invalid value for --max-workers. It must be between 1 and 100.")

    # Prepare the query parameters
    query_params = {
        "device_owner": args.device_owner,
        "project_id": openstack_api.os_conn.current_project_id,
        "status": "DOWN",
        "network_id": args.network_id,
    }
    logging.debug("Retrieving ports with query params: %s", query_params)

    ports = openstack_api.network.retrieve_ports(**query_params)
    if not ports:
        logging.debug("No ports found using query parameter: %s", query_params)
        print("No ports found matching the specified criteria.")
        return

    eligible_ports = filter_unused_ports(
        ports, args.device_owner, args.ping, max_workers=args.max_workers
    )
    if eligible_ports:
        show_unused_ports(eligible_ports)

    print("Summary")
    print("-------")
    print(f"Total ports processed: {len(ports)}")
    print(f"Total ports eligible for deletion: {len(eligible_ports)}")


# vim: ts=4 sw=4 expandtab
