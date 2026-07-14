# file: tests/test_pi_scanner.py
from unittest.mock import MagicMock, patch

from node_scanner import is_port_open


@patch("node_scanner.socket.socket")
def test_is_port_open_success(mock_socket_class):
    """Tests is_port_open returns True when the port is open."""
    # Configure the mock to simulate a successful connection
    mock_sock_instance = MagicMock()
    mock_sock_instance.connect.return_value = None  # .connect returns None on success
    mock_socket_class.return_value = mock_sock_instance

    # Call the function directly
    assert is_port_open("127.0.0.1", 22) is True
    mock_sock_instance.connect.assert_called_once_with(("127.0.0.1", 22))


@patch("node_scanner.socket.socket")
def test_is_port_open_failure(mock_socket_class):
    """Tests is_port_open returns False when the port is closed."""
    # Configure the mock to simulate a failed connection
    mock_sock_instance = MagicMock()
    # .connect raises an exception on failure, which the function catches
    mock_sock_instance.connect.side_effect = ConnectionRefusedError
    mock_socket_class.return_value = mock_sock_instance

    # Call the function and assert failure
    assert is_port_open("127.0.0.1", 22) is False
    mock_sock_instance.connect.assert_called_once_with(("127.0.0.1", 22))
