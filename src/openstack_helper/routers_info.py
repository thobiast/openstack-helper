# -*- coding: utf-8 -*-
"""
openstack-helper - Router's info
"""
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from openstack_helper.common import RICH_AVAILABLE, Console, Group, Table, Text, Tree


@dataclass
class PortInfo:
    """Class to store a Neutron port attached to a router."""

    id: str
    status: str
    network_id: str
    fixed_ips: list[dict]


@dataclass
class RouterInfo:
    """Aggregated, display-oriented router structure."""

    id: str
    name: str
    status: str
    updated_at: str
    is_distributed: bool
    external_gateway_info: Optional[dict]
    ports: list[PortInfo]


def render_ports(ports, network_map):
    """
    Render ports grouped by network as a Rich tree.

    Args:
        ports: Iterable of PortInfo to render.
        network_map: Mapping of network_id -> human-friendly network name.

    Returns:
        A Rich renderable (Group or Text) suitable for printing inside a table.
        Returns a dimmed "-" when there are no ports.
    """
    if not ports:
        return Text("-", style="dim")

    ports_by_net = defaultdict(list)
    for port in ports:
        ports_by_net[port.network_id].append(port)

    network_trees = []
    for net_id, net_ports in ports_by_net.items():
        network_name = network_map.get(net_id, "Unknown Network")
        network_header = Text.assemble(
            ("Network: ", "bold"),
            (net_id or "N/A", "magenta"),
            (f" ({network_name})", "dim magenta"),
        )
        tree = Tree(network_header)

        for port in net_ports:
            port_label = Text.assemble(
                ("Port: ", "bold"),
                (port.id, "cyan"),
                (" (", "dim"),
                (port.status, "green" if port.status == "ACTIVE" else "red"),
                (")", "dim"),
            )
            port_branch = tree.add(port_label)
            for ip_info in port.fixed_ips:
                ip_label = Text.assemble(
                    ("IP: ", "bold"),
                    (ip_info.get("ip_address", "N/A"), "bright_green"),
                    (" | Subnet: ", "dim"),
                    (ip_info.get("subnet_id", "N/A"), "yellow"),
                )
                port_branch.add(ip_label)
        network_trees.append(tree)

    return Group(*network_trees)


def render_gateway_info(gw_info, network_map):
    """
    Render the router's external gateway info as styled Rich text.

    Args:
        gw_info: Dict with Neutron external_gateway_info or None.
        network_map: Mapping of network_id -> network name.

    Returns:
        A Rich renderable (Group or Text) summarizing the gateway info, or
        a dimmed "-" when no gateway is present.
    """
    if not gw_info:
        return Text("-")

    network_id = gw_info.get("network_id", "")
    network_name = network_map.get(network_id, "Unknown Network")
    enable_snat = gw_info.get("enable_snat")
    ext_fixed_ips = gw_info.get("external_fixed_ips", [])

    header = Text.assemble(
        ("network_id: ", "bold"),
        (network_id, "magenta"),
        (f" ({network_name})", "dim magenta"),
    )
    snat_label = Text("True", "green") if enable_snat else Text("False", "red")
    snat_line = Text.assemble(("enable_snat: ", "bold"), snat_label)

    if ext_fixed_ips:
        ip_lines = []
        for ip_info in ext_fixed_ips:
            ip_address = ip_info.get("ip_address", "N/A")
            subnet_id = ip_info.get("subnet_id", "N/A")

            ip_lines.append(
                Text.assemble(("  - ip_address: ", "default"), (ip_address, "green"))
            )
            ip_lines.append(
                Text.assemble(("    subnet_id: ", "default"), (subnet_id, "yellow"))
            )

        ip_addr_renderable = Group(Text("external_fixed_ips:", style="bold"), *ip_lines)
    else:
        ip_addr_renderable = Text.assemble(("external_fixed_ips: ", "bold"), ("-", "dim"))

    return Group(header, snat_line, ip_addr_renderable)


