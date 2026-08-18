# tests/managers/test_backup_manager.py

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from src.managers.backup_manager import DISCLAIMER_TEXT, BackupManager, _format_size


class TestBackupManager(unittest.TestCase):

    def setUp(self):
        """Set up BackupManager instance and mock SSHManager."""
        self.manager = BackupManager(project_config_dir="/opt/njorddeploy")
        self.mock_ssh = MagicMock()

    def test_format_size(self):
        """Verify human-readable byte conversion."""
        self.assertEqual(_format_size(0), "0 B")
        self.assertEqual(_format_size(512), "512.0 B")
        self.assertEqual(_format_size(1024), "1.0 KB")
        self.assertEqual(_format_size(1048576), "1.0 MB")
        self.assertEqual(_format_size(1073741824), "1.0 GB")

    def test_parse_compose_volumes_string_syntax(self):
        """Verify parsing of standard string-based volume declarations."""
        compose_yaml = """
services:
  grafana:
    image: grafana/grafana:latest
    volumes:
      - "/opt/grafana/data:/var/lib/grafana:rw"
      - "/etc/timezone:/etc/timezone:ro"
  uptime-kuma:
    image: louislam/uptime-kuma:latest
    volumes:
      - "/opt/uptime-kuma/data:/app/data"
        """
        parsed = self.manager.parse_compose_volumes(compose_yaml)
        self.assertIn("grafana", parsed)
        self.assertIn("uptime-kuma", parsed)

        grafana_vols = parsed["grafana"]
        self.assertEqual(len(grafana_vols), 2)
        # Unpacking-first mandate
        first_vol, second_vol, *_ = grafana_vols
        self.assertEqual(first_vol["host_path"], "/opt/grafana/data")
        self.assertEqual(first_vol["container_path"], "/var/lib/grafana")
        self.assertEqual(first_vol["mode"], "rw")
        self.assertEqual(first_vol["type"], "bind")

        self.assertEqual(second_vol["mode"], "ro")

    def test_parse_compose_volumes_dict_syntax(self):
        """Verify parsing of long-form dictionary volume declarations."""
        compose_yaml = """
services:
  db:
    image: mariadb:10.11
    volumes:
      - type: bind
        source: /opt/mariadb/data
        target: /var/lib/mysql
        read_only: false
        """
        parsed = self.manager.parse_compose_volumes(compose_yaml)
        self.assertIn("db", parsed)
        db_vols = parsed["db"]
        first_vol, *_ = db_vols
        self.assertEqual(first_vol["host_path"], "/opt/mariadb/data")
        self.assertEqual(first_vol["container_path"], "/var/lib/mysql")
        self.assertEqual(first_vol["mode"], "rw")

    def test_parse_compose_volumes_invalid(self):
        """Verify graceful fallback for invalid or empty YAML."""
        self.assertEqual(self.manager.parse_compose_volumes(""), {})
        self.assertEqual(self.manager.parse_compose_volumes("not: [valid: yaml"), {})
        self.assertEqual(self.manager.parse_compose_volumes("simple_string"), {})

    def test_inspect_target_success(self):
        """Verify target volume inspection and size calculation."""
        compose_yaml = """
services:
  grafana:
    volumes:
      - "/opt/grafana/data:/var/lib/grafana"
        """

        def mock_exec(cmd, log_cb, check_exit_code=True):
            if "compose" in cmd and "cat" in cmd:
                return 0, f"___COMPOSE_FOUND___\n{compose_yaml}\n___COMPOSE_END___\n"
            if "du -s" in cmd:
                return 0, "10485760\t/opt/grafana/data"  # 10 MB
            return 0, ""

        self.mock_ssh.execute_command.side_effect = mock_exec

        result = self.manager.inspect_target(self.mock_ssh)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["managed_scope"], "/opt/njorddeploy")
        self.assertEqual(result["disclaimer"], DISCLAIMER_TEXT)
        self.assertEqual(len(result["components"]), 1)

        first_comp, *_ = result["components"]
        self.assertEqual(first_comp["id"], "grafana")
        self.assertEqual(first_comp["total_size_bytes"], 10485760)
        self.assertEqual(first_comp["total_size_human"], "10.0 MB")
        self.assertFalse(first_comp["is_heavy"])

    def test_inspect_target_missing_compose(self):
        """Verify error report when no docker-compose.yml is found on host."""
        self.mock_ssh.execute_command.return_value = (0, "__END__")
        result = self.manager.inspect_target(self.mock_ssh)
        self.assertEqual(result["status"], "error")
        self.assertIn("No docker-compose.yml or compose.yaml found", result["message"])

    def test_create_backup_success(self):
        """Verify end-to-end backup creation workflow."""
        compose_yaml = """
services:
  grafana:
    volumes:
      - "/opt/grafana/data:/var/lib/grafana"
        """

        def mock_exec(cmd, log_cb, check_exit_code=True):
            if "compose" in cmd and "cat" in cmd:
                return 0, f"___COMPOSE_FOUND___\n{compose_yaml}\n___COMPOSE_END___\n"
            if "du -s" in cmd:
                return 0, "5242880\t/opt/grafana/data"
            if "sha256sum" in cmd:
                return 0, "abcdef1234567890\n5242880"
            return 0, ""

        self.mock_ssh.execute_command.side_effect = mock_exec

        logs = []
        result = self.manager.create_backup(
            self.mock_ssh,
            selected_components=["grafana"],
            log_callback=logs.append,
        )

        self.assertEqual(result["status"], "success")
        self.assertIn("njorddeploy_backup_", result["filename"])
        self.assertEqual(result["sha256"], "abcdef1234567890")
        self.assertEqual(result["size_bytes"], 5242880)
        self.assertIn("grafana", result["components"])
        self.assertTrue(any("Initiating NjordDeploy Backup" in ln for ln in logs))

    def test_create_backup_with_pause(self):
        """Verify container pause and unpause calls when pause_containers is True."""
        compose_yaml = """
services:
  grafana:
    volumes:
      - "/opt/grafana/data:/var/lib/grafana"
        """
        executed_cmds = []

        def mock_exec(cmd, log_cb, check_exit_code=True):
            executed_cmds.append(cmd)
            if "compose" in cmd and "cat" in cmd:
                return 0, f"___COMPOSE_FOUND___\n{compose_yaml}\n___COMPOSE_END___\n"
            if "sha256sum" in cmd:
                return 0, "hash123\n1000"
            return 0, ""

        self.mock_ssh.execute_command.side_effect = mock_exec

        result = self.manager.create_backup(
            self.mock_ssh,
            selected_components=["grafana"],
            pause_containers=True,
        )
        self.assertEqual(result["status"], "success")
        self.assertTrue(any("docker compose pause grafana" in c for c in executed_cmds))
        self.assertTrue(
            any("docker compose unpause grafana" in c for c in executed_cmds)
        )

    def test_list_backups(self):
        """Verify parsing and sorting of backup list from remote host."""
        mock_output = (
            "/opt/njorddeploy/backups/"
            "njorddeploy_backup_20260818_080000.tar.gz|5000000|1787040000\n"
            "/opt/njorddeploy/backups/"
            "njorddeploy_backup_20260818_100000.tar.gz|6000000|1787047200\n"
        )
        self.mock_ssh.execute_command.return_value = (0, mock_output)

        backups = self.manager.list_backups(self.mock_ssh)
        self.assertEqual(len(backups), 2)
        # Should be sorted newest first
        first_bk, second_bk, *_ = backups
        self.assertEqual(
            first_bk["filename"], "njorddeploy_backup_20260818_100000.tar.gz"
        )
        self.assertEqual(first_bk["size_bytes"], 6000000)
        self.assertEqual(
            second_bk["filename"], "njorddeploy_backup_20260818_080000.tar.gz"
        )

    def test_restore_backup_success(self):
        """Verify successful restore workflow with permissions and stack restart."""
        executed_cmds = []

        def mock_exec(cmd, log_cb, check_exit_code=True):
            executed_cmds.append(cmd)
            if "tar -tzf" in cmd:
                return 0, "VALID\n"
            if "manifest.json" in cmd:
                return 0, json.dumps({"components": ["grafana", "uptime-kuma"]})
            return 0, ""

        self.mock_ssh.execute_command.side_effect = mock_exec

        logs = []
        result = self.manager.restore_backup(
            self.mock_ssh,
            "njorddeploy_backup_20260818_120000.tar.gz",
            restart_after=True,
            log_callback=logs.append,
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(
            result["restored_archive"], "njorddeploy_backup_20260818_120000.tar.gz"
        )
        self.assertTrue(result["restarted"])
        self.assertTrue(any("docker compose stop" in c for c in executed_cmds))
        self.assertTrue(any("tar -xzf" in c for c in executed_cmds))
        self.assertTrue(any("docker compose up -d" in c for c in executed_cmds))

    def test_restore_backup_invalid_filename(self):
        """Verify rejection of malicious path traversal in restore filename."""
        result = self.manager.restore_backup(
            self.mock_ssh,
            "../../etc/shadow",
        )
        self.assertEqual(result["status"], "error")
        self.assertIn("Invalid backup filename", result["message"])

    def test_restore_backup_missing_archive(self):
        """Verify error handling when archive is missing on target host."""
        self.mock_ssh.execute_command.return_value = (0, "MISSING\n")
        result = self.manager.restore_backup(
            self.mock_ssh,
            "njorddeploy_backup_20260818_999999.tar.gz",
        )
        self.assertEqual(result["status"], "error")
        self.assertIn("not found", result["message"])

    def test_download_backup_sftp(self):
        """Verify SFTP download delegation."""
        mock_client = MagicMock()
        mock_sftp = MagicMock()
        mock_client.open_sftp.return_value = mock_sftp
        self.mock_ssh.client = mock_client

        dest_dir = Path("/tmp/njord_test_backups")  # nosec B108
        success, msg, local_file = self.manager.download_backup_sftp(
            self.mock_ssh,
            "njorddeploy_backup_20260818_120000.tar.gz",
            dest_dir,
        )

        self.assertTrue(success)
        mock_sftp.get.assert_called_once()
        self.assertEqual(local_file.name, "njorddeploy_backup_20260818_120000.tar.gz")

    def test_resolve_project_dir_auto_detect(self):
        """Verify remote directory resolution and candidate detection."""
        self.mock_ssh.execute_command.return_value = (0, "/home/pi/docker\n")
        resolved = self.manager.resolve_project_dir(self.mock_ssh, "~/docker")
        self.assertEqual(resolved, "/home/pi/docker")

    def test_inspect_target_custom_directory(self):
        """Verify inspecting a custom compose path."""
        compose_yaml = """
services:
  custom-app:
    volumes:
      - "/home/pi/docker/data:/app/data"
        """

        def mock_exec(cmd, log_cb, check_exit_code=True):
            if "expanded" in cmd or "for d in" in cmd:
                return 0, "/home/pi/docker\n"
            if "compose" in cmd and "cat" in cmd:
                return 0, f"___COMPOSE_FOUND___\n{compose_yaml}\n___COMPOSE_END___\n"
            if "du -s" in cmd:
                return 0, "2048\t/home/pi/docker/data"
            return 0, ""

        self.mock_ssh.execute_command.side_effect = mock_exec

        result = self.manager.inspect_target(
            self.mock_ssh, project_config_dir="/home/pi/docker"
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["managed_scope"], "/home/pi/docker")
        self.assertEqual(len(result["components"]), 1)
        first_comp, *_ = result["components"]
        self.assertEqual(first_comp["id"], "custom-app")

    def test_discover_compose_files(self):
        """Verify discovering compose files across target filesystem."""
        mock_find_output = (
            "/home/pi/docker/docker-compose.yml\n" "/opt/njorddeploy/compose.yaml\n"
        )
        self.mock_ssh.execute_command.return_value = (0, mock_find_output)
        discovered = self.manager.discover_compose_files(self.mock_ssh)
        self.assertEqual(len(discovered), 2)
        first_d, second_d, *_ = discovered
        self.assertEqual(first_d["directory"], "/opt/njorddeploy")
        self.assertEqual(second_d["directory"], "/home/pi/docker")
