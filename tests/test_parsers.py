# test_parsers.py

"""Unit tests for the parser function."""

from argparse import ArgumentTypeError
from unittest.mock import call, patch

import pytest

from openstack_helper.main import parse_uuid, parse_uuid_list

VALID_UUIDS = [
    "123e4567-e89b-12d3-a456-426614174000",
    "00000000-0000-0000-0000-000000000000",
    "ffffffff-ffff-ffff-ffff-ffffffffffff",
]

INVALID_UUIDS = [
    "invalid-uuid",
    "123e4567e89b12d3a456426614174000",
    "123e4567-e89b-12d3-a456-42661417400Z",  # Invalid char 'Z'
    "",
    "   ",
    "123e4567-e89b-12d3-a456-426614174000,invalid",
]


@pytest.fixture(name="mock_is_valid_uuid")
def mock_uuid_validator():
    """
    Fixture to mock the is_valid_uuid function.
    """
    with patch("openstack_helper.main.is_valid_uuid") as mock_uuid:
        yield mock_uuid


@pytest.mark.parametrize("uuid_str", VALID_UUIDS)
def test_parse_uuid_valid(uuid_str, mock_is_valid_uuid):
    """
    Test parse_uuid with valid UUIDs.
    """
    mock_is_valid_uuid.return_value = True
    assert parse_uuid(uuid_str) == uuid_str
    mock_is_valid_uuid.assert_called_once_with(uuid_str)


@pytest.mark.parametrize("uuid_str", INVALID_UUIDS)
def test_parse_uuid_invalid(uuid_str, mock_is_valid_uuid):
    """
    Test parse_uuid with invalid UUIDs.
    """
    mock_is_valid_uuid.return_value = False
    with pytest.raises(ArgumentTypeError) as exc_info:
        parse_uuid(uuid_str)
    expected_uuid = uuid_str.strip() if uuid_str.strip() else uuid_str
    assert f"Invalid UUID: '{expected_uuid}'" in str(exc_info.value)
    mock_is_valid_uuid.assert_called_once_with(uuid_str)


@pytest.mark.parametrize(
    "input_uuids, expected_output",
    [
        (
            "123e4567-e89b-12d3-a456-426614174000,123e4567-e89b-12d3-a456-426614174001",
            "123e4567-e89b-12d3-a456-426614174000,123e4567-e89b-12d3-a456-426614174001",
        ),
        (
            " 123e4567-e89b-12d3-a456-426614174000 , 123e4567-e89b-12d3-a456-426614174001 ",
            "123e4567-e89b-12d3-a456-426614174000,123e4567-e89b-12d3-a456-426614174001",
        ),
        ("123e4567-e89b-12d3-a456-426614174000", "123e4567-e89b-12d3-a456-426614174000"),
    ],
)
def test_parse_uuid_list_valid(input_uuids, expected_output, mock_is_valid_uuid):
    """
    Test parse_uuid_list with valid comma-separated UUIDs.
    """
    # Configure the mock to return True for all UUIDs
    mock_is_valid_uuid.return_value = True
    assert parse_uuid_list(input_uuids) == expected_output

    # Extract individual UUIDs after cleaning
    cleaned_uuids = [u.strip() for u in input_uuids.split(",") if u.strip()]

    # Check that is_valid_uuid is called for each UUID
    for uuid in cleaned_uuids:
        mock_is_valid_uuid.assert_any_call(uuid)
    assert mock_is_valid_uuid.call_count == len(cleaned_uuids)


@pytest.mark.parametrize(
    "input_uuids, invalid_uuid",
    [
        # Invalid UUID in the first position
        ("invalid-uuid,123e4567-e89b-12d3-a456-426614174000", "invalid-uuid"),
        ("invalid1,invalid2", "invalid1"),
    ],
)
def test_parse_uuid_list_invalid_uuid_first_position(
    input_uuids, invalid_uuid, mock_is_valid_uuid
):
    """
    Test parse_uuid_list with invalid UUIDs in the first position.
    Ensures that is_valid_uuid is called only for the first UUID.
    """

    # Setup the mock to return False for the invalid UUID and True otherwise
    def side_effect(uuid):
        return uuid != invalid_uuid

    mock_is_valid_uuid.side_effect = side_effect

    with pytest.raises(ArgumentTypeError) as exc_info:
        parse_uuid_list(input_uuids)
    assert f"Invalid UUID: '{invalid_uuid}'" in str(exc_info.value)

    # Extract individual UUIDs after cleaning
    called_uuids = [uuid.strip() for uuid in input_uuids.split(",") if uuid.strip()]

    # Expected calls are only for the first UUID
    expected_calls = [call(uuid) for uuid in called_uuids[:1]]

    mock_is_valid_uuid.assert_has_calls(expected_calls, any_order=False)
    assert mock_is_valid_uuid.call_count == len(expected_calls)


@pytest.mark.parametrize(
    "input_uuids, invalid_uuid",
    [
        # Invalid UUID in the second position
        ("123e4567-e89b-12d3-a456-426614174000,invalid-uuid", "invalid-uuid"),
    ],
)
def test_parse_uuid_list_invalid_uuid_second_position(
    input_uuids, invalid_uuid, mock_is_valid_uuid
):
    """
    Test parse_uuid_list with invalid UUIDs in the second position.
    Ensures that is_valid_uuid is called for the first and second UUIDs.
    """

    # Setup the mock to return False for the invalid UUID and True otherwise
    def side_effect(uuid):
        return uuid != invalid_uuid

    mock_is_valid_uuid.side_effect = side_effect

    with pytest.raises(ArgumentTypeError) as exc_info:
        parse_uuid_list(input_uuids)
    assert f"Invalid UUID: '{invalid_uuid}'" in str(exc_info.value)

    # Extract individual UUIDs after cleaning
    called_uuids = [uuid.strip() for uuid in input_uuids.split(",") if uuid.strip()]

    # Expected calls are for the first and second UUIDs
    expected_calls = [call(uuid) for uuid in called_uuids[:2]]

    mock_is_valid_uuid.assert_has_calls(expected_calls, any_order=False)
    assert mock_is_valid_uuid.call_count == len(expected_calls)