def _get_ports_for_router(openstack_api, router_id):
    """
    Fetch ports for a router and structure them as PortInfo objects.

    Args:
        openstack_api (OpenStackAPI): Instance of OpenStackAPI.
        router_id: The router UUID whose ports should be retrieved.

    Returns:
        List of PortInfo derived from the SDK port resources.
    """
    ports_info = []
    query_params = {"device_id": router_id}
    for port in openstack_api.network.retrieve_ports(**query_params):
        ports_info.append(
            PortInfo(
                id=port.id,
                status=port.status or "N/A",
                network_id=port.network_id or "",
                fixed_ips=port.fixed_ips or [],
            )
        )
    return ports_info


def get_all_router_data(openstack_api, router_ids, router_names):
    """
    Collect routers (optionally filtered) and gather related network IDs.

    For each router, this pulls its external gateway info and attached ports,
    recording all network IDs.

    Args:
        openstack_api (OpenStackAPI): Instance of OpenStackAPI.
        router_ids: Optional list of router UUIDs to filter by.
        router_names: Optional list of router names to filter by.

    Returns:
        A tuple of:
            - routers_info: List of RouterInfo.
            - all_network_ids: Set of network UUIDs referenced by routers/ports.
    """

    routers_info = []
    all_network_ids = set()

    query_params = {}
    if router_ids:
        query_params["id"] = router_ids
    if router_names:
        query_params["name"] = router_names
    logging.debug("Getting routers with filter: %s", query_params)

    for router in openstack_api.network.list_routers(**query_params):
        gateway_info = router.external_gateway_info or None
        if gateway_info:
            network_id = gateway_info.get("network_id", None)
            if network_id:
                all_network_ids.add(network_id)

        ports = _get_ports_for_router(openstack_api, router.id)
        for port in ports:
            if port.network_id:
                all_network_ids.add(port.network_id)

        routers_info.append(
            RouterInfo(
                id=router.id,
                name=router.name,
                status=router.status,
                updated_at=router.updated_at,
                is_distributed=router.is_distributed,
                external_gateway_info=gateway_info,
                ports=ports,
            )
        )
    return routers_info, all_network_ids


def handle_routers_info_cmd(openstack_api, args):
    """
    Handle the 'routers_info' subcommand.

    Args:
        openstack_api (OpenStackAPI): Instance of OpenStackAPI.
        args (argparse.Namespace): Parsed command-line arguments.
           - uuid: A string of one or more comma-separated UUIDs.
    """

    router_ids = args.uuid.split(",") if args.uuid else None
    router_names = args.name.split(",") if args.name else None

    if not RICH_AVAILABLE:
        print("Install Rich library to use this command")
        return

    console = Console()
    with console.status("[bold green]Fetching router information..."):
        all_routers, all_network_ids = get_all_router_data(
            openstack_api, router_ids, router_names
        )

    if not all_routers:
        console.print("[yellow]No routers found.[/yellow]")
        return

    network_map = {}
    if all_network_ids:
        with console.status("[bold green]Fetching network information..."):
            for network_id in all_network_ids:
                network = openstack_api.network.find_network(network_id)
                network_map[network_id] = network.name

    table = Table(show_header=True, padding=(0, 0), show_lines=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Updated At", style="yellow")
    table.add_column("Distributed", style="blue", justify="center")
    table.add_column("Gateway Info", style="white")
    table.add_column("Ports", style="white")

    for router in all_routers:
        is_dist_label = (
            Text("True", "green") if router.is_distributed else Text("False", "red")
        )
        router_status_label = Text(
            router.status, style="green" if router.status == "ACTIVE" else "red"
        )

        table.add_row(
            router.id,
            router.name,
            router_status_label,
            router.updated_at,
            is_dist_label,
            render_gateway_info(router.external_gateway_info, network_map),
            render_ports(router.ports, network_map),
        )

    console.print(table)


# vim: ts=4 sw=4 expandtab
