# tests/test_ssh_manager.py
# noinspection DuplicatedCode
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from src.managers.ssh_manager import SSHManager


class TestSSHManagerKeyManagement(unittest.TestCase):
    """Test suite for SSH key management in SSHManager."""

    def setUp(self):
        """Set up test fixtures with mocked dependencies."""
        self.mock_key = MagicMock()
        self.mock_key.get_name.return_value = "ssh-ed25519"
        self.mock_key.get_base64.return_value = "AAAAC3NzaC1lZDI1NTE5AAAAITESTKEY"

        self.temp_dir = tempfile.mkdtemp()
        self.key_file = Path(self.temp_dir) / "id_ed25519_njorddeploy"

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    @patch("src.managers.ssh_manager.user_data_dir")
    def test_init_sets_correct_key_path(self, mock_user_data_dir):
        """Verify that the key file path is correctly set via appdirs."""
        mock_user_data_dir.return_value = self.temp_dir
        ssh_mgr = SSHManager("192.168.1.100", "pi", "password")

        self.assertEqual(ssh_mgr.key_file, self.key_file)
        mock_user_data_dir.assert_called_once_with("NjordDeploy", "NjordDeploy")

    @patch("src.managers.ssh_manager.user_data_dir")
    def test_get_or_create_key_existing(self, mock_user_data_dir):
        """Test loading an existing SSH key."""
        mock_user_data_dir.return_value = self.temp_dir

        existing_key_content = (
            "-----BEGIN OPENSSH PRIVATE KEY-----\n"
            "test_existing_key_data\n"
            "-----END OPENSSH PRIVATE KEY-----\n"
        )

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=existing_key_content)),
            patch("src.managers.ssh_manager.Ed25519Key") as mock_ed25519,
        ):
            mock_ed25519.from_private_key_file.return_value = self.mock_key

            ssh_mgr = SSHManager("192.168.1.100", "pi", "password")
            ssh_mgr.key_file = self.key_file
            key = ssh_mgr._get_or_create_key()

            mock_ed25519.from_private_key_file.assert_called_once_with(
                str(self.key_file)
            )
            self.assertEqual(key, self.mock_key)

    @patch("src.managers.ssh_manager.user_data_dir")
    @patch("src.managers.ssh_manager.ed25519")
    @patch("src.managers.ssh_manager.crypto_serialization")
    @patch("src.managers.ssh_manager.Ed25519Key")
    def test_get_or_create_key_generate_new(
        self, mock_ed25519_key, mock_crypto, mock_ed25519, mock_user_data_dir
    ):
        """Test generating a new Ed25519 key when none exists."""
        mock_user_data_dir.return_value = self.temp_dir

        mock_private_key = MagicMock()
        mock_private_key.private_bytes.return_value = b"private_key_bytes"
        mock_ed25519.Ed25519PrivateKey.generate.return_value = mock_private_key

        mock_crypto.Encoding.PEM = "PEM"
        mock_crypto.PrivateFormat.OpenSSH = "OpenSSH"
        mock_crypto.NoEncryption = MagicMock(return_value="NoEncryption")

        mock_ed25519_key.from_private_key_file.return_value = self.mock_key

        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("builtins.open", mock_open()) as mock_file,
            patch("pathlib.Path.chmod"),
        ):
            ssh_mgr = SSHManager("192.168.1.100", "pi", "password")
            ssh_mgr.key_file = self.key_file
            key = ssh_mgr._get_or_create_key()

            mock_ed25519.Ed25519PrivateKey.generate.assert_called_once()
            mock_file.assert_called_with(self.key_file, "wb")
            self.assertEqual(key, self.mock_key)

    @patch("src.managers.ssh_manager.user_data_dir")
    @patch("src.managers.ssh_manager.ed25519")
    @patch("src.managers.ssh_manager.crypto_serialization")
    @patch("src.managers.ssh_manager.Ed25519Key")
    def test_key_file_permissions_set_to_600(
        self, mock_ed25519_key, mock_crypto, mock_ed25519, mock_user_data_dir
    ):
        """Verify that the private key file has 0600 permissions."""
        mock_user_data_dir.return_value = self.temp_dir

        mock_private_key = MagicMock()
        mock_private_key.private_bytes.return_value = b"private_key_bytes"
        mock_ed25519.Ed25519PrivateKey.generate.return_value = mock_private_key

        mock_crypto.Encoding.PEM = "PEM"
        mock_crypto.PrivateFormat.OpenSSH = "OpenSSH"
        mock_crypto.NoEncryption = MagicMock(return_value="NoEncryption")

        mock_ed25519_key.from_private_key_file.return_value = self.mock_key

        chmod_calls = []

        def mock_chmod(mode, *_args, **_kwargs):
            chmod_calls.append(mode)

        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("builtins.open", mock_open()),
            patch("pathlib.Path.chmod", side_effect=mock_chmod),
        ):
            ssh_mgr = SSHManager("192.168.1.100", "pi", "password")
            ssh_mgr.key_file = self.key_file
            ssh_mgr._get_or_create_key()

            self.assertEqual(len(chmod_calls), 1)
            self.assertEqual(chmod_calls[0], 0o600)


