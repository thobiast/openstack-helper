# test_common.py

"""Unit tests for the common is_valid_ip_address function."""

import subprocess
from unittest.mock import Mock, patch

from openstack_helper.common import ping_ip_address


def test_ping_ip_address_success():
    """Test that ping_ip_address returns True when ping is successful."""
    ip = "192.168.1.1"
    with patch("openstack_helper.common.subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0)
        assert ping_ip_address(ip) is True
        mock_run.assert_called_once()
        expected_command = ["ping", "-c", "1", "-W", "1", ip]
        mock_run.assert_called_with(
            expected_command,
            shell=False,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def test_ping_ip_address_failure():
    """Test that ping_ip_address returns False when ping fails."""
    ip = "192.168.1.1"
    with patch("openstack_helper.common.subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=1)
        assert ping_ip_address(ip) is False
        mock_run.assert_called_once()


def test_ping_ip_address_invalid_ip():
    """Test that ping_ip_address returns False when IP is invalid."""
    ip = "invalid_ip"
    with patch("openstack_helper.common.subprocess.run") as mock_run:
        assert ping_ip_address(ip) is False
        mock_run.assert_not_called()


def test_ping_ip_address_exception():
    """Test that ping_ip_address returns False when subprocess.run raises an OSError."""
    ip = "192.168.1.1"
    with patch(
        "openstack_helper.common.subprocess.run", side_effect=OSError("Test OSError")
    ) as mock_run:
        assert ping_ip_address(ip) is False
        mock_run.assert_called_once()


def test_ping_ip_address_custom_timeout():
    """Test that ping_ip_address uses the provided timeout."""
    ip = "192.168.1.1"
    timeout = 5
    with patch("openstack_helper.common.subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0)
        assert ping_ip_address(ip, timeout=timeout) is True
        expected_command = ["ping", "-c", "1", "-W", str(int(timeout)), ip]
        mock_run.assert_called_with(
            expected_command,
            shell=False,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
