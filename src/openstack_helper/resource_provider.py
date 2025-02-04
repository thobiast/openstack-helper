# -*- coding: utf-8 -*-
"""
openstack-helper - resource provider command
"""
import logging
from dataclasses import dataclass, field, fields

from openstack_helper.common import RICH_AVAILABLE, Console, Table


@dataclass
# pylint: disable=too-many-instance-attributes
class ResourceProviderInfo:
    """
    Represents detailed information about an OpenStack resource provider's inventory and usage.

    Attributes:
        provider_name (str):
            The name of the resource provider (e.g., a compute node name).
        resource_class (str):
            The type of resource (e.g., 'VCPU', 'MEMORY_MB', 'DISK_GB').
        allocation_ratio (float):
            The allocation ratio applied to the resource,
            indicating the level of overcommitment.
        total (int):
            The total amount of the resource available on the provider.
        reserved (int):
            The amount of the resource that is reserved and not available for allocation.
        usage (int):
            The current amount of the resource that is in use.
        allocation_ratio_pct (float):
            The percentage of the allocatable resource that is currently used
            (computed in __post_init__).
        current_allocation_ratio (float):
            The current ratio of used resources to total physical resources
            (computed in __post_init__).
    """

    provider_name: str = field(
        metadata={
            "display_name": "Provider Name",
            "style": {"style": "cyan", "justify": "left", "no_wrap": True},
        }
    )
    resource_class: str = field(
        metadata={
            "display_name": "Resource Class",
            "style": {"style": "green", "justify": "left"},
        }
    )
    total: int = field(metadata={"display_name": "Total", "style": {"justify": "right"}})
    reserved: int = field(metadata={"display_name": "Reserved", "style": {"justify": "right"}})
    usage: int = field(metadata={"display_name": "Used", "style": {"justify": "right"}})
    allocation_ratio: float = field(
        metadata={"display_name": "Conf Alloc Ratio", "style": {"justify": "right"}}
    )
    allocation_ratio_pct: float = field(
        init=False,
        metadata={"display_name": "Alloc Ratio Used (%)", "style": {"justify": "right"}},
    )
    current_allocation_ratio: float = field(
        init=False,
        metadata={"display_name": "Current Alloc Ratio", "style": {"justify": "right"}},
    )

    def __post_init__(self):
        # Calculate current allocation ratio used pct
        allocatable = (self.total - self.reserved) * self.allocation_ratio
        if allocatable > 0:
            self.allocation_ratio_pct = (self.usage / allocatable) * 100
        else:
            self.allocation_ratio_pct = 0.0

        # Calculate the current allocation ratio
        physical_allocatable = self.total - self.reserved
        if physical_allocatable > 0:
            self.current_allocation_ratio = self.usage / physical_allocatable
        else:
            self.current_allocation_ratio = 0.0


def get_resource_providers_info(openstack_api, resource_classes=None, filters=None):
    """
    Retrieve resource provider information and return it as a list of
    ResourceProviderInfo instances.

    Args:
        openstack_api (OpenStackAPI): Instance of OpenStackAPI.
        resource_classes (list): List of resource classes to include. If None, include all.
        filters (dict): Dictionary of filters to apply when retrieving resource providers.

    Returns:
        List[ResourceProviderInfo]: List of resource provider information instances.
    """
    resource_providers_info = []

    logging.debug("Retrieving resource providers with filters: %s", filters)

    for provider in openstack_api.placement.retrieve_resource_providers(**filters):
        logging.debug("Processing resource provider: %s", provider.name)

        usage = openstack_api.placement.retrieve_provider_usage(provider)
        logging.debug("Usage for provider %s: %s", provider.name, usage)

        logging.debug("Retrieving resource provider inventories: %s", provider.name)
        inventories = openstack_api.placement.retrieve_resource_provider_inventories(provider)
        for inventory in inventories:
            logging.debug("Provider inventory: %s", inventory)

            # If filters are provided, skip classes not in the list
            if resource_classes and inventory.resource_class not in resource_classes:
                logging.debug(
                    "Skipping resource class '%s' (not in user selection)",
                    inventory.resource_class,
                )
                continue

            provider_info = ResourceProviderInfo(
                provider_name=provider.name,
                resource_class=inventory.resource_class,
                allocation_ratio=inventory.allocation_ratio,
                total=inventory.total,
                reserved=inventory.reserved,
                usage=usage.get(inventory.resource_class, 0),
            )
            resource_providers_info.append(provider_info)

    logging.debug("Collected details for %d resource providers", len(resource_providers_info))
    return resource_providers_info


