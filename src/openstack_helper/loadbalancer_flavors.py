# -*- coding: utf-8 -*-
"""
openstack-helper - load balancer flavor

This module provides functionality for retrieving and displaying
OpenStack load balancer flavors, along with their associated
flavor profiles and compute flavors.
"""
import json
import logging
from dataclasses import asdict, dataclass
from typing import Optional

from openstack_helper.common import RICH_AVAILABLE, Console, Table, Tree


@dataclass
class ComputeFlavor:
    """
    Data class representing a compute flavor

    Attributes:
        id (str): The uuid for the compute flavor
        name (str): The name of the compute flavor
        vcpus (int): Number of vCPUs
        ram (int): Amount of RAM
        disk (int): Disk size
    """

    id: str
    name: str
    vcpus: int
    ram: int
    disk: int


@dataclass
class FlavorProfile:
    """
    Data class representing a flavor profile.

    Attributes:
        id (str): The uuid for the flavor profile
        name (str): The name of the flavor profile
        provider_name (str): The provider name associated with the flavor profile
        flavor_data (str): A JSON string containing additional flavor data
    """

    id: str
    name: str
    provider_name: str
    flavor_data: str

    def get_compute_flavor_id(self):
        """
        Parse the flavor_data JSON and retrieve the compute flavor ID

        Returns:
            The compute flavor ID if present; otherwise, None
        """
        try:
            data = json.loads(self.flavor_data)
        except json.JSONDecodeError as e:
            logging.error("Error decoding flavor_data for flavor profile %s: %s", self.id, e)
            return None

        compute_flavor = data.get("compute_flavor")
        if not compute_flavor:
            logging.warning("Flavor profile %s missing 'compute_flavor' key.", self.id)

        return compute_flavor


@dataclass
class Flavor:
    """
    Data class representing a load balancer flavor

    Attributes:
        id (str): The uuid for the flavor
        name (str): The name of the flavor
        description (str): A description of the flavor
        is_enabled (bool): Indicates whether the flavor is enabled
        flavor_profile (Optional[FlavorProfile]): Associated flavor profile information
        compute_flavor (Optional[ComputeFlavor]): Associated compute flavor information
    """

    id: str
    name: str
    description: str
    is_enabled: bool
    flavor_profile: Optional[FlavorProfile] = None
    compute_flavor: Optional[ComputeFlavor] = None

    def get_basic_info(self):
        """
        Return a tuple of basic information for display

        Returns:
            A tuple (flavor_id, name, description, enabled, profile_info, compute_info)
        """
        flavor_id = self.id
        name = self.name
        description = self.description
        enabled = str(self.is_enabled)
        profile_info = (
            f"{self.flavor_profile.name} (Provider: {self.flavor_profile.provider_name})"
            if self.flavor_profile
            else "N/A"
        )
        compute_info = (
            f"{self.compute_flavor.name} "
            f"(Resources: vCPUs:{self.compute_flavor.vcpus} RAM:{self.compute_flavor.ram})"
            if self.compute_flavor
            else "N/A"
        )
        return flavor_id, name, description, enabled, profile_info, compute_info

    def get_detailed_info(self):
        """
        Return a dictionary of detailed information for display

        This includes all basic fields plus all details from the associated objects

        Returns:
            dict: A dictionary where keys are field names (with prefixes) and
                values are their corresponding values
        """
        info = {}

        # Convert the flavor dataclass to a dict and merge it into info.
        flavor_dict = asdict(self)
        for key, value in flavor_dict.items():
            # Do not add flavor profile and compute flavor in the flavor level
            if key in ["flavor_profile", "compute_flavor"]:
                continue
            info[f"Flavor {key.capitalize()}"] = value

        if self.flavor_profile:
            # Convert the flavor_profile dataclass to a dict and merge it into info.
            fp_dict = asdict(self.flavor_profile)
            for key, value in fp_dict.items():
                info[f"Flavor_Profile {key.capitalize()}"] = value
        else:
            info["Flavor_Profile"] = "N/A"

        if self.compute_flavor:
            # Convert the compute_flavor dataclass to a dict and merge it into info.
            cf_dict = asdict(self.compute_flavor)
            for key, value in cf_dict.items():
                info[f"Compute_Flavor {key.capitalize()}"] = value
        else:
            info["Compute_Flavor"] = "N/A"

        return info


def get_lb_flavor_profile(openstack_api, flavor):
    """
    Retrieve and construct the FlavorProfile for a given flavor.

    Args:
        openstack_api: The OpenStack API client.
        flavor: A flavor object from the loadbalancer service.

    Returns:
        A FlavorProfile instance if found; otherwise, None.
    """
    if not flavor.flavor_profile_id:
        logging.warning("Flavor %s does not have a flavor_profile_id attribute", flavor.id)
        return None

    fprofile = openstack_api.loadbalancer.find_flavor_profile(flavor.flavor_profile_id)
    if not fprofile:
        logging.warning(
            "Flavor %s missing associated flavor profile (ID: %s)",
            flavor.id,
            flavor.flavor_profile_id,
        )
        return None

    try:
        return FlavorProfile(
            id=fprofile.id,
            name=fprofile.name,
            provider_name=fprofile.provider_name,
            flavor_data=fprofile.flavor_data,
        )
    except (ValueError, TypeError, AttributeError) as e:
        logging.error(
            "Error constructing FlavorProfile for ID %s: %s", flavor.flavor_profile_id, e
        )
        return None


