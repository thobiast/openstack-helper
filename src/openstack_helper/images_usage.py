# -*- coding: utf-8 -*-
"""
openstack-helper - image usage command
"""
import datetime
import logging
from dataclasses import dataclass, field

from openstack_helper.common import RICH_AVAILABLE, Console, Table


@dataclass
class ServerInfo:
    """Data class representing server (VM) information."""

    id: str
    name: str


@dataclass
class ImageInfo:
    """Data class representing image information and associated servers."""

    id: str
    name: str
    status: str
    visibility: str
    created_at: str
    servers: list = field(default_factory=list)


def get_filtered_images(openstack_api, args):
    """
    Retrieve and filter images based on provided arguments.

    Args:
        openstack_api: Instance of OpenStackAPI.
        args: Parsed command-line arguments.

    Returns:
        Dict[str, ImageInfo]: A dictionary mapping image IDs to ImageInfo instances.
    """
    image_info_map = {}

    # Prepare the query parameters
    query_params = {}
    if args.name:
        query_params["name"] = args.name
    if args.tag:
        query_params["tag"] = args.tag.split(",")
    logging.debug("Retrieving images with query params: %s", query_params)

    current_date = datetime.datetime.utcnow()

    for img in openstack_api.image.list_images(**query_params):
        # Filter by creation date
        if args.days and img.created_at:
            delta = current_date - datetime.datetime.strptime(
                img.created_at, "%Y-%m-%dT%H:%M:%SZ"
            )
            num_days = delta.days
            logging.debug("num_days: %s", num_days)
            if num_days < args.days:
                logging.debug(
                    "Excluding by image days filter: %s created %s days ago", img.id, num_days
                )
                continue
        # Filter by image ID
        if args.image_id and args.image_id != img.id:
            logging.debug("Excluding by image id filter: %s", img.id)
            continue

        logging.debug("Getting details of image: %s (%s)", img.name, img.id)
        image_info = ImageInfo(
            id=img.id,
            name=img.name,
            status=img.status,
            visibility=img.visibility,
            created_at=img.created_at,
            servers=[],
        )
        image_info_map[img.id] = image_info

    return image_info_map


def get_boot_volume_image_id(server, openstack_api):
    """
    Retrieve the image ID from the boot volume if the server was booted from volume.

    Args:
        server: Server object from OpenStack API.
        openstack_api: Instance of OpenStackAPI.

    Returns:
        str or None: The image ID of the boot volume, or None if not found.
    """
    logging.debug("Server %s. Trying to find image id from volume", server.name)
    logging.debug("Server root device name: %s", server.root_device_name)
    logging.debug("Server attached volumes: %s", server.attached_volumes)

    server_image_id = None

    for attachment in server.attached_volumes:
        volume = openstack_api.volume.get_volume(attachment.id)
        logging.debug("Examining volume: %s", volume.id)

        if not volume.attachments:
            logging.warning("Volume %s has no attachments; skipping volume", volume.id)
            continue

        volume_device = volume.attachments[0].get("device")
        if volume_device == server.root_device_name:
            server_image_id = getattr(volume, "volume_image_metadata", {}).get("image_id")
            logging.debug(
                "Server %s using image id %s from volume %s",
                server.name,
                server_image_id,
                volume.id,
            )
            return server_image_id

        logging.debug(
            "Volume %s attachment device %s did not match root device %s",
            volume.id,
            volume_device,
            server.root_device_name,
        )

    logging.warning("Server %s has no attached volumes or we can't detect image", server.name)

    return server_image_id


def add_servers_to_images(openstack_api, image_info_map, all_projects=False):
    """
    Associate servers with their corresponding images in place.

    Args:
        openstack_api: Instance of OpenStackAPI.
        image_info_map (Dict[str, ImageInfo]): Dictionary mapping image IDs to
            ImageInfo instances.
        all_projects (bool): Whether to include servers from all projects.

    Mutates:
        image_info_map: Updated in-place with servers added to corresponding images.
    """
    logging.debug("Listing servers. all_projects=%s", all_projects)

    for server in openstack_api.compute.list_servers(all_projects=all_projects):
        logging.debug("Checking information for server: %s id: %s", server.name, server.id)

        server_image_id = server.image.get("id", None)

        if server_image_id:
            logging.debug("Server %s using image %s", server.name, server_image_id)
        else:
            # handle boot from volume
            logging.debug("Server %s: no direct image found. Checking volumes...", server.name)
            server_image_id = get_boot_volume_image_id(server, openstack_api)

        if server_image_id in image_info_map:
            server_info = ServerInfo(id=server.id, name=server.name)
            image_info_map[server_image_id].servers.append(server_info)
        else:
            logging.debug(
                "Server %s using image id '%s' not in image_info_map",
                server.name,
                server_image_id,
            )


def print_results(image_info_map, show_vm_details, show_no_vms):
    """
    Print image usage information in a table format.

    Args:
        image_info_map (Dict[str, ImageInfo]): Dictionary mapping image IDs to
            ImageInfo instances.
        show_vm_details (bool): Whether to display VM IDs and Names.
        show_no_vms (bool): Whether to include images with no VMs.
    """

    images_to_display = []

    # Apply show_no_vms filter
    for image_info in image_info_map.values():
        if show_no_vms and len(image_info.servers) > 0:
            continue
        images_to_display.append(image_info)

    if RICH_AVAILABLE:
        console = Console()
        table = Table(show_header=True)

        table.add_column("Image ID", style="cyan", no_wrap=True)
        table.add_column("Image Name", style="green")
        table.add_column("Status", style="red")
        table.add_column("Visibility", style="blue")
        table.add_column("Created At", style="magenta")
        table.add_column("Number of VMs", justify="right", style="yellow")
        if show_vm_details:
            table.add_column("VM IDs and Names", style="white")

        for image_info in images_to_display:
            row = [
                image_info.id,
                image_info.name,
                image_info.status,
                image_info.visibility,
                image_info.created_at,
                str(len(image_info.servers)),
            ]
            if show_vm_details:
                vm_details = (
                    "\n".join(
                        [f"{server.id} ({server.name})" for server in image_info.servers]
                    )
                    or "No VMs"
                )
                row.append(vm_details)

            table.add_row(*row)
        console.print(table)
    else:
        for image_info in images_to_display:
            if show_no_vms and len(image_info.servers) > 0:
                continue
            print(f"Image ID: {image_info.id}")
            print(f"Image Name: {image_info.name}")
            print(f"Image Status: {image_info.status}")
            print(f"Image Visibility: {image_info.visibility}")
            print(f"Created At: {image_info.created_at}")
            print(f"Number of VMs using this image: {len(image_info.servers)}")
            if show_vm_details:
                for server in image_info.servers:
                    print(f"  VM ID: {server.id}, VM Name: {server.name}")
            print("-" * 50)


def handle_images_usage_cmd(openstack_api, args):
    """
    Handle the 'images_usage' subcommand.

    Args:
        openstack_api (OpenStackAPI): Instance of OpenStackAPI.
        args (argparse.Namespace): Parsed command-line arguments.
    """
    image_info_map = get_filtered_images(openstack_api, args)

    # Enrich image_info_map with servers info (in-place)
    add_servers_to_images(openstack_api, image_info_map, all_projects=args.all_projects)

    print_results(image_info_map, args.show_vm_details, args.show_no_vms)


# vim: ts=4 sw=4 expandtab
