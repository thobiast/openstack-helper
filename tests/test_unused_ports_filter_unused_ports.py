# test_filter_unused_ports.py

"""Unit tests for the filter_unused_ports function."""

from dataclasses import dataclass
from unittest.mock import patch

import pytest

from openstack_helper.unused_ports import filter_unused_ports


@dataclass
class MockPort:
    """A mock Port class."""

    id: str
    name: str
    status: str
    binding_host_id: str
    binding_vif_details: dict
    binding_vif_type: str
    device_owner: str


@pytest.mark.parametrize(
    "port_attributes,expected_eligible",
    [
        # Test case 1: All conditions passing, port should be eligible
        (
            {
                "id": "port1",
                "name": "Test Port 1",
                "status": "DOWN",
                "binding_host_id": None,
                "binding_vif_details": None,
                "binding_vif_type": "unbound",
                "device_owner": "some_device_owner",
            },
            True,
        ),
        # Test case 2: Status not DOWN, port should not be eligible
        (
            {
                "id": "port2",
                "name": "Test Port 2",
                "status": "ACTIVE",  # Not 'DOWN'
                "binding_host_id": None,
                "binding_vif_details": None,
                "binding_vif_type": "unbound",
                "device_owner": "some_device_owner",
            },
            False,
        ),
        # Test case 3: binding_host_id is set, port should not be eligible
        (
            {
                "id": "port3",
                "name": "Test Port 3",
                "status": "DOWN",
                "binding_host_id": "some_host_id",  # Should be None or empty
                "binding_vif_details": None,
                "binding_vif_type": "unbound",
                "device_owner": "some_device_owner",
            },
            False,
        ),
        # Test case 4: binding_vif_details is set, port should not be eligible
        (
            {
                "id": "port4",
                "name": "Test Port 4",
                "status": "DOWN",
                "binding_host_id": None,
                "binding_vif_details": {"some": "details"},  # Should be None or empty
                "binding_vif_type": "unbound",
                "device_owner": "some_device_owner",
            },
            False,
        ),
        # Test case 5: binding_vif_type not 'unbound', port should not be eligible
        (
            {
                "id": "port5",
                "name": "Test Port 5",
                "status": "DOWN",
                "binding_host_id": None,
                "binding_vif_details": None,
                "binding_vif_type": "ovs",  # Not 'unbound'
                "device_owner": "some_device_owner",
            },
            False,
        ),
        # Test case 6: device_owner does not match, port should not be eligible
        (
            {
                "id": "port6",
                "name": "Test Port 6",
                "status": "DOWN",
                "binding_host_id": None,
                "binding_vif_details": None,
                "binding_vif_type": "unbound",
                "device_owner": "different_device_owner",
            },
            False,
        ),
    ],
)
def test_filter_unused_ports_parametrized(port_attributes, expected_eligible):
    # Prepare parameters
    device_owner = "some_device_owner"
    port = MockPort(**port_attributes)
    ports = [port]

    # Call function
    eligible_ports = filter_unused_ports(ports, device_owner, ping=False)

    # Check result
    if expected_eligible:
        assert eligible_ports == ports
    else:
        assert not eligible_ports


def test_filter_unused_ports_no_eligible_ports_no_ping():
    """
    Ping true, but port is not elegible. Should not call ping
    """
    device_owner = "some_device_owner"
    port1 = MockPort(
        id="port1",
        name="Port 1",
        status="ACTIVE",  # Not 'DOWN'
        binding_host_id=None,
        binding_vif_details=None,
        binding_vif_type="unbound",
        device_owner=device_owner,
    )
    ports = [port1]

    # Ensure filter_ports_by_ping is not called
    with patch("openstack_helper.unused_ports.filter_ports_by_ping") as mock_filter_ping:
        eligible_ports = filter_unused_ports(ports, device_owner, ping=True)
        assert not eligible_ports
        mock_filter_ping.assert_not_called()


@pytest.mark.parametrize(
    "ping_flag, expected_call_count",
    [
        (False, 0),
        (True, 1),
    ],
)
def test_filter_unused_ports_ping_flag(ping_flag, expected_call_count):
    """
    Port is elegible. Call ping as the user option parameter
    """
    device_owner = "some_device_owner"
    port = MockPort(
        id="port1",
        name="Port 1",
        status="DOWN",
        binding_host_id=None,
        binding_vif_details=None,
        binding_vif_type="unbound",
        device_owner=device_owner,
    )
    ports = [port]

    # Mock filter_ports_by_ping
    with patch(
        "openstack_helper.unused_ports.filter_ports_by_ping", return_value=ports
    ) as mock_filter_ping:
        eligible_ports = filter_unused_ports(ports, device_owner, ping=ping_flag)
        assert eligible_ports == ports
        assert mock_filter_ping.call_count == expected_call_count


@pytest.mark.parametrize(
    "filter_ports_by_ping_return, expected_ports",
    [
        # Test case where filter_ports_by_ping returns an empty list
        ([], []),
        # Test case where filter_ports_by_ping returns the same list of ports
        (["input_ports"], ["input_ports"]),
    ],
)
def test_filter_unused_ports_with_ping(filter_ports_by_ping_return, expected_ports):
    """
    Test if it return elegible ports as returned by filter_ports_by_ping func
    """
    device_owner = "some_device_owner"
    port = MockPort(
        id="port1",
        name="Port 1",
        status="DOWN",
        binding_host_id=None,
        binding_vif_details=None,
        binding_vif_type="unbound",
        device_owner=device_owner,
    )
    ports = [port]

    # Prepare the return value for filter_ports_by_ping
    if filter_ports_by_ping_return == ["input_ports"]:
        return_value = ports
    else:
        return_value = filter_ports_by_ping_return

    # Prepare the expected eligible ports
    if expected_ports == ["input_ports"]:
        expected_eligible_ports = ports
    else:
        expected_eligible_ports = expected_ports

    with patch(
        "openstack_helper.unused_ports.filter_ports_by_ping", return_value=return_value
    ):
        eligible_ports = filter_unused_ports(ports, device_owner, ping=True)

    assert eligible_ports == expected_eligible_ports
