# -*- coding: utf-8 -*-
"""
openstack-helper - OpenStack API module

This module acts as a wrapper around the OpenStack SDK, encapsulating common API calls
to simplify interactions with OpenStack services.

By using this wrapper, we can easily manage and verify which OpenStack operations
are available within a given OpenStack environment.
"""
import openstack


# pylint: disable=too-few-public-methods
class OpenStackAPI:
    """
    Main entry point for interacting with OpenStack services.

    Attributes:
        os_conn (openstack.connection.Connection): An authenticated OpenStack SDK
            connection object.
        image (ImageAPI): Interface to OpenStack Image operations.
        compute (ComputeAPI): Interface to OpenStack Compute operations.
        volume (VolumeAPI): Interface to OpenStack Volume operations.
        network (NetworkAPI): Interface to OpenStack Network operations.
        placement (PlacementAPI): Interface to OpenStack Placement operations.
    """

    def __init__(self, debug=False, insecure=False):
        """
        Initialize the OpenStackAPI instance and establish a connection.

        Args:
            debug (bool): Whether to enable debug logging.
            insecure (bool): If True, disable TLS certificate verification
        """
        openstack.enable_logging(debug=debug)
        self.os_conn = openstack.connect(insecure=insecure)

        self.image = ImageAPI(self.os_conn)
        self.compute = ComputeAPI(self.os_conn)
        self.loadbalancer = LoadBalanerAPI(self.os_conn)
        self.volume = VolumeAPI(self.os_conn)
        self.network = NetworkAPI(self.os_conn)
        self.placement = PlacementAPI(self.os_conn)


class LoadBalanerAPI:
    """
    A wrapper around OpenStack Load Balancer (Octavia) API.

    Attributes:
        os_conn (openstack.connection.Connection): An authenticated OpenStack SDK
            connection object.
    """

    def __init__(self, os_conn):
        self.os_conn = os_conn

    def list_flavors(self, **filters):
        """
        Retrieve a list of available load balancer flavors.

        Args:
            **filters: Additional filters to apply.

        Returns:
            list: A list of openstack.load_balancer.v2.flavor objects.
        """
        return list(self.os_conn.load_balancer.flavors(**filters))

    def find_flavor_profile(self, name_or_id, ignore_missing=True):
        """
        Find a single flavor profile.

        Args:
            name_or_id (str): The name or UUID of the flavor profile to find.
            ignore_missing (bool, optional): If True, returns None if the flavor
                profile is not found. If False, raises an exception if the profile
                does not exist. Defaults to True.

        Returns:
            openstack.load_balancer.v2.flavor_profile.FlavorProfile or None:
                The matching flavor profile object if found, or None if `ignore_missing`
                is True and no profile matches the given identifier.
        """
        return self.os_conn.load_balancer.find_flavor_profile(
            name_or_id, ignore_missing=ignore_missing
        )


# pylint: disable=too-few-public-methods
class NetworkAPI:
    """
    A wrapper around OpenStack Network (Neutron) API.

    Attributes:
        os_conn (openstack.connection.Connection): An authenticated OpenStack SDK
            connection object.
    """

    def __init__(self, os_conn):
        self.os_conn = os_conn

    def retrieve_ports(self, **filters):
        """
        Retrieve a list of OpenStack ports based on the provided filters.

        Args:
            **filters: Arbitrary keyword arguments specifying filtering
                       criteria for the OpenStack port query. Common filters
                       'network_id', 'status', 'device_owner', 'project_id', etc.

        Returns:
            list: A list of OpenStack port objects that match the filters.
        """
        return list(self.os_conn.network.ports(**filters))


# pylint: disable=too-few-public-methods
class VolumeAPI:
    """
    A wrapper around OpenStack Volume (Cinder) API.

    Attributes:
        os_conn (openstack.connection.Connection): An authenticated OpenStack SDK
            connection object.
    """

    def __init__(self, os_conn):
        self.os_conn = os_conn

    def get_volume(self, volume_id, all_projects=False):
        return self.os_conn.volume.find_volume(volume_id, all_projects=all_projects)


class ImageAPI:
    """
    A wrapper around OpenStack Image (Glance) API.

    Attributes:
        os_conn (openstack.connection.Connection): An authenticated OpenStack SDK
            connection object.
    """

    def __init__(self, os_conn):
        self.os_conn = os_conn

    def list_images(self, **filters):
        """
        Retrieve a list of available images.

        Args:
            **filters: Additional filters to apply (e.g., `name`, `visibility`, `status`).

        Returns:
            list: A list of `openstack.image.v2.image.Image` objects.
        """
        return list(self.os_conn.image.images(**filters))

    def get_image(self, name_or_id):
        """
        Retrieve an image by its name or ID.

        Args:
            name_or_id (str): The name or UUID of the image.

        Returns:
            openstack.image.v2.image.Image or None: The requested image if found,
                otherwise None.
        """
        return self.os_conn.image.find_image(name_or_id)