class TestSSHManagerConnect(unittest.TestCase):
    """Test suite for SSH connection functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.mock_transport = MagicMock()

        self.temp_dir = tempfile.mkdtemp()
        self.key_file = Path(self.temp_dir) / "id_ed25519_njorddeploy"

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    @patch("src.managers.ssh_manager.user_data_dir")
    @patch("src.managers.ssh_manager.SSHClient")
    def test_connect_ssh_key_success(self, mock_ssh_client, mock_user_data_dir):
        """Test successful SSH connection using key-based authentication."""
        mock_user_data_dir.return_value = self.temp_dir
        mock_client_instance = MagicMock()
        mock_ssh_client.return_value = mock_client_instance
        mock_client_instance.connect.return_value = None

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("src.managers.ssh_manager.paramiko.RejectPolicy"),
        ):
            ssh_mgr = SSHManager("192.168.1.100", "pi", "password")
            ssh_mgr.key_file = self.key_file
            success, message = ssh_mgr.connect()

            self.assertTrue(success)
            self.assertIn("SSH Key", message)
            mock_client_instance.connect.assert_called()

    @patch("src.managers.ssh_manager.user_data_dir")
    @patch("src.managers.ssh_manager.SSHClient")
    def test_connect_password_fallback(self, mock_ssh_client, mock_user_data_dir):
        """Test fallback to password authentication when key fails."""
        mock_user_data_dir.return_value = self.temp_dir
        mock_client_instance = MagicMock()
        mock_ssh_client.return_value = mock_client_instance

        import paramiko

        mock_client_instance.connect.side_effect = [
            paramiko.AuthenticationException("Key auth failed"),
            None,
        ]

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("src.managers.ssh_manager.paramiko.RejectPolicy"),
        ):
            ssh_mgr = SSHManager("192.168.1.100", "pi", "password123")
            ssh_mgr.key_file = self.key_file
            success, message = ssh_mgr.connect()

            self.assertTrue(success)
            self.assertIn("Password", message)
            self.assertEqual(mock_client_instance.connect.call_count, 2)

    @patch("src.managers.ssh_manager.user_data_dir")
    @patch("src.managers.ssh_manager.SSHClient")
    def test_connect_failure(self, mock_ssh_client, mock_user_data_dir):
        """Test connection failure returns False with error message."""
        mock_user_data_dir.return_value = self.temp_dir
        mock_client_instance = MagicMock()
        mock_ssh_client.return_value = mock_client_instance
        mock_client_instance.connect.side_effect = Exception("Refused")

        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("src.managers.ssh_manager.paramiko.RejectPolicy"),
        ):
            ssh_mgr = SSHManager("192.168.1.100", "pi", "password")
            ssh_mgr.key_file = self.key_file
            success, message = ssh_mgr.connect()

            self.assertFalse(success)
            self.assertEqual(message, "Refused")

    @patch("src.managers.ssh_manager.user_data_dir")
    @patch("src.managers.ssh_manager.SSHClient")
    @patch("pathlib.Path.exists", return_value=False)
    @patch("src.managers.ssh_manager.paramiko.RejectPolicy")
    def test_connect_sets_missing_host_key_policy(
        self, mock_reject_policy, _mock_exists, mock_ssh_client, mock_user_data_dir
    ):
        """Verify that RejectPolicy is set for host keys."""
        mock_user_data_dir.return_value = self.temp_dir
        mock_client_instance = MagicMock()
        mock_ssh_client.return_value = mock_client_instance

        ssh_mgr = SSHManager("192.168.1.100", "pi", "password")
        ssh_mgr.connect()

        mock_client_instance.set_missing_host_key_policy.assert_called_once_with(
            mock_reject_policy.return_value
        )


class TestSSHManagerExecuteCommand(unittest.TestCase):
    """Test suite for command execution via SSH."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    @patch("src.managers.ssh_manager.user_data_dir")
    def test_execute_command_no_client(self, mock_user_data_dir):
        """Test executing command without connection returns error."""
        mock_user_data_dir.return_value = self.temp_dir

        ssh_mgr = SSHManager("192.168.1.100", "pi", "password")
        ssh_mgr.client = None

        log_output = []

        def log_callback(msg: str) -> None:
            log_output.append(msg)

        exit_code, output = ssh_mgr.execute_command("ls", log_callback)

        self.assertEqual(exit_code, -1)
        self.assertIn("not connected", "".join(log_output))

    @patch("src.managers.ssh_manager.user_data_dir")
    def test_execute_command_no_transport(self, mock_user_data_dir):
        """Test executing command without transport returns error."""
        mock_user_data_dir.return_value = self.temp_dir

        mock_client = MagicMock()
        mock_client.get_transport.return_value = None

        ssh_mgr = SSHManager("192.168.1.100", "pi", "password")
        ssh_mgr.client = mock_client

        log_output = []

        def log_callback(msg: str) -> None:
            log_output.append(msg)

        exit_code, output = ssh_mgr.execute_command("ls", log_callback)

        self.assertEqual(exit_code, -1)
        self.assertIn("transport", "".join(log_output).lower())

    @patch("src.managers.ssh_manager.user_data_dir")
    def test_execute_command_success(self, mock_user_data_dir):
        """Test successful command execution."""
        mock_user_data_dir.return_value = self.temp_dir

        mock_client = MagicMock()
        mock_transport = MagicMock()
        mock_channel = MagicMock()

        mock_client.get_transport.return_value = mock_transport
        mock_transport.open_session.return_value = mock_channel
        mock_channel.exit_status_ready.return_value = True
        mock_channel.recv_exit_status.return_value = 0
        mock_channel.recv_ready.return_value = False

        ssh_mgr = SSHManager("192.168.1.100", "pi", "password")
        ssh_mgr.client = mock_client

        log_output = []

        def log_callback(msg: str) -> None:
            log_output.append(msg)

        exit_code, output = ssh_mgr.execute_command("echo hello", log_callback)

        self.assertEqual(exit_code, 0)

    @patch("src.managers.ssh_manager.user_data_dir")
    def test_execute_command_failure_non_zero_exit(self, mock_user_data_dir):
        """Test command execution with non-zero exit code."""
        mock_user_data_dir.return_value = self.temp_dir

        mock_client = MagicMock()
        mock_transport = MagicMock()
        mock_channel = MagicMock()

        mock_client.get_transport.return_value = mock_transport
        mock_transport.open_session.return_value = mock_channel
        mock_channel.exit_status_ready.return_value = True
        mock_channel.recv_exit_status.return_value = 1

        ssh_mgr = SSHManager("192.168.1.100", "pi", "password")
        ssh_mgr.client = mock_client

        log_output = []

        def log_callback(msg: str) -> None:
            log_output.append(msg)

        exit_code, output = ssh_mgr.execute_command("false", log_callback)

        self.assertEqual(exit_code, 1)
        self.assertIn("failed", "".join(log_output).lower())