def get_compute_flavor(openstack_api, flavor_profile):
    """
    Retrieve and construct the ComputeFlavor using the flavor profile's data.

    Args:
        openstack_api: The OpenStack API client.
        flavor_profile: A FlavorProfile instance.

    Returns:
        A ComputeFlavor instance if the 'compute_flavor' key exists and the flavor is found;
        otherwise, None.
    """
    compute_flavor_value = flavor_profile.get_compute_flavor_id()
    if not compute_flavor_value:
        return None

    compute_flavor = openstack_api.compute.find_flavor(compute_flavor_value)
    if not compute_flavor:
        logging.warning(
            "No compute flavor found for compute_flavor_id %s.", compute_flavor_value
        )
        return None

    try:
        return ComputeFlavor(
            id=compute_flavor.id,
            name=compute_flavor.name,
            vcpus=int(compute_flavor.vcpus),
            ram=int(compute_flavor.ram),
            disk=int(compute_flavor.disk),
        )
    except (ValueError, TypeError, AttributeError) as e:
        logging.error(
            "Error constructing ComputeFlavor for ID %s: %s", compute_flavor_value, e
        )
        return None


def display_flavors_basic(flavors_list):
    """
    Display basic flavor information

    Args:
        flavors_list (list): A list of Flavor objects
    """
    if RICH_AVAILABLE:
        console = Console()
        table = Table(title="Load Balancer Flavors")
        table.add_column("Flavor Id", style="cyan", no_wrap=True)
        table.add_column("Name", style="magenta")
        table.add_column("Description", style="green")
        table.add_column("Enabled", style="yellow")
        table.add_column("Flavor Profile", style="blue")
        table.add_column("Compute Flavor", style="red")

        for flavor in flavors_list:
            table.add_row(*flavor.get_basic_info())
        console.print(table)
    else:
        # Fallback plain text output
        print("Load Balancer Flavors:")
        header = " | ".join(
            ["Flavor Id", "Name", "Description", "Enabled", "Flavor Profile", "Compute Flavor"]
        )
        print(header)
        print("-" * len(header))
        for flavor in flavors_list:
            row = flavor.get_basic_info()
            print(" | ".join(row))


def display_flavors_detail(flavors_list):
    """
    Display detailed flavor information

    Args:
        flavors_list (list): A list of Flavor objects
    """
    if RICH_AVAILABLE:
        console = Console()
        root_tree = Tree(
            "[bold blue]Load Balancer Flavors[/bold blue]",
            guide_style="bright_blue",
            highlight=True,
        )

        for flavor in flavors_list:
            info = flavor.get_detailed_info()
            # Display header with Flavor Id and Flavor Name
            flavor_node = root_tree.add(
                f"[cyan]Flavor Id:[/cyan] {info.get('Flavor Id')} "
                f"([magenta]{info.get('Flavor Name')}[/magenta])"
            )
            for key, value in info.items():
                flavor_node.add(f"[cyan]{key}:[/cyan] {value}")
        console.print(root_tree)
    else:
        # Fallback plain text output
        print("Load Balancer Flavors:")
        for flavor in flavors_list:
            info = flavor.get_detailed_info()
            print(f"Flavor Id: {info.get('Flavor Id')} ({info.get('Flavor Name')})")
            for key, value in info.items():
                print(f"  {key}: {value}")
            print("-" * 40)


def display_flavors(flavors_list, detail):
    """
    Top-level function to display a list of Flavor objects

    Args:
        flavors_list (list): List of Flavor objects
        detail (bool): True for detailed view, False for basic view
    """
    if detail:
        display_flavors_detail(flavors_list)
    else:
        display_flavors_basic(flavors_list)


def handle_lb_flavors_cmd(openstack_api, args):
    """
    Handle the 'lb_flavors' subcommand

    Args:
        openstack_api (OpenStackAPI): Instance of OpenStackAPI
        args (argparse.Namespace): Parsed command-line arguments
    """
    filters = {}
    if args.flavor_id:
        filters["id"] = args.flavor_id
    if args.flavor_name:
        filters["name"] = args.flavor_name

    flavors_list = []

    for flavor in openstack_api.loadbalancer.list_flavors(**filters):
        logging.debug("Processing load balancer flavor: %s", flavor)

        # Retrieve the associated FlavorProfile for this flavor
        flavor_profile_obj = get_lb_flavor_profile(openstack_api, flavor)
        logging.debug("Flavor profile associated: %s", flavor_profile_obj)

        # If a FlavorProfile exists, retrieve the ComputeFlavor using its data;
        # otherwise, set the compute flavor object to None
        if flavor_profile_obj:
            compute_flavor_obj = get_compute_flavor(openstack_api, flavor_profile_obj)
        else:
            compute_flavor_obj = None
        logging.debug("Compute flavor associated: %s", compute_flavor_obj)

        # Construct a Flavor object
        flavor_obj = Flavor(
            id=flavor.id,
            name=flavor.name,
            description=flavor.description,
            is_enabled=flavor.is_enabled,
            flavor_profile=flavor_profile_obj,
            compute_flavor=compute_flavor_obj,
        )
        logging.debug("Dataclass flavor object: %s", flavor_obj)

        flavors_list.append(flavor_obj)

    display_flavors(flavors_list, args.detail)


# vim: ts=4 sw=4 expandtab
