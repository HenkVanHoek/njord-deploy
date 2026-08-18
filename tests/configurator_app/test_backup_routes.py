# tests/configurator_app/test_backup_routes.py

import json
import unittest
from unittest.mock import patch

from src.configurator_app.app import create_app


class TestBackupRoutes(unittest.TestCase):

    def setUp(self):
        """Set up test client and patch SSHManager and BackupManager."""
        self.patcher_ssh = patch("src.configurator_app.app.SSHManager")
        self.patcher_backup = patch("src.configurator_app.app.BackupManager")

        self.mock_ssh_class = self.patcher_ssh.start()
        self.mock_backup_class = self.patcher_backup.start()

        self.mock_ssh = self.mock_ssh_class.return_value
        self.mock_backup = self.mock_backup_class.return_value

        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-key"})
        self.client = self.app.test_client()

    def tearDown(self):
        self.patcher_ssh.stop()
        self.patcher_backup.stop()

    def test_backup_inspect_success(self):
        """Verify successful target inspection via /api/backup/inspect."""
        self.mock_ssh.connect.return_value = (True, "Connected")
        self.mock_backup.inspect_target.return_value = {
            "status": "success",
            "managed_scope": "/opt/njorddeploy",
            "components": [{"id": "grafana", "total_size_bytes": 1000}],
        }

        response = self.client.post(
            "/api/backup/inspect",
            data=json.dumps(
                {
                    "ip": "192.168.1.100",
                    "username": "root",
                    "project_config_dir": "~/docker",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertEqual(len(data["components"]), 1)
        self.mock_backup.inspect_target.assert_called_with(
            self.mock_ssh, project_config_dir="~/docker"
        )

    def test_backup_inspect_missing_ip(self):
        """Verify 400 Bad Request when IP is missing."""
        response = self.client.post(
            "/api/backup/inspect",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_backup_inspect_ssh_fail(self):
        """Verify 400 when SSH connection fails."""
        self.mock_ssh.connect.return_value = (False, "Auth failure")
        response = self.client.post(
            "/api/backup/inspect",
            data=json.dumps({"ip": "192.168.1.100", "username": "root"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("Auth failure", data["error"])

    def test_backup_create_success(self):
        """Verify /api/backup/create triggers backup generation."""
        self.mock_ssh.connect.return_value = (True, "Connected")
        self.mock_backup.create_backup.return_value = {
            "status": "success",
            "filename": "njorddeploy_backup_20260818_120000.tar.gz",
            "size_human": "5.0 MB",
        }

        response = self.client.post(
            "/api/backup/create",
            data=json.dumps(
                {
                    "ip": "192.168.1.100",
                    "username": "root",
                    "selected_components": ["grafana"],
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")

    def test_backup_list_success(self):
        """Verify /api/backup/list returns list of backups."""
        self.mock_ssh.connect.return_value = (True, "Connected")
        self.mock_backup.list_backups.return_value = [
            {"filename": "njorddeploy_backup_20260818_120000.tar.gz", "size_bytes": 500}
        ]

        response = self.client.post(
            "/api/backup/list",
            data=json.dumps({"ip": "192.168.1.100", "username": "root"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertEqual(len(data["backups"]), 1)

    def test_backup_restore_success(self):
        """Verify /api/backup/restore executes restoration."""
        self.mock_ssh.connect.return_value = (True, "Connected")
        self.mock_backup.restore_backup.return_value = {
            "status": "success",
            "restored_archive": "njorddeploy_backup_20260818_120000.tar.gz",
        }

        response = self.client.post(
            "/api/backup/restore",
            data=json.dumps(
                {
                    "ip": "192.168.1.100",
                    "username": "root",
                    "backup_filename": "njorddeploy_backup_20260818_120000.tar.gz",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")

    def test_backup_restore_missing_filename(self):
        """Verify 400 when backup_filename is not provided."""
        response = self.client.post(
            "/api/backup/restore",
            data=json.dumps({"ip": "192.168.1.100", "username": "root"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_backup_download_invalid_filename(self):
        """Verify 400 rejection on path traversal / invalid filename."""
        response = self.client.get("/api/backup/download/invalid_file.txt")
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("Invalid backup filename", data["error"])

    def test_backup_discover_compose_success(self):
        """Verify /api/backup/discover-compose scans for stacks."""
        self.mock_ssh.connect.return_value = (True, "Connected")
        self.mock_backup.discover_compose_files.return_value = [
            {
                "directory": "/home/pi/docker",
                "compose_file": "/home/pi/docker/docker-compose.yml",
            }
        ]

        response = self.client.post(
            "/api/backup/discover-compose",
            data=json.dumps({"ip": "192.168.1.100", "username": "root"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["suggested_path"], "/home/pi/docker")