class TestSSHManagerSetupSSHKey(unittest.TestCase):
    """Test suite for SSH key deployment to remote host."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    @patch("src.managers.ssh_manager.user_data_dir")
    @patch("src.managers.ssh_manager.SSHClient")
    def test_setup_ssh_key_success(self, mock_ssh_client, mock_user_data_dir):
        """Test successful SSH key setup on remote host."""
        mock_user_data_dir.return_value = self.temp_dir
        mock_transport = MagicMock()
        mock_channel = MagicMock()

        mock_ssh_client.get_transport.return_value = mock_transport
        mock_transport.open_session.return_value = mock_channel
        mock_channel.exit_status_ready.return_value = True
        mock_channel.recv_exit_status.return_value = 0
        mock_channel.recv_ready.return_value = False

        ssh_mgr = SSHManager("192.168.1.100", "pi", "password")
        ssh_mgr.client = mock_ssh_client

        mock_key = MagicMock()
        mock_key.get_name.return_value = "ssh-ed25519"
        mock_key.get_base64.return_value = "AAAAC3NzaC1lZDI1NTE5AAAAITESTKEY"

        with patch.object(ssh_mgr, "_get_or_create_key", return_value=mock_key):
            log_output = []

            def log_callback(msg: str) -> None:
                log_output.append(msg)

            result = ssh_mgr.setup_ssh_key(log_callback)

            self.assertTrue(result)
            self.assertIn("successfully deployed", "".join(log_output))

    @patch("src.managers.ssh_manager.user_data_dir")
    @patch("src.managers.ssh_manager.SSHClient")
    def test_setup_ssh_key_failure(self, mock_ssh_client, mock_user_data_dir):
        """Test SSH key setup failure when command fails."""
        mock_user_data_dir.return_value = self.temp_dir

        mock_key = MagicMock()
        mock_key.get_name.return_value = "ssh-ed25519"
        mock_key.get_base64.return_value = "AAAAC3NzaC1lZDI1NTE5AAAAITESTKEY"

        mock_transport = MagicMock()
        mock_channel = MagicMock()

        mock_ssh_client.get_transport.return_value = mock_transport
        mock_transport.open_session.return_value = mock_channel
        mock_channel.exit_status_ready.return_value = True
        mock_channel.recv_exit_status.return_value = 1

        ssh_mgr = SSHManager("192.168.1.100", "pi", "password")
        ssh_mgr.client = mock_ssh_client

        with patch.object(ssh_mgr, "_get_or_create_key", return_value=mock_key):
            log_output = []

            def log_callback(msg: str) -> None:
                log_output.append(msg)

            result = ssh_mgr.setup_ssh_key(log_callback)

            self.assertFalse(result)


class TestSSHManagerUploadContent(unittest.TestCase):
    """Test suite for file upload functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    @patch("src.managers.ssh_manager.user_data_dir")
    def test_upload_content_no_client(self, mock_user_data_dir):
        """Test upload returns False when client is not connected."""
        mock_user_data_dir.return_value = self.temp_dir

        ssh_mgr = SSHManager("192.168.1.100", "pi", "password")
        ssh_mgr.client = None

        success, message = ssh_mgr.upload_content(b"content", "/remote/path")

        self.assertFalse(success)
        self.assertIn("not connected", message.lower())

    @patch("src.managers.ssh_manager.user_data_dir")
    def test_upload_content_success(self, mock_user_data_dir):
        """Test successful file content upload."""
        mock_user_data_dir.return_value = self.temp_dir

        mock_client = MagicMock()
        mock_sftp = MagicMock()
        mock_sftp_file = MagicMock()

        mock_client.open_sftp.return_value = mock_sftp
        mock_sftp.open.return_value.__enter__ = MagicMock(return_value=mock_sftp_file)
        mock_sftp.open.return_value.__exit__ = MagicMock(return_value=False)

        ssh_mgr = SSHManager("192.168.1.100", "pi", "password")
        ssh_mgr.client = mock_client

        content = b"test content data"
        success, message = ssh_mgr.upload_content(content, "/home/pi/test.txt")

        self.assertTrue(success)
        mock_sftp.open.assert_called_once_with("/home/pi/test.txt", "wb")

    @patch("src.managers.ssh_manager.user_data_dir")
    def test_upload_content_failure(self, mock_user_data_dir):
        """Test file upload handles exceptions correctly."""
        mock_user_data_dir.return_value = self.temp_dir

        mock_client = MagicMock()
        mock_client.open_sftp.side_effect = Exception("Permission denied")

        ssh_mgr = SSHManager("192.168.1.100", "pi", "password")
        ssh_mgr.client = mock_client

        success, message = ssh_mgr.upload_content(b"content", "/root/test.txt")

        self.assertFalse(success)
        self.assertIn("Permission denied", message)