class ComputeAPI:
    """
    A wrapper around OpenStack Compute (Nova) API.

    Attributes:
        os_conn (openstack.connection.Connection): An authenticated OpenStack SDK
            connection object.
    """

    def __init__(self, os_conn):
        self.os_conn = os_conn

    def list_servers(self, details=True, all_projects=False, **filters):
        """
        List all servers (instances) with optional filters.

        Args:
            details (bool, optional): Whether to fetch detailed information about each server.
                Defaults to True.
            all_projects (bool, optional): Whether to list servers from all projects.
                Defaults to False.
            **filters: Additional filters to apply (e.g., `status`, `name`, `image_id`).

        Returns:
            list: A list of `openstack.compute.v2.server.Server` objects.
        """
        return list(
            self.os_conn.compute.servers(details=details, all_projects=all_projects, **filters)
        )

    def find_server(self, server_id, ignore_missing=True, details=True):
        """
        Retrieve an OpenStack server (instance).

        Args:
            server_id (str): The UUID or name of the server to find.
            ignore_missing (bool, optional): If True, returns None when
                the server does not exist. If False, an exception is raised.
                Defaults to True.
            details (bool, optional): If True, retrieve a more detailed
                server object. Defaults to True.

        Returns:
            openstack.compute.v2.server.Server: An OpenStack server object representing
            the specified server.
        """
        return self.os_conn.compute.find_server(
            server_id, ignore_missing=ignore_missing, details=details
        )

    def find_flavor(self, name_or_id, ignore_missing=True):
        """
        Retrieve an OpenStack compute flavor.

        Args:
            name_or_id (str): The UUID or name of the server to find.
            ignore_missing (bool, optional): If True, returns None when
                the flavor does not exist. If False, an exception is raised.
                Defaults to True.

        Returns:
            openstack.compute.v2.flavor.Flavor: An OpenStack flavor object representing
            the specified flavor.
        """
        return self.os_conn.compute.find_flavor(name_or_id, ignore_missing=ignore_missing)


class PlacementAPI:
    """
    A wrapper around OpenStack Placement API.

    This class provides methods to interact with OpenStack resource providers,
    retrieve allocation information, and query resource provider usage.

    Attributes:
        os_conn (openstack.connection.Connection): An authenticated OpenStack SDK
            connection object.
        placement_endpoint (str): The base URL for the Placement API.
    """

    def __init__(self, os_conn):
        self.os_conn = os_conn
        self.placement_endpoint = os_conn.placement.get_endpoint()

    def find_resource_provider(self, provider, ignore_missing=True):
        """
        Retrieve a single resource provider by name or ID.

        Args:
            provider (str): The name or ID of a resource provider.
            ignore_missing (bool, optional): If True, returns None when
                the resource provider does not exist. If False, raises an
                exception. Defaults to True.

        Return:
            openstack.placement.v1.resource_provider.ResourceProvider:
                An OpenStack resource provider instance
        """
        return self.os_conn.placement.find_resource_provider(
            provider, ignore_missing=ignore_missing
        )

    def retrieve_resource_providers(self, **filters):
        """
        Retrieve all resource providers.

        Args:
            **filters: Arbitrary keyword arguments to filter resource providers.

        Returns:
            list: A list of resource providers.
        """
        return self.os_conn.placement.resource_providers(**filters)

    def retrieve_provider_allocations(self, provider):
        """
        Retrieve allocations information for a given resource provider.

        This method looks for a link with "rel" == "allocations" in the
        provider's links, then queries that link to retrieve the allocations.

        Args:
            provider (openstack.placement.v1.resource_provider.ResourceProvider):
                The resource provider object for which to retrieve
                allocation information.

        Returns:
            dict or None: A dictionary of allocations if successful,
            or None if the provider lacks an allocations link or an
            unexpected error occurs.
        """
        allocations_link = next(
            (item for item in provider.links if item["rel"] == "allocations"), None
        )
        if allocations_link:
            allocations_response = self.os_conn.session.get(
                f"{self.placement_endpoint}{allocations_link['href']}"
            )
            allocations = allocations_response.json()["allocations"]
            return allocations
        return None

    def retrieve_provider_allocations_for_instance(self, server_id):
        """
        Retrieve allocations information for a given instance UUID.

        This method queries the Placement API endpoint
        `allocations/<server_id>` to get the allocation details.

        Args:
            server_id (str): The ID of the OpenStack instance

        Returns:
            dict: Allocation information for the instance.
        """
        url = f"{self.placement_endpoint}/allocations/{server_id}"
        allocations_response = self.os_conn.session.get(url)

        json_data = allocations_response.json()
        return json_data["allocations"]

    def retrieve_provider_usage(self, provider):
        """
        Retrieve usage information for a given resource provider.

        Args:
            provider (Provider): The provider to retrieve usage information for.

        Returns:
            dict: Usage information for the provider, or None if not found or an error occurs.
        """
        usages_link = next((item for item in provider.links if item["rel"] == "usages"), None)
        if usages_link:
            usage_response = self.os_conn.session.get(
                f"{self.placement_endpoint}{usages_link['href']}"
            )
            usage = usage_response.json()["usages"]
            return usage
        return None

    def retrieve_resource_provider_inventories(self, provider):
        """
        Retrieve inventories for a given resource provider.

        Args:
            provider (Provider): The provider to retrieve inventories for.

        Returns:
            list: Inventories of the provider.
        """
        return self.os_conn.placement.resource_provider_inventories(provider)


# vim: ts=4 sw=4 expandtab
