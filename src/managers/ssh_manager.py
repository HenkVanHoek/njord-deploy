# src/managers/ssh_manager.py
import select
from pathlib import Path
from typing import Callable, Optional, Tuple

import paramiko
from appdirs import user_data_dir
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from paramiko import Ed25519Key, SFTPClient, SSHClient


class SSHManager:
    """Manages SSH connections and command execution on a remote host."""

    def __init__(
        self,
        hostname: str,
        username: str,
        password: str,
        port: int = 22,
        allow_auto_add: bool = False,
        load_system_keys: bool = True,
    ):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self.allow_auto_add = allow_auto_add
        self.load_system_keys = load_system_keys
        self.client: Optional[SSHClient] = None
        self.sftp: Optional[SFTPClient] = None

        # Determine the local path for the SSH private key
        app_data_dir = Path(user_data_dir("NjordDeploy", "NjordDeploy"))
        app_data_dir.mkdir(parents=True, exist_ok=True)
        self.key_file = app_data_dir / "id_ed25519_njorddeploy"

    def get_ssh_key(self) -> Ed25519Key:
        """Retrieves the active SSH key."""
        return self._get_or_create_key()

    def _get_or_create_key(self) -> Ed25519Key:
        """Retrieves an existing Ed25519 key or generates a new one."""
        if self.key_file.exists():
            return Ed25519Key.from_private_key_file(str(self.key_file))

        # ROBUST FIX: Many Paramiko versions lack Ed25519Key.generate().
        # We use the cryptography library directly to generate the key pair.
        private_key = ed25519.Ed25519PrivateKey.generate()

        # Export to OpenSSH format
        private_bytes = private_key.private_bytes(
            encoding=crypto_serialization.Encoding.PEM,
            format=crypto_serialization.PrivateFormat.OpenSSH,
            encryption_algorithm=crypto_serialization.NoEncryption(),
        )

        with open(self.key_file, "wb") as f:
            f.write(private_bytes)

        # Ensure the private key has correct permissions on Linux/macOS
        self.key_file.chmod(0o600)

        # Load it back into the Paramiko Ed25519Key class
        return Ed25519Key.from_private_key_file(str(self.key_file))

    def connect(self) -> Tuple[bool, str]:
        """Establishes the SSH connection, preferring keys to passwords."""
        try:
            client = SSHClient()
            if self.load_system_keys:
                client.load_system_host_keys()
            if self.allow_auto_add:
                client.set_missing_host_key_policy(
                    paramiko.WarningPolicy()
                )  # nosec B507
            else:
                # Enforce RejectPolicy to prevent MitM in general operations
                client.set_missing_host_key_policy(paramiko.RejectPolicy())

            # Attempt key-based authentication first if a key exists
            if self.key_file.exists():
                try:
                    client.connect(
                        hostname=self.hostname,
                        username=self.username,
                        port=self.port,
                        key_filename=str(self.key_file),
                        timeout=10,
                        look_for_keys=False,
                        allow_agent=False,
                    )
                    self.client = client
                    return True, "Connection successful (via SSH Key)."
                except paramiko.AuthenticationException:
                    pass  # Fallback to password

            # Fallback to password-based authentication
            client.connect(
                hostname=self.hostname,
                username=self.username,
                password=self.password,
                port=self.port,
                timeout=10,
            )
            self.client = client
            return True, "Connection successful (via Password)."
        except Exception as e:
            self.client = None
            return False, str(e)

    def setup_ssh_key(self, log_callback: Callable[[str], None]) -> bool:
        """
        Deploys the local public key to the remote host to enable
        passwordless authentication.
        """
        log_callback(f"Securing {self.hostname} by deploying SSH keys...")
        key = self._get_or_create_key()
        public_key_str = f"{key.get_name()} {key.get_base64()}"

        commands = [
            "mkdir -p ~/.ssh",
            f'echo "{public_key_str}" >> ~/.ssh/authorized_keys',
            "chmod 700 ~/.ssh",
            "chmod 600 ~/.ssh/authorized_keys",
        ]

        for cmd in commands:
            exit_code, _ = self.execute_command(cmd, log_callback)
            if exit_code != 0:
                log_callback(f"FAILED to set up SSH key during: {cmd}")
                return False

        log_callback("SSH key successfully deployed.")
        return True

    def execute_command(
        self,
        command: str,
        log_callback: Callable[[str], None],
        *,
        check_exit_code: bool = True,
    ) -> Tuple[int, str]:
        """Executes a command on the remote host, streaming output."""
        if not self.client:
            log_callback("FATAL: SSH client not connected.\n")
            return -1, ""

        try:
            transport = self.client.get_transport()
            if not transport:
                log_callback("FATAL: SSH transport is not active.\n")
                return -1, ""

            channel = transport.open_session()
            channel.get_pty()  # Request a pseudo-terminal
            channel.exec_command(command)  # nosec B601

            stdout_parts = []
            while not channel.exit_status_ready():
                readq, _, _ = select.select([channel], [], [], 0.2)
                if readq:
                    if channel.recv_ready():
                        chunk = channel.recv(4096).decode("utf-8", "ignore")
                        stdout_parts.append(chunk)
                        log_callback(chunk)
                    if channel.recv_stderr_ready():
                        chunk = channel.recv_stderr(4096).decode("utf-8", "ignore")
                        stdout_parts.append(chunk)
                        log_callback(chunk)

            exit_code = channel.recv_exit_status()

            if check_exit_code and exit_code != 0:
                short_cmd = f"{command[:40]}..." if len(command) > 40 else command
                log_callback(
                    f"ERROR: Command '{short_cmd}' failed with code {exit_code}\n"
                )

            full_stdout = "".join(stdout_parts).strip()
            return exit_code, full_stdout

        except Exception as e:
            log_callback(f"FATAL STREAMING ERROR: {e}\n")
            return -1, ""

    def upload_content(
        self, content_bytes: bytes, remote_path: str
    ) -> Tuple[bool, str]:
        """Uploads byte content to a file on the remote host."""
        if not self.client:
            return False, "Client not connected."
        try:
            sftp = self.client.open_sftp()
            self.sftp = sftp
            with sftp.open(remote_path, "wb") as f:
                f.set_pipelined(True)
                f.write(content_bytes)
            return True, "File content uploaded successfully."
        except Exception as e:
            return False, str(e)
        finally:
            if self.sftp:
                self.sftp.close()

    def close(self) -> None:
        """Closes the SSH connection."""
        if self.sftp:
            self.sftp.close()
            self.sftp = None
        if self.client:
            self.client.close()
            self.client = None