class TestSSHManagerClose(unittest.TestCase):
    """Test suite for connection cleanup."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    @patch("src.managers.ssh_manager.user_data_dir")
    def test_close_connections(self, mock_user_data_dir):
        """Test that client and SFTP are properly closed."""
        mock_user_data_dir.return_value = self.temp_dir

        mock_client = MagicMock()
        mock_sftp = MagicMock()

        ssh_mgr = SSHManager("192.168.1.100", "pi", "password")
        ssh_mgr.client = mock_client
        ssh_mgr.sftp = mock_sftp

        ssh_mgr.close()

        mock_sftp.close.assert_called_once()
        mock_client.close.assert_called_once()
        self.assertIsNone(ssh_mgr.client)
        self.assertIsNone(ssh_mgr.sftp)

    @patch("src.managers.ssh_manager.user_data_dir")
    def test_close_idempotent(self, mock_user_data_dir):
        """Test that multiple close calls do not cause errors."""
        mock_user_data_dir.return_value = self.temp_dir

        mock_client = MagicMock()

        ssh_mgr = SSHManager("192.168.1.100", "pi", "password")
        ssh_mgr.client = mock_client

        ssh_mgr.close()
        ssh_mgr.close()

        mock_client.close.assert_called_once()


class TestExecuteCommandStreaming(unittest.TestCase):
    """Test suite for streaming output during command execution."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    @patch("src.managers.ssh_manager.user_data_dir")
    @patch("src.managers.ssh_manager.select.select")
    def test_execute_command_streams_stdout(self, mock_select, mock_user_data_dir):
        """Test that stdout chunks are streamed via log callback."""
        mock_user_data_dir.return_value = self.temp_dir

        mock_client = MagicMock()
        mock_transport = MagicMock()
        mock_channel = MagicMock()

        mock_client.get_transport.return_value = mock_transport
        mock_transport.open_session.return_value = mock_channel
        mock_select.return_value = ([mock_channel], [], [])

        mock_channel.exit_status_ready.side_effect = [False, False, True]
        mock_channel.recv_ready.side_effect = [True, False]
        mock_channel.recv_stderr_ready.return_value = False
        mock_channel.recv.return_value = b"Hello World\n"
        mock_channel.recv_exit_status.return_value = 0

        ssh_mgr = SSHManager("192.168.1.100", "pi", "password")
        ssh_mgr.client = mock_client

        log_output = []

        def log_callback(msg: str) -> None:
            log_output.append(msg)

        exit_code, output = ssh_mgr.execute_command("echo hello", log_callback)

        self.assertEqual(exit_code, 0)
        self.assertTrue(any("Hello World" in msg for msg in log_output))

    @patch("src.managers.ssh_manager.user_data_dir")
    @patch("src.managers.ssh_manager.select.select")
    def test_execute_command_streams_stderr(self, mock_select, mock_user_data_dir):
        """Test that stderr chunks are streamed via log callback."""
        mock_user_data_dir.return_value = self.temp_dir

        mock_client = MagicMock()
        mock_transport = MagicMock()
        mock_channel = MagicMock()

        mock_client.get_transport.return_value = mock_transport
        mock_transport.open_session.return_value = mock_channel
        mock_select.return_value = ([mock_channel], [], [])

        mock_channel.exit_status_ready.side_effect = [False, False, True]
        mock_channel.recv_ready.return_value = False
        mock_channel.recv_stderr_ready.side_effect = [True, False]
        mock_channel.recv_stderr.return_value = b"Error message\n"
        mock_channel.recv_exit_status.return_value = 0

        ssh_mgr = SSHManager("192.168.1.100", "pi", "password")
        ssh_mgr.client = mock_client

        log_output = []

        def log_callback(msg: str) -> None:
            log_output.append(msg)

        _exit_code, _output = ssh_mgr.execute_command("ls /nonexistent", log_callback)

        self.assertTrue(any("Error message" in msg for msg in log_output))

    @patch("src.managers.ssh_manager.user_data_dir")
    @patch("src.managers.ssh_manager.select.select")
    def test_execute_command_combines_output(self, mock_select, mock_user_data_dir):
        """Test that stdout chunks are combined into full output."""
        mock_user_data_dir.return_value = self.temp_dir

        mock_client = MagicMock()
        mock_transport = MagicMock()
        mock_channel = MagicMock()

        mock_client.get_transport.return_value = mock_transport
        mock_transport.open_session.return_value = mock_channel
        mock_select.return_value = ([mock_channel], [], [])

        mock_channel.exit_status_ready.side_effect = [False, False, True]
        mock_channel.recv_ready.side_effect = [True, True, False]
        mock_channel.recv_stderr_ready.return_value = False
        mock_channel.recv.side_effect = [b"Line 1\n", b"Line 2\n"]
        mock_channel.recv_exit_status.return_value = 0

        ssh_mgr = SSHManager("192.168.1.100", "pi", "password")
        ssh_mgr.client = mock_client

        log_output = []

        def log_callback(msg: str) -> None:
            log_output.append(msg)

        exit_code, output = ssh_mgr.execute_command("echo test", log_callback)

        self.assertIn("Line 1", output)
        self.assertIn("Line 2", output)