def display_resource_providers_info(resource_providers_info):
    """
    Display resource providers information.

    If the 'rich' library is available, it utilizes Rich's Table for enhanced display.
    It builds a Rich 'Table' where each column's styling is derived from the
    dataclass field's metadata (e.g., color, justification).
    Otherwise, it falls back to a simple tab-separated textual representation.

    Args:
        resource_providers_info (List[ResourceProviderInfo]): List of resource provider
            information instances.
    """
    # Get field objects from the dataclass
    dataclass_fields = fields(ResourceProviderInfo)
    logging.debug("dataclass_fields: %s", dataclass_fields)

    # Prepare rows for the table
    rows = []
    for resource in resource_providers_info:
        row = []
        for field_obj in dataclass_fields:
            value = getattr(resource, field_obj.name)
            # Format fields
            if field_obj.name == "allocation_ratio_pct":
                value = f"{value:.2f}%"
            if field_obj.name == "current_allocation_ratio":
                value = f"{value:.2f}"
            row.append(str(value))
        rows.append(row)

    if RICH_AVAILABLE:
        console = Console()
        table = Table(show_header=True, header_style="bold magenta")

        # Build table columns using field metadata
        for field_obj in dataclass_fields:
            display_name = field_obj.metadata.get(
                "display_name", field_obj.name.replace("_", " ").title()
            )
            style = field_obj.metadata.get("style", {})
            table.add_column(display_name, **style)
        for row in rows:
            table.add_row(*row)

        console.print(table)
    else:
        headers = []
        for field_obj in dataclass_fields:
            display_name = field_obj.metadata.get(
                "display_name", field_obj.name.replace("_", " ").title()
            )
            headers.append(display_name)
        print("\t".join(headers))
        for row in rows:
            print("\t".join(row))


def sort_resource_providers_info(resource_providers_info, sort_by_columns):
    """
    Sorts a list of ResourceProviderInfo instances based on specified display
    name columns.

    Args:
        resource_providers_info (List[ResourceProviderInfo]):
            The list of `ResourceProviderInfo` instances.
        sort_by_columns (List[str]):
            List of column display names to sort by.

    Returns:
        List[ResourceProviderInfo]:
            Sorted list of resource provider information instances.

    """

    # Retrieve the display names from the ResourceProviderInfo dataclass metadata
    display_names = get_dataclass_field_metadata(ResourceProviderInfo, "display_name")

    # Extract the actual field names that correspond to the provided sort-by display names
    sort_fields = []
    for col in sort_by_columns:
        # Find which field matches the display name `col`
        for field_name, disp_name in display_names.items():
            if disp_name == col:
                sort_fields.append(field_name)
                break

    # Sort the resource providers
    return sorted(
        resource_providers_info, key=lambda x: [getattr(x, field) for field in sort_fields]
    )


def get_dataclass_field_metadata(dataclass_type, metadata_key):
    """
    Retrieves specified metadata from all fields of a given dataclass.

    This function iterates over all the fields of the provided dataclass and
    extracts the value associated with the specified metadata key from each field.

    Args:
        dataclass_type (dataclass): The dataclass type from which to retrieve metadata.
        metadata_key (str): The key of the metadata to retrieve from each field.

    Returns:
        Dict[str, Any]: A dictionary mapping each field name to its corresponding
            metadata value. If a field does not contain the specified metadata key,
            the field's name is used as the value.
    """
    if not hasattr(dataclass_type, "__dataclass_fields__"):
        raise TypeError(f"{dataclass_type} is not a dataclass.")

    if not isinstance(metadata_key, str):
        raise AttributeError("metadata_key must be a string.")

    dataclass_fields = fields(dataclass_type)
    metadata_values = {
        field_obj.name: field_obj.metadata.get(metadata_key, field_obj.name)
        for field_obj in dataclass_fields
    }

    return metadata_values


def construct_filters(args):
    """
    Constructs the filters dictionary based on user input.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.

    Returns:
        dict: Filters to apply when retrieving resource providers.
    """
    # Define filters based on user input
    filters = {}

    if args.name:
        filters["name"] = args.name

    if args.uuid:
        filters["uuid"] = args.uuid

    if args.member_of:
        filters["member_of"] = [f"in:{args.member_of}"]

    return filters


def handle_resource_provider_cmd(openstack_api, args):
    """
    Handle the 'resource_provider' subcommand.

    Args:
        openstack_api (OpenStackAPI): Instance of OpenStackAPI.
        args (argparse.Namespace): Parsed command-line arguments.
    """
    # Retrieve display names from the ResourceProviderInfo dataclass metadata
    display_names = get_dataclass_field_metadata(ResourceProviderInfo, "display_name")
    logging.debug("display_names: %s", display_names)

    # Identify any sort-by columns specified by the user that are not valid
    invalid_columns = [col for col in args.sort_by if col not in display_names.values()]
    if invalid_columns:
        print(f"Invalid sort-by column(s): {', '.join(invalid_columns)}")
        print(f"Valid columns are: {', '.join(display_names.values())}")
        raise ValueError("Error: Invalid sort-by column")

    # Construct filters based on user input
    filters = construct_filters(args)

    resource_providers_info = get_resource_providers_info(
        openstack_api, args.resource_class, filters
    )

    if not resource_providers_info:
        print("No resource provider information available.")
        return

    resource_providers_info = sort_resource_providers_info(
        resource_providers_info, args.sort_by
    )

    # Display the sorted resource providers information
    display_resource_providers_info(resource_providers_info)


# vim: ts=4 sw=4 expandtab
