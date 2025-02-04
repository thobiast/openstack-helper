# test_filter_unused_ports.py

"""Unit tests for the is_port_eligible function."""

from unittest.mock import Mock

import pytest

from openstack_helper.unused_ports import is_port_eligible


@pytest.fixture(name="mock_port")
def mock_port_fixture():
    """
    Fixture to provide a mock port object with default values.
    """
    port = Mock()
    port.id = "mock_port_id"
    port.name = "mock_port_name"
    return port


def test_port_eligible_all_checks_pass(mock_port):
    """
    Test case where all conditions for eligibility are met.
    """
    mock_port.status = "DOWN"
    mock_port.binding_host_id = None
    mock_port.binding_vif_details = None
    mock_port.binding_vif_type = "unbound"
    mock_port.device_owner = "expected_device_owner"

    assert is_port_eligible(mock_port, "expected_device_owner") is True


def test_port_not_eligible_status_not_down(mock_port):
    """
    Test case where the port status is not 'DOWN'
    """
    mock_port.status = "ACTIVE"
    mock_port.binding_host_id = None
    mock_port.binding_vif_details = None
    mock_port.binding_vif_type = "unbound"
    mock_port.device_owner = "expected_device_owner"

    assert is_port_eligible(mock_port, "expected_device_owner") is False


def test_port_not_eligible_binding_host_id_present(mock_port):
    """
    Test case where the port has a binding_host_id
    """
    mock_port.status = "DOWN"
    mock_port.binding_host_id = "some_host_id"
    mock_port.binding_vif_details = None
    mock_port.binding_vif_type = "unbound"
    mock_port.device_owner = "expected_device_owner"

    assert is_port_eligible(mock_port, "expected_device_owner") is False


def test_port_not_eligible_binding_vif_details_present(mock_port):
    """
    Test case where the port has binding_vif_details
    """
    mock_port.status = "DOWN"
    mock_port.binding_host_id = None
    mock_port.binding_vif_details = {"vif_details": "present"}
    mock_port.binding_vif_type = "unbound"
    mock_port.device_owner = "expected_device_owner"

    assert is_port_eligible(mock_port, "expected_device_owner") is False


def test_port_not_eligible_binding_vif_type_not_unbound(mock_port):
    """
    Test case where the port binding_vif_type is not 'unbound'
    """
    mock_port.status = "DOWN"
    mock_port.binding_host_id = None
    mock_port.binding_vif_details = None
    mock_port.binding_vif_type = "some_other_type"
    mock_port.device_owner = "expected_device_owner"

    assert is_port_eligible(mock_port, "expected_device_owner") is False


def test_port_not_eligible_device_owner_mismatch(mock_port):
    """
    Test case where the port device_owner does not match the expected value
    """
    mock_port.status = "DOWN"
    mock_port.binding_host_id = None
    mock_port.binding_vif_details = None
    mock_port.binding_vif_type = "unbound"
    mock_port.device_owner = "wrong_device_owner"

    assert is_port_eligible(mock_port, "expected_device_owner") is False