class TestExecuteCommandCheckExitCode(unittest.TestCase):
    """Test suite for the check_exit_code parameter."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    @patch("src.managers.ssh_manager.user_data_dir")
    def test_execute_command_skip_exit_code_check(self, mock_user_data_dir):
        """Test that error is not logged when check_exit_code is False."""
        mock_user_data_dir.return_value = self.temp_dir

        mock_client = MagicMock()
        mock_transport = MagicMock()
        mock_channel = MagicMock()

        mock_client.get_transport.return_value = mock_transport
        mock_transport.open_session.return_value = mock_channel
        mock_channel.exit_status_ready.return_value = True
        mock_channel.recv_exit_status.return_value = 1
        mock_channel.recv_ready.return_value = False

        ssh_mgr = SSHManager("192.168.1.100", "pi", "password")
        ssh_mgr.client = mock_client

        log_output = []

        def log_callback(msg: str) -> None:
            log_output.append(msg)

        exit_code, _ = ssh_mgr.execute_command(
            "false", log_callback, check_exit_code=False
        )

        self.assertEqual(exit_code, 1)
        log_text = "".join(log_output).lower()
        self.assertNotIn("failed", log_text)

    @patch("src.managers.ssh_manager.user_data_dir")
    def test_execute_command_long_command_truncation(self, mock_user_data_dir):
        """Test that long commands are truncated in error messages."""
        mock_user_data_dir.return_value = self.temp_dir

        mock_client = MagicMock()
        mock_transport = MagicMock()
        mock_channel = MagicMock()

        mock_client.get_transport.return_value = mock_transport
        mock_transport.open_session.return_value = mock_channel
        mock_channel.exit_status_ready.return_value = True
        mock_channel.recv_exit_status.return_value = 1
        mock_channel.recv_ready.return_value = False

        ssh_mgr = SSHManager("192.168.1.100", "pi", "password")
        ssh_mgr.client = mock_client

        log_output = []

        def log_callback(msg: str) -> None:
            log_output.append(msg)

        long_command = "a" * 50
        ssh_mgr.execute_command(long_command, log_callback)

        log_text = "".join(log_output)
        self.assertIn("...", log_text)
        self.assertNotIn(long_command, log_text)


class TestUploadContentPipelining(unittest.TestCase):
    """Test suite for SFTP pipelining functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    @patch("src.managers.ssh_manager.user_data_dir")
    def test_upload_content_enables_pipelining(self, mock_user_data_dir):
        """Test that pipelining is enabled for faster uploads."""
        mock_user_data_dir.return_value = self.temp_dir

        mock_client = MagicMock()
        mock_sftp = MagicMock()
        mock_sftp_file = MagicMock()

        mock_client.open_sftp.return_value = mock_sftp
        mock_sftp.open.return_value.__enter__ = MagicMock(return_value=mock_sftp_file)
        mock_sftp.open.return_value.__exit__ = MagicMock(return_value=False)

        ssh_mgr = SSHManager("192.168.1.100", "pi", "password")
        ssh_mgr.client = mock_client

        ssh_mgr.upload_content(b"test content", "/home/pi/test.txt")

        mock_sftp_file.set_pipelined.assert_called_once_with(True)


