# tests/cli/test_runner.py
"""Unit tests for NjordDeploy Headless CLI runner."""

import unittest
from unittest.mock import MagicMock, patch

from cli.runner import NjordCliRunner, main, parse_cli_args


class TestNjordCliRunner(unittest.TestCase):
    """Test suite for NjordCliRunner functionality."""

    @patch("cli.runner.seed_user_components_if_needed")
    @patch("cli.runner.get_components_paths")
    @patch("cli.runner.ComponentManager")
    @patch("cli.runner.SetupManager")
    @patch("cli.runner.DeploymentManager")
    def setUp(
        self,
        mock_dep_mgr_cls,
        mock_setup_mgr_cls,
        mock_comp_mgr_cls,
        mock_paths,
        mock_seed,
    ):
        mock_paths.return_value = ("/fake/meta.json", "/fake/templates")
        self.mock_comp_mgr = MagicMock()
        self.mock_setup_mgr = MagicMock()
        self.mock_setup_mgr.output_dir = "/fake/output"
        self.mock_dep_mgr = MagicMock()

        mock_comp_mgr_cls.return_value = self.mock_comp_mgr
        mock_setup_mgr_cls.return_value = self.mock_setup_mgr
        mock_dep_mgr_cls.return_value = self.mock_dep_mgr

        self.runner = NjordCliRunner()

    def test_example_config_output(self):
        """Verify structure of sample example configuration."""
        sample = self.runner.get_example_config()
        self.assertIn("target", sample)
        self.assertIn("components", sample)
        self.assertIn("env_vars", sample)
        self.assertIsInstance(sample["components"], list)

    def test_parse_cli_args_deploy(self):
        """Verify parsing of deployment CLI flags."""
        args = parse_cli_args(
            [
                "--deploy",
                "deploy_spec.json",
                "--ip",
                "192.168.1.100",
                "--components",
                "uptime-kuma,homarr",
            ]
        )
        self.assertEqual(args.deploy, "deploy_spec.json")
        self.assertEqual(args.ip, "192.168.1.100")
        self.assertEqual(args.components, "uptime-kuma,homarr")

    def test_parse_cli_args_backup_restore(self):
        """Verify parsing of backup & restore CLI flags."""
        args_b = parse_cli_args(["--backup", "--ip", "10.0.0.5", "--pause-containers"])
        self.assertTrue(args_b.backup)
        self.assertEqual(args_b.ip, "10.0.0.5")
        self.assertTrue(args_b.pause_containers)

        args_r = parse_cli_args(
            ["--restore", "njorddeploy_backup_123.tar.gz", "--ip", "10.0.0.5"]
        )
        self.assertEqual(args_r.restore, "njorddeploy_backup_123.tar.gz")
        self.assertEqual(args_r.ip, "10.0.0.5")

    def test_deploy_missing_target(self):
        """Verify failure when no target device is configured."""
        config = {"components": ["uptime-kuma"]}
        result = self.runner.deploy(config)
        self.assertFalse(result)

    def test_deploy_missing_components(self):
        """Verify failure when no components are selected."""
        config = {"target": {"ip": "192.168.1.50"}}
        result = self.runner.deploy(config)
        self.assertFalse(result)

    def test_deploy_unknown_components(self):
        """Verify rejection of unknown component IDs."""
        self.mock_comp_mgr.get_all_components.return_value = [
            {"id": "uptime-kuma"},
            {"id": "homarr"},
        ]
        config = {
            "target": {"ip": "192.168.1.50"},
            "components": ["uptime-kuma", "nonexistent-service"],
        }
        result = self.runner.deploy(config)
        self.assertFalse(result)

    def test_deploy_success(self):
        """Verify successful headless deployment execution."""
        self.mock_comp_mgr.get_all_components.return_value = [
            {"id": "uptime-kuma", "name": "Uptime Kuma"},
            {"id": "homarr", "name": "Homarr"},
        ]
        self.mock_setup_mgr.prepare_deployment_package.return_value = (True, [])

        def mock_start(task_id, tasks, *args, **kwargs):
            tasks[task_id]["status"] = "completed"
            tasks[task_id]["logs"].append("Deployment finished successfully.")

        self.mock_dep_mgr.start_deployment.side_effect = mock_start

        config = {
            "target": {"ip": "192.168.1.50", "username": "root"},
            "components": ["uptime-kuma", "homarr"],
            "env_vars": {"GLOBAL_DOMAIN": "local.domain"},
        }
        result = self.runner.deploy(config, stream_logs=False)
        self.assertTrue(result)
        self.mock_setup_mgr.prepare_deployment_package.assert_called_once()
        self.mock_comp_mgr.generate_deployment_artifacts.assert_called_once()

    @patch("cli.runner.SSHManager")
    @patch("cli.runner.BackupManager")
    def test_inspect_stack(self, mock_bk_cls, mock_ssh_cls):
        """Verify stack inspection CLI integration."""
        mock_ssh = MagicMock()
        mock_ssh.connect.return_value = (True, "Connected")
        mock_ssh_cls.return_value = mock_ssh

        mock_bk = MagicMock()
        mock_bk.inspect_target.return_value = {
            "status": "success",
            "components": [{"id": "uptime-kuma"}],
        }
        mock_bk_cls.return_value = mock_bk

        res = self.runner.inspect_stack(ip="10.0.0.1", username="root")
        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["components"]), 1)

    @patch("cli.runner.SSHManager")
    @patch("cli.runner.BackupManager")
    def test_backup_cli(self, mock_bk_cls, mock_ssh_cls):
        """Verify backup creation CLI integration."""
        mock_ssh = MagicMock()
        mock_ssh.connect.return_value = (True, "Connected")
        mock_ssh_cls.return_value = mock_ssh

        mock_bk = MagicMock()
        mock_bk.create_backup.return_value = {
            "status": "success",
            "filename": "backup.tar.gz",
        }
        mock_bk_cls.return_value = mock_bk

        res = self.runner.backup(ip="10.0.0.1", components=["uptime-kuma"])
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["filename"], "backup.tar.gz")

    @patch("cli.runner.SSHManager")
    @patch("cli.runner.BackupManager")
    def test_restore_cli(self, mock_bk_cls, mock_ssh_cls):
        """Verify restore CLI integration."""
        mock_ssh = MagicMock()
        mock_ssh.connect.return_value = (True, "Connected")
        mock_ssh_cls.return_value = mock_ssh

        mock_bk = MagicMock()
        mock_bk.restore_backup.return_value = {
            "status": "success",
            "message": "Restored",
        }
        mock_bk_cls.return_value = mock_bk

        res = self.runner.restore(ip="10.0.0.1", backup_filename="backup.tar.gz")
        self.assertEqual(res["status"], "success")

    @patch("cli.runner.NjordCliRunner")
    def test_main_example_config(self, mock_runner_cls):
        """Verify main router handles --example-config."""
        mock_runner = MagicMock()
        mock_runner.get_example_config.return_value = {"sample": "test"}
        mock_runner_cls.return_value = mock_runner

        code = main(["--example-config"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
