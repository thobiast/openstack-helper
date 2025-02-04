# -*- coding: utf-8 -*-
"""
openstack-helper - check instance allocations

This module retrieves allocation information from Nova and Placement for one or more
instances, computes a status based on allocation consistency, and displays the results
in a single table using Rich if available or plain text.
"""
import logging
from dataclasses import dataclass

import openstack

from openstack_helper.common import RICH_AVAILABLE, Console, Table


@dataclass
class VmAlloc:
    """Data class representing server (VM) allocations."""

    vm_id: str
    vm_name: str
    nova_compute_host: str
    nova_hypervisor_hostname: str
    placement_alloc: dict

    @property
    def status(self) -> str:
        """
        Compute the status based on the following criteria:
          - "OK" if either:
              * There is no data from Nova and Placement (i.e. vm_name, nova_compute_host,
                and nova_hypervisor_hostname are None and placement_alloc is empty).
                This behavior is a design choice to treat a completely missing record
                as non-problematic.
              * nova_compute_host equals nova_hypervisor_hostname, and
                placement_alloc has exactly one key that matches nova_compute_host.
          - Otherwise, "Not OK".

        Returns:
            "OK" or "Not OK" based on the conditions above.
        """
        # If there is no data in Nova nor in Placement, consider it OK.
        if (
            self.vm_name is None
            and self.nova_compute_host is None
            and self.nova_hypervisor_hostname is None
            and len(self.placement_alloc) == 0
        ):
            return "OK"

        # Check if Nova data is valid and consistent with Placement allocation.
        if (
            self.nova_compute_host == self.nova_hypervisor_hostname
            and self.placement_alloc is not None
            and len(self.placement_alloc) == 1
            and list(self.placement_alloc.keys())[0] == self.nova_compute_host
        ):
            return "OK"

        return "Not OK"


def check_nova_allocation(openstack_api, vm_uuid):
    """
    Retrieve Nova allocation details for a given instance.

    Args:
        openstack_api: An instance of the OpenStackAPI.
        vm_uuid: The UUID of the virtual machine.

    Returns:
        A tuple containing (vm_id, vm_name, nova_compute_host, nova_hypervisor_hostname),
        or (None, None, None, None) if the server is not found.
    """
    try:
        server = openstack_api.compute.find_server(
            vm_uuid, ignore_missing=False, details=False
        )
        logging.debug(
            "Retrieving Nova allocation for instance: %s (%s)", server.id, server.name
        )
        return (server.id, server.name, server.compute_host, server.hypervisor_hostname)
    except openstack.exceptions.ResourceNotFound:
        logging.warning("No Nova instance found with UUID '%s'", vm_uuid)
        return (None, None, None, None)


def check_placement_allocation(openstack_api, vm_uuid):
    """
    Retrieve placement allocations for a given instance.

    Args:
        openstack_api: An instance of the OpenStackAPI.
        vm_uuid: The UUID of the virtual machine.

    Returns:
        A dictionary mapping resource provider names to their allocation resources.
    """
    allocations = openstack_api.placement.retrieve_provider_allocations_for_instance(vm_uuid)
    logging.debug("Instance: %s Resource provider allocations found: %s", vm_uuid, allocations)

    placement = {}
    for rp_id, alloc in allocations.items():
        logging.debug("Getting info about resource provider: %s", rp_id)
        try:
            rp = openstack_api.placement.find_resource_provider(rp_id, ignore_missing=False)
            placement[rp.name] = alloc.get("resources", {})
        except openstack.exceptions.NotFoundException:
            logging.warning("Resource provider with ID %s not found", rp_id)
            # If the resource provider is not found, fallback to using its ID as the key.
            placement[rp_id] = alloc.get("resources", {})

    logging.debug("Instance: %s Placement allocations found: %s", vm_uuid, placement)
    return placement


def check_allocations(openstack_api, vm_uuids):
    """
    Retrieve allocation details from both Nova and Placement for multiple instances.

    For each instance (identified by its UUID), the function:
      1. Queries the Nova API to obtain the server's details.
      2. Queries the Placement API to obtain resource provider allocations.
      3. Constructs a VmAlloc instance containing the collected data.

    Args:
        openstack_api: An instance of the OpenStackAPI.
        vm_uuids: A list of instance UUID strings.

    Returns:
        A list of VmAlloc objects containing allocation details and a computed status.
    """
    results = []
    for vm_uuid in vm_uuids:
        nova_alloc = check_nova_allocation(openstack_api, vm_uuid)
        logging.debug("Server nova compute host: %s", nova_alloc)
        vm_id, vm_name, nova_compute_host, nova_hypervisor_hostname = nova_alloc

        placement_alloc = check_placement_allocation(openstack_api, vm_uuid)
        logging.debug("Server placement allocation: %s", placement_alloc)

        vm_alloc = VmAlloc(
            # Use vm_uuid as the VM ID since the instance may not exist in Nova.
            vm_id=vm_id if vm_id else vm_uuid,
            vm_name=vm_name,
            nova_compute_host=nova_compute_host,
            nova_hypervisor_hostname=nova_hypervisor_hostname,
            placement_alloc=placement_alloc,
        )
        results.append(vm_alloc)

    return results


def display_allocations(results):
    """
    Display the list of VmAlloc results using Rich if available, or plain text.

    Args:
        results: A list of VmAlloc objects to display.
    """
    if RICH_AVAILABLE:
        console = Console()
        table = Table(show_header=True)
        table.add_column("Instance ID", style="magenta", no_wrap=True)
        table.add_column("VM Name", style="blue")
        table.add_column("Nova Allocation", style="cyan", no_wrap=True)
        table.add_column("Placement Allocation", style="cyan")
        table.add_column("Status", style="yellow")
        for alloc in results:
            vm_name_str = alloc.vm_name or "N/A"
            nova_alloc_str = (
                f"compute_host: {alloc.nova_compute_host or 'N/A'}, "
                f"hypervisor: {alloc.nova_hypervisor_hostname or 'N/A'}"
            )
            placement_alloc_str = (
                str(alloc.placement_alloc) if alloc.placement_alloc else "N/A"
            )
            color = "green" if alloc.status == "OK" else "red"
            status_str = f"[{color}]{alloc.status}[/{color}]"
            table.add_row(
                alloc.vm_id, vm_name_str, nova_alloc_str, placement_alloc_str, status_str
            )
        console.print(table)
    else:
        print("---- Allocations for Instances ----")
        for alloc in results:
            print(f"Instance: {alloc.vm_id} ({alloc.vm_name})")
            print(
                f"  - Nova allocation: compute_host: {alloc.nova_compute_host},"
                f" hypervisor: {alloc.nova_hypervisor_hostname}"
            )
            print(f"  - Placement allocation: {alloc.placement_alloc}")
            print(f"  - Check: {alloc.status}")
            print("-" * 40)


def handle_check_allocations_cmd(openstack_api, args):
    """
    Handle the 'check_allocations' subcommand.

    Args:
        openstack_api (OpenStackAPI): Instance of OpenStackAPI.
        args (argparse.Namespace): Parsed command-line arguments.
           - uuid: A string of one or more comma-separated UUIDs.
    """
    vm_uuids = args.uuid.split(",")
    results = check_allocations(openstack_api, vm_uuids)
    display_allocations(results)


# vim: ts=4 sw=4 expandtab