class TestSetupSSHKeyPublicKeyFormat(unittest.TestCase):
    """Test suite for SSH key public key format in setup_ssh_key."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    @patch("src.managers.ssh_manager.user_data_dir")
    @patch("src.managers.ssh_manager.SSHClient")
    def test_setup_ssh_key_public_key_format(
        self, _mock_ssh_client, mock_user_data_dir
    ):
        """Test that public key is correctly formatted for authorized_keys."""
        mock_user_data_dir.return_value = self.temp_dir

        mock_key = MagicMock()
        mock_key.get_name.return_value = "ssh-ed25519"
        mock_key.get_base64.return_value = "AAAAC3NzaC1lZDI1NTE5AAAAITESTKEYBASE64"

        mock_client = MagicMock()
        mock_transport = MagicMock()
        mock_channel = MagicMock()

        mock_client.get_transport.return_value = mock_transport
        mock_transport.open_session.return_value = mock_channel
        mock_channel.exit_status_ready.return_value = True
        mock_channel.recv_exit_status.return_value = 0
        mock_channel.recv_ready.return_value = False

        ssh_mgr = SSHManager("192.168.1.100", "pi", "password")
        ssh_mgr.client = mock_client

        public_key_used: str = ""

        def capture_echo(cmd, *_args, **_kwargs):
            nonlocal public_key_used
            if "echo" in cmd and "ssh-ed25519" in cmd:
                public_key_used = cmd
            return 0, ""

        with patch.object(ssh_mgr, "_get_or_create_key", return_value=mock_key):
            with patch.object(ssh_mgr, "execute_command", side_effect=capture_echo):

                def log_callback(_msg: str) -> None:
                    pass

                ssh_mgr.setup_ssh_key(log_callback)

        self.assertNotEqual(
            public_key_used, "", "Public key should be used in echo command"
        )
        self.assertIn("ssh-ed25519", public_key_used)
        self.assertIn("AAAAC3NzaC1lZDI1NTE5AAAAITESTKEYBASE64", public_key_used)


if __name__ == "__main__":
    unittest.main()
