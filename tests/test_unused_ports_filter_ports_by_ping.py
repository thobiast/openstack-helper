# test_filter_ports_by_ping.py

"""Unit tests for the filter_ports_by_ping function."""

from unittest.mock import patch

import pytest

from openstack_helper.unused_ports import filter_ports_by_ping


# Create a mock Port
class MockPort:
    """A mock Port class."""

    # pylint: disable=too-few-public-methods
    def __init__(self, port_id, fixed_ips):
        self.id = port_id
        self.fixed_ips = fixed_ips


@pytest.fixture(name="mock_ports")
def mock_ports_func():
    return [
        MockPort(port_id="port1", fixed_ips=[{"ip_address": "192.168.1.1"}]),
        MockPort(port_id="port2", fixed_ips=[{"ip_address": "192.168.1.2"}]),
        MockPort(port_id="port3", fixed_ips=[{"ip_address": "192.168.1.3"}]),
    ]


def test_filter_ports_by_ping_all_reachable(mock_ports):
    """All ports are reachable, so none should be returned"""
    with patch("openstack_helper.unused_ports.ping_port_ip_addresses", return_value=True):
        result = filter_ports_by_ping(mock_ports, max_workers=2)
        assert not result


def test_filter_ports_by_ping_all_unreachable(mock_ports):
    """All ports are unreachable, so all should be returned"""
    with patch("openstack_helper.unused_ports.ping_port_ip_addresses", return_value=False):
        result = filter_ports_by_ping(mock_ports, max_workers=2)
        assert set(result) == set(mock_ports)


def test_filter_ports_by_ping_mixed_reachability(mock_ports):
    def side_effect(port):
        return port.id == "port2"  # Only port2 is reachable

    with patch(
        "openstack_helper.unused_ports.ping_port_ip_addresses", side_effect=side_effect
    ):
        result = filter_ports_by_ping(mock_ports, max_workers=2)
        # Only port2 is reachable, so it should not be in the result
        expected_ports = [port for port in mock_ports if port.id != "port2"]
        assert set(result) == set(expected_ports)


def test_filter_ports_by_ping_no_eligible_ports():
    """Test no ports to process"""
    result = filter_ports_by_ping([], max_workers=2)
    assert not result
