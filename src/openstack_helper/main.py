#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenStack Helper CLI Tool

Provides subcommands for common OpenStack operations:
- 'check_allocations' (alias 'ca'): Check instance allocation in Nova and Placement.
- 'images_usage' (alias 'iu'): Show image usage details and the VMs referencing them.
- 'lb_flavors' (alias 'lbf'): List load balancer flavors along with associated
    flavor profiles and Nova flavors.
- 'resource_provider' (alias 'rp'): Retrieve and display resource provider data.
- 'unused_ports' (alias 'up'): Identify and analyze unused ports.
...

Run 'openstack_helper --help' for global usage or 'openstack_helper <subcommand> --help'
for details on each subcommand. Requires Python 3.7+ and appropriate OpenStack
configuration.
"""
import argparse
import logging
import sys

from openstack_helper.check_allocations import handle_check_allocations_cmd
from openstack_helper.common import is_valid_uuid
from openstack_helper.images_usage import handle_images_usage_cmd
from openstack_helper.loadbalancer_flavors import handle_lb_flavors_cmd
from openstack_helper.logging_config import setup_logging
from openstack_helper.openstack_api import OpenStackAPI
from openstack_helper.resource_provider import handle_resource_provider_cmd
from openstack_helper.routers_info import handle_routers_info_cmd
from openstack_helper.unused_ports import handle_unused_ports_cmd


def parse_uuid(uuid_str):
    """
    Parses and validates a single UUID.

    Args:
        uuid_str (str): The UUID string to validate.

    Returns:
        str: The validated UUID string.

    Raises:
        argparse.ArgumentTypeError: If the UUID is invalid.
    """
    if not is_valid_uuid(uuid_str):
        raise argparse.ArgumentTypeError(f"Invalid UUID: '{uuid_str}'")

    return uuid_str


def parse_uuid_list(uuids_str):
    """
    Parses and validates a comma-separated list of UUIDs.

    Args:
        uuids_str (str): Comma-separated UUIDs.

    Returns:
        str: Cleaned comma-separated UUID string.

    Raises:
        argparse.ArgumentTypeError: If any UUID is invalid or
            if no UUIDs are provided.
    """
    # Split the input string by commas and strip whitespace
    uuids = [u.strip() for u in uuids_str.split(",") if u.strip()]

    if not uuids:
        raise argparse.ArgumentTypeError("No UUIDs provided.")

    for u in uuids:
        if not is_valid_uuid(u):
            raise argparse.ArgumentTypeError(f"Invalid UUID: '{u}'")

    return ",".join(uuids)


def parse_args():
    """
    Parse command-line arguments and return the parsed arguments.

    Returns:
        Namespace: Parsed command-line arguments.
    """
    epilog = """
    Example of use:
        %(prog)s --help
        %(prog)s rp --help
        %(prog)s rp --resource-class vcpu --sort-by "Current Alloc Ratio"
        %(prog)s unused_ports -h
        %(prog)s unused_ports --network-id 17583b07-92c2-4a07-9fb9-5bc8705d58e2
        %(prog)s lbf
    """

    parser = argparse.ArgumentParser(
        description="OpenStack Helper tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )

    parser.add_argument("--debug", "-d", action="store_true", help="debug flag")
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="disable TLS certificate verification for OpenStack API connections",
    )

    # Add subcommands options
    subparsers = parser.add_subparsers(required=True, dest="command")

    ################
    # Unused ports #
    ################
    unused_port_epilog = """
    Example:
      %(prog)s --network-id f741fc0c-72b7-433e-961c-cb483b344721
      %(prog)s --network-id f741fc0c-72b7-433e-961c-cb483b344721 --device-owner ""
    """
    unused_ports_parser = subparsers.add_parser(
        "unused_ports",
        aliases=["up"],
        description="Retrieves and checks unused OpenStack ports",
        help="Retrieves and checks unused OpenStack ports",
        epilog=unused_port_epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    unused_ports_parser.add_argument(
        "--device-owner",
        help="Specify the device owner to filter ports (default: %(default)s)",
        default="compute:nova",
    )
    unused_ports_parser.add_argument(
        "--network-id",
        type=parse_uuid,
        help="Specify the network ID to filter ports",
        required=False,
    )
    unused_ports_parser.add_argument(
        "--ping",
        action="store_true",
        help=(
            "Also try to ping the port IP address to determine if it is active"
            " (default: %(default)s)"
        ),
    )
    unused_ports_parser.add_argument(
        "--max-workers",
        type=int,
        default=20,
        help="Maximum number of worker threads for ping operations (default: %(default)s)",
    )
    unused_ports_parser.set_defaults(func=handle_unused_ports_cmd)

    ################
    # Images Usage #
    ################
    image_usage_epilog = """
    Example:
      %(prog)s
      %(prog)s --tag ubuntu
      %(prog)s --tag ubuntu --current-project
      %(prog)s --image-id 800f285b-ea14-46b7-8911-5e867766f0bb --show-vm-details
    """
    images_usage_parser = subparsers.add_parser(
        "images_usage",
        aliases=["iu"],
        description="Show usage details about images, including which VMs are using them",
        help="Show usage details about images, including which VMs are using them",
        epilog=image_usage_epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    images_usage_parser.add_argument(
        "--name",
        help="Filter images by name",
        type=str,
    )
    images_usage_parser.add_argument(
        "--image-id",
        help="Filter images by ID",
        type=str,
    )
    images_usage_parser.add_argument(
        "--tag",
        help=(
            "Filter images by tag(s). Multiple tags can be specified, separated by commas."
            "  Only images containing all specified tags are included"
        ),
        type=str,
    )
    images_usage_parser.add_argument(
        "--days",
        help="Show only images that are at least X days old",
        type=int,
    )
    images_usage_parser.add_argument(
        "--current-project",
        help=(
            "Restrict server lookup to the currently scoped project"
            " (otherwise, all projects are included)"
        ),
        action="store_false",
        dest="all_projects",
    )
    images_usage_parser.add_argument(
        "--show-no-vms",
        help="Show only images that have zero VMs using them",
        action="store_true",
    )
    images_usage_parser.add_argument(
        "--show-vm-details",
        help="Display detailed VM information (IDs and names)",
        action="store_true",
    )
    images_usage_parser.set_defaults(func=handle_images_usage_cmd)

    ######################
    # Resource providers #
    ######################
    resource_provider_epilog = """
    Example:
      %(prog)s
      %(prog)s -r VCPU --sort-by "Current Alloc Ratio"
      %(prog)s -r VCPU --sort-by 'Used' 'Provider Name'
      %(prog)s -r VCPU MEMORY_MB --sort-by "Resource Class" "Provider Name"
      %(prog)s --aggregates-uuid 7f34801e-b37c-4e5b-abaa-3db09630e421 -r vcpu  --sort 'Current Alloc Ratio'
    """
    resource_provider_parser = subparsers.add_parser(
        "resource_provider",
        aliases=["rp"],
        description=(
            "Retrieves and displays inventory and usage details about resource providers"
        ),
        help="Retrieves and displays inventory and usage details about resource providers",
        epilog=resource_provider_epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    resource_provider_parser.add_argument(
        "-r",
        "--resource-class",
        help=(
            "Show information only for the specified resource classes."
            " You can specify multiple classes by separating them with a space"
            " (for example: '-r VCPU MEMORY_MB'). (default: all)"
        ),
        choices=("VCPU", "MEMORY_MB", "DISK_GB"),
        nargs="*",
        type=str.upper,
        required=False,
    )
    resource_provider_parser.add_argument(
        "-s",
        "--sort-by",
        help=(
            "Sort table by the specified column(s). You can specify multiple"
            " columns by separating them with spaces (for example:"
            " \"-s 'Used' 'Provider Name'\").(default: %(default)s)"
        ),
        nargs="+",
        required=False,
        default=["Provider Name"],
    )
    resource_provider_parser.add_argument(
        "--name", type=str, dest="name", help="Filter by resource provider name"
    )
    resource_provider_parser.add_argument(
        "--uuid", type=parse_uuid, dest="uuid", help="Filter by resource provider UUID"
    )
    resource_provider_parser.add_argument(
        "--aggregates-uuid",
        type=parse_uuid_list,
        dest="member_of",
        help=(
            "Filter by aggregates UUIDs. When specifying multiple UUIDs, "
            "separate them with commas"
        ),
    )
    resource_provider_parser.set_defaults(func=handle_resource_provider_cmd)

    ##############################
    # Check instance allocations #
    ##############################
    check_allocations_parser = subparsers.add_parser(
        "check_allocations",
        aliases=["ca"],
        description="Check instance allocation in Nova and Placement",
        help="Check instance allocation in Nova and Placement",
    )
    check_allocations_parser.add_argument(
        "--uuid",
        type=parse_uuid_list,
        required=True,
        dest="uuid",
        help="Comma-separated list of instance UUIDs to check allocation",
    )
    check_allocations_parser.set_defaults(func=handle_check_allocations_cmd)

    ################
    # Routers info #
    ################
    routers_info_parser = subparsers.add_parser(
        "router_info",
        aliases=["ri"],
        description="Show router's information",
        help="Show router's information",
    )
    routers_info_parser.add_argument(
        "--uuid",
        type=parse_uuid_list,
        required=False,
        dest="uuid",
        help="Comma-separated list of routers UUIDs to show information",
    )
    routers_info_parser.add_argument(
        "--name",
        type=str,
        required=False,
        dest="name",
        help="Comma-separated list of routers name to show information",
    )
    routers_info_parser.set_defaults(func=handle_routers_info_cmd)

    #########################
    # Load Balancer Flavors #
    #########################
    lb_flavors_parser = subparsers.add_parser(
        "lb_flavors",
        aliases=["lbf"],
        help="List load balancer flavors and associated flavor profiles and Nova flavors",
        description=(
            "List load balancer flavors along with their load balancer flavor profiles and "
            "the associated Nova flavors."
        ),
        epilog="""
    Example:
      %(prog)s
      %(prog)s --flavor-id 1234abcd-5b0c-46e0-ada9-2a5090b9151e
      %(prog)s --flavor-id 1234abcd-5b0c-46e0-ada9-2a5090b9151e --detail
      %(prog)s --flavor-name "example_flavor"
    """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    lb_flavors_parser.add_argument(
        "--flavor-id", type=str, help="Query load balancer flavor by its ID"
    )
    lb_flavors_parser.add_argument(
        "--flavor-name", type=str, help="Query load balancer flavor by its name"
    )
    lb_flavors_parser.add_argument(
        "--detail", action="store_true", help="Display detailed information"
    )
    lb_flavors_parser.set_defaults(func=handle_lb_flavors_cmd)

    return parser.parse_args()


def main():
    """
    Main entry point for the script.

    Initializes logging, parses command-line arguments, establishes a connection
    to OpenStack, and dispatches the appropriate subcommand handler based on user input.
    """
    args = parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO

    # Initialize logging
    setup_logging(log_level)

    logging.debug(args)

    openstack_api = OpenStackAPI(insecure=args.insecure)
    try:
        args.func(openstack_api, args)
    except ValueError as e:
        sys.exit(e)


if __name__ == "__main__":
    main()

# vim: ts=4 sw=4 expandtab
