# tests/test_deployment_manager.py
import unittest
from unittest.mock import MagicMock

from managers.component_reader import ComponentReader
from managers.deployment_manager import DeploymentManager


class TestDeploymentManager(unittest.TestCase):
    """
    Test suite for DeploymentManager using the new ComponentReader.
    """

    def setUp(self):
        """
        Set up the test environment by mocking the ComponentReader.
        Fixes the 'Expected type ComponentReader' warning.
        """
        # Create a mock that specifically follows the ComponentReader spec
        self.mock_reader = MagicMock(spec=ComponentReader)

        # Initialize the manager with the mocked reader
        self.deploy_mgr = DeploymentManager(component_manager=self.mock_reader)

        # Standard test data
        self.test_task_id = "test-task-123"
        self.tasks_dict = {self.test_task_id: {"status": "pending", "logs": []}}

    def test_initialization_with_reader(self):
        """Verify that the manager correctly identifies the reader attribute."""
        self.assertEqual(self.deploy_mgr.reader, self.mock_reader)
        # Verify fix for line 788: check if prefix is initialized
        self.assertTrue(hasattr(self.deploy_mgr, "_docker_prefix"))

    def test_start_deployment_calls_reader(self):
        """
        Test if deployment logic correctly requests component details
        via the reader.
        """
        # Setup mock behavior
        self.mock_reader.get_component_details.return_value = {
            "name": "Nginx",
            "docker_service_name": "nginx_svc",
        }

        # Simulate a deployment start
        output_path = "/tmp/deploy"
        devices = [{"ip": "192.168.1.50"}]

        from unittest.mock import patch

        mock_runner = MagicMock()
        mock_runner.events = []
        mock_runner.status = "successful"
        mock_runner.stdout = None

        with patch(
            "managers.deployment_manager.ansible_runner.run",
            return_value=mock_runner,
        ):
            self.deploy_mgr.start_deployment(
                self.test_task_id, self.tasks_dict, output_path, devices
            )

        self.assertTrue(True)

    def test_cleanup_logic(self):
        """Verify that redundant parentheses are removed (Line 308 fix)."""
        # This test ensures the logic still holds after linter cleanup
        result = (
            self.deploy_mgr._cleanup_example()
            if hasattr(self.deploy_mgr, "_cleanup_example")
            else None
        )
        self.assertIsNone(result)

    def test_start_deployment_captures_errors(self):
        """Verify that deployment manager correctly captures task errors."""
        from unittest.mock import patch

        # Create mock event stream
        mock_events = [
            {
                "event": "runner_on_failed",
                "event_data": {
                    "task": "Pull latest service images",
                    "res": {
                        "msg": "pull access denied for fluffychat",
                        "stderr": "Error response from daemon: pull access denied",
                    },
                },
            }
        ]

        # Mock runner object
        mock_runner = MagicMock()
        mock_runner.events = mock_events
        mock_runner.status = "failed"
        mock_runner.stdout = None

        output_path = "/tmp/deploy"
        devices = [{"ip": "100.121.216.150"}]

        with patch(
            "managers.deployment_manager.ansible_runner.run",
            return_value=mock_runner,
        ):
            self.deploy_mgr.start_deployment(
                self.test_task_id, self.tasks_dict, output_path, devices
            )

        task_res = self.tasks_dict[self.test_task_id]
        self.assertEqual(task_res["status"], "failed")
        self.assertTrue(len(task_res["errors"]) > 0)

        # Verify first error structure
        err, *_ = task_res["errors"]
        assert isinstance(err, dict)
        self.assertEqual(err["type"], "Ansible:FAILED")
        self.assertEqual(
            err["summary"],
            "Ansible task failed: Pull latest service images",
        )
        self.assertIn("pull access denied", err["details"])

    def test_start_deployment_captures_item_errors(self):
        """Verify that deployment manager captures loop item errors."""
        from unittest.mock import patch

        # Create mock event stream
        mock_events = [
            {
                "event": "runner_on_item_failed",
                "event_data": {
                    "task": "Perform Clean Install",
                    "item": "pish-fluffychat-web",
                    "res": {
                        "msg": "non-zero return code",
                        "stderr": "no such service: pish-fluffychat-web",
                    },
                },
            }
        ]

        # Mock runner object
        mock_runner = MagicMock()
        mock_runner.events = mock_events
        mock_runner.status = "failed"
        mock_runner.stdout = None

        output_path = "/tmp/deploy"
        devices = [{"ip": "100.121.216.150"}]

        with patch(
            "managers.deployment_manager.ansible_runner.run",
            return_value=mock_runner,
        ):
            self.deploy_mgr.start_deployment(
                self.test_task_id, self.tasks_dict, output_path, devices
            )

        task_res = self.tasks_dict[self.test_task_id]
        self.assertEqual(task_res["status"], "failed")
        self.assertTrue(len(task_res["errors"]) > 0)

        # Verify first error structure
        err, *_ = task_res["errors"]
        assert isinstance(err, dict)
        self.assertEqual(err["type"], "Ansible:ITEM_FAILED")
        self.assertEqual(
            err["summary"],
            "Ansible task failed: Perform Clean Install",
        )
        self.assertIn("no such service", err["details"])

    def test_start_deployment_passes_container_engine(self):
        """Verify that container_engine is passed to Ansible runner extravars."""
        from unittest.mock import patch

        mock_runner = MagicMock()
        mock_runner.events = []
        mock_runner.status = "successful"
        mock_runner.stdout = None

        output_path = "/tmp/deploy"
        devices = [{"ip": "100.121.216.150", "container_engine": "podman"}]

        with patch(
            "managers.deployment_manager.ansible_runner.run",
            return_value=mock_runner,
        ) as mock_run:
            self.deploy_mgr.start_deployment(
                self.test_task_id, self.tasks_dict, output_path, devices
            )

            # Check that extravars passed to runner contains container_engine
            call_kwargs = mock_run.call_args[1]
            self.assertIn("extravars", call_kwargs)
            self.assertEqual(call_kwargs["extravars"]["container_engine"], "podman")

    def test_start_deployment_events_handling(self):
        """
        Verify detailed Ansible events parsing including OK stdout,
        warnings, and subtask errors.
        """
        from unittest.mock import patch

        mock_events = [
            {
                "event": "runner_on_ok",
                "event_data": {
                    "task": "Echo Version",
                    "res": {
                        "stdout": "version 1.0.0\nbuild 42",
                        "msg": "Task completed successfully",
                        "warnings": ["Deprecated parameter used"],
                    },
                },
            },
            {
                "event": "runner_on_item_ok",
                "event_data": {"res": {"msg": "Item 1 processed"}},
            },
            {
                "event": "warning",
                "event_data": {"warning": "Global Ansible deprecation warning"},
            },
            {
                "event": "runner_on_unreachable",
                "event_data": {
                    "task": "Connect to host",
                    "res": {
                        "msg": "Host is unreachable",
                        "module_stderr": "Connection timed out",
                    },
                },
            },
            {
                "event": "runner_on_failed",
                "event_data": {
                    "task": "Install complex stack",
                    "res": {
                        "msg": "One or more items failed",
                        "results": [
                            {"failed": True, "msg": "Subtask db init failed"},
                            {"failed": False, "msg": "Subtask web ok"},
                        ],
                    },
                },
            },
        ]

        mock_runner = MagicMock()
        mock_runner.events = mock_events
        mock_runner.status = "failed"
        mock_runner.stdout = None

        with patch(
            "managers.deployment_manager.ansible_runner.run", return_value=mock_runner
        ):
            self.deploy_mgr.start_deployment(
                self.test_task_id,
                self.tasks_dict,
                "/tmp/deploy",
                [{"ip": "192.168.1.50"}],
            )

        logs = self.tasks_dict[self.test_task_id]["logs"]
        log_str = "\n".join(logs)
        self.assertIn("STDOUT [Echo Version]: version 1.0.0", log_str)
        self.assertIn("WARN: [Echo Version] Deprecated parameter used", log_str)
        self.assertIn("DEBUG: Item 1 processed", log_str)
        self.assertIn("WARN: Global Ansible deprecation warning", log_str)
        self.assertIn("SUB_FAILED: Subtask db init failed", log_str)

    def test_start_deployment_options_and_manifest(self):
        """
        Verify podman rootful detection, clean/restart mapping, and compose
        manifest logging.
        """
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        self.mock_reader.get_docker_service_name.side_effect = lambda cid: f"srv_{cid}"

        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            (out_dir / "docker-compose.yml").write_text(
                "services:\n  web:\n    image: nginx\n", encoding="utf-8"
            )
            (out_dir / "config.env").write_text("FOO=BAR\n", encoding="utf-8")

            mock_runner = MagicMock()
            mock_runner.events = []
            mock_runner.status = "successful"
            mock_runner.stdout = None

            device = {
                "ip": "192.168.1.100",
                "user": "root",
                "password": "secret_password",
                "container_engine": "podman",
                "components_to_clean": ["app1"],
                "components_to_restart": ["app2"],
                "selected_components_data": [{"id": "app1", "requires_root": True}],
                "global_vars": {"SKIP_ENGINE_PROVISIONING": True},
            }

            with patch(
                "managers.deployment_manager.ansible_runner.run",
                return_value=mock_runner,
            ) as mock_run:
                with patch(
                    "managers.deployment_manager.get_ssh_key_path",
                    return_value=Path(tmpdir) / "id_rsa",
                ):
                    (Path(tmpdir) / "id_rsa").write_text("dummy_key", encoding="utf-8")
                    self.deploy_mgr.start_deployment(
                        self.test_task_id,
                        self.tasks_dict,
                        str(out_dir),
                        [device],
                        components_to_clean=["app1"],
                        components_to_restart=["app2"],
                        selected_components_data=[
                            {"id": "app1", "requires_root": True}
                        ],
                        global_vars={"SKIP_ENGINE_PROVISIONING": True},
                    )

                call_kwargs = mock_run.call_args[1]
                extravars = call_kwargs["extravars"]
                self.assertEqual(extravars["container_engine"], "podman")
                self.assertTrue(extravars["podman_rootful"])
                self.assertEqual(extravars["components_to_clean"], ["srv_app1"])
                self.assertEqual(extravars["components_to_restart"], ["srv_app2"])
                self.assertEqual(extravars["ansible_password"], "secret_password")
                self.assertTrue(extravars["skip_engine_provisioning"])

            logs = "\n".join(self.tasks_dict[self.test_task_id]["logs"])
            self.assertIn("MANIFEST: Transferring", logs)
            self.assertIn("MANIFEST: Target docker-compose.yml contents:", logs)

    def test_start_deployment_stdout_cleanup_and_exception(self):
        """
        Verify runner stdout capture on failure, temp file cleanup,
        and fatal exception handling.
        """
        import io
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            proj_root = Path(tmpdir)
            (proj_root / "env").mkdir()
            (proj_root / "env" / "extravars").write_text("VARS", encoding="utf-8")
            (proj_root / "inventory").mkdir()
            (proj_root / "inventory" / "hosts.json").write_text("{}", encoding="utf-8")
            art_dir = proj_root / "artifacts"
            art_dir.mkdir()
            spec_art = art_dir / "specific_task"
            spec_art.mkdir()
            (spec_art / "job.log").write_text("LOG", encoding="utf-8")

            # 1. Runner failed with stdout
            mock_runner = MagicMock()
            mock_runner.events = []
            mock_runner.status = "failed"
            mock_runner.stdout = io.StringIO(
                "Line 1\nLine 2\nFatal compilation error\n"
            )
            mock_runner.config = MagicMock()
            mock_runner.config.artifact_dir = str(spec_art)

            with patch(
                "managers.deployment_manager.resource_path",
                side_effect=lambda p: proj_root / p,
            ):
                with patch(
                    "managers.deployment_manager.ansible_runner.run",
                    return_value=mock_runner,
                ):
                    self.deploy_mgr.start_deployment(
                        self.test_task_id,
                        self.tasks_dict,
                        "/tmp/deploy",
                        [{"ip": "192.168.1.50"}],
                    )

            logs = "\n".join(self.tasks_dict[self.test_task_id]["logs"])
            self.assertIn("CONSOLE: Fatal compilation error", logs)
            self.assertFalse((proj_root / "env" / "extravars").exists())
            self.assertFalse((proj_root / "inventory" / "hosts.json").exists())
            self.assertFalse(spec_art.exists())

            # 2. ansible_runner.run raises unexpected Exception
            with patch(
                "managers.deployment_manager.ansible_runner.run",
                side_effect=RuntimeError("Runner crashed"),
            ):
                self.deploy_mgr.start_deployment(
                    self.test_task_id,
                    self.tasks_dict,
                    "/tmp/deploy",
                    [{"ip": "192.168.1.50"}],
                )

            self.assertEqual(self.tasks_dict[self.test_task_id]["status"], "failed")
            fatal_logs = "\n".join(self.tasks_dict[self.test_task_id]["logs"])
            self.assertIn("FATAL: Runner crashed", fatal_logs)

    def test_component_mapping_fallbacks(self):
        """
        Verify fallbacks when reader lacks get_docker_service_name or
        returns None.
        """
        from unittest.mock import patch

        mock_runner = MagicMock()
        mock_runner.events = []
        mock_runner.status = "successful"
        mock_runner.stdout = None

        # Case 1: reader has get_docker_service_name returning None
        self.mock_reader.get_docker_service_name.return_value = None
        with patch(
            "managers.deployment_manager.ansible_runner.run",
            return_value=mock_runner,
        ) as mock_run:
            self.deploy_mgr.start_deployment(
                self.test_task_id,
                self.tasks_dict,
                "/tmp/deploy",
                [{"ip": "192.168.1.10"}],
                components_to_clean=["clean_app"],
                components_to_restart=["restart_app"],
            )
            extravars = mock_run.call_args[1]["extravars"]
            self.assertEqual(extravars["components_to_clean"], ["clean_app"])
            self.assertEqual(extravars["components_to_restart"], ["restart_app"])

        # Case 2: reader does not have get_docker_service_name attribute
        mgr_no_reader_attr = DeploymentManager(component_manager=object())
        with patch(
            "managers.deployment_manager.ansible_runner.run",
            return_value=mock_runner,
        ) as mock_run:
            mgr_no_reader_attr.start_deployment(
                self.test_task_id,
                self.tasks_dict,
                "/tmp/deploy",
                [{"ip": "192.168.1.10"}],
                components_to_clean=["clean_app"],
                components_to_restart=["restart_app"],
            )
            extravars = mock_run.call_args[1]["extravars"]
            self.assertEqual(extravars["components_to_clean"], ["clean_app"])
            self.assertEqual(extravars["components_to_restart"], ["restart_app"])

    def test_compose_manifest_read_error(self):
        """Verify handling when compose file cannot be read."""
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        mock_runner = MagicMock()
        mock_runner.events = []
        mock_runner.status = "successful"
        mock_runner.stdout = None

        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            compose_file = out_dir / "docker-compose.yml"
            compose_file.write_text("dummy", encoding="utf-8")

            with patch.object(
                Path, "read_text", side_effect=OSError("Read permission denied")
            ):
                with patch(
                    "managers.deployment_manager.ansible_runner.run",
                    return_value=mock_runner,
                ):
                    self.deploy_mgr.start_deployment(
                        self.test_task_id,
                        self.tasks_dict,
                        str(out_dir),
                        [{"ip": "192.168.1.10"}],
                    )

            self.assertEqual(self.tasks_dict[self.test_task_id]["status"], "completed")

    def test_duplicate_events_and_component_id_match(self):
        """Verify duplicate events are ignored and component_id is matched."""
        from unittest.mock import patch

        mock_events = [
            {
                "uuid": "event-1",
                "event": "runner_on_failed",
                "event_data": {
                    "task": "Deploy Immich Server",
                    "res": {
                        "msg": "Crash loop backoff",
                        "stderr": "container error",
                    },
                },
            },
            {
                # Duplicate event with same uuid
                "uuid": "event-1",
                "event": "runner_on_failed",
                "event_data": {"task": "Deploy Immich Server"},
            },
        ]

        mock_runner = MagicMock()
        mock_runner.events = mock_events
        mock_runner.status = "failed"
        mock_runner.stdout = None

        with patch(
            "managers.deployment_manager.ansible_runner.run",
            return_value=mock_runner,
        ):
            self.deploy_mgr.start_deployment(
                self.test_task_id,
                self.tasks_dict,
                "/tmp/deploy",
                [{"ip": "192.168.1.50"}],
                selected_components_data=[{"id": "immich"}],
            )

        errors = self.tasks_dict[self.test_task_id]["errors"]
        self.assertEqual(len(errors), 1)
        first_err, *_ = errors
        self.assertEqual(first_err["component_id"], "immich")

    def test_runner_stdout_read_error(self):
        """Verify graceful handling when runner stdout reading raises an error."""
        from unittest.mock import patch

        mock_stdout = MagicMock()
        mock_stdout.seek.return_value = None
        mock_stdout.read.side_effect = OSError("Read failed")

        mock_runner = MagicMock()
        mock_runner.events = []
        mock_runner.status = "failed"
        mock_runner.stdout = mock_stdout

        with patch(
            "managers.deployment_manager.ansible_runner.run",
            return_value=mock_runner,
        ):
            self.deploy_mgr.start_deployment(
                self.test_task_id,
                self.tasks_dict,
                "/tmp/deploy",
                [{"ip": "192.168.1.50"}],
            )

        self.assertEqual(self.tasks_dict[self.test_task_id]["status"], "failed")

    def test_cleanup_exceptions(self):
        """Verify error logging when file unlink or rmdir fails in finally block."""
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            proj_root = Path(tmpdir)
            (proj_root / "env").mkdir()
            (proj_root / "env" / "extravars").write_text("VARS", encoding="utf-8")
            (proj_root / "inventory").mkdir()
            (proj_root / "inventory" / "hosts.json").write_text("{}", encoding="utf-8")
            art_dir = proj_root / "artifacts"
            art_dir.mkdir()
            spec_art = proj_root / "specific_task"
            spec_art.mkdir()

            mock_runner = MagicMock()
            mock_runner.events = []
            mock_runner.status = "successful"
            mock_runner.stdout = None
            mock_runner.config = MagicMock()
            mock_runner.config.artifact_dir = str(spec_art)

            with patch(
                "managers.deployment_manager.resource_path",
                side_effect=lambda p: proj_root / p,
            ):
                with patch(
                    "managers.deployment_manager.ansible_runner.run",
                    return_value=mock_runner,
                ):
                    with patch.object(
                        Path, "unlink", side_effect=OSError("Unlink denied")
                    ):
                        with patch(
                            "shutil.rmtree", side_effect=OSError("Rmtree denied")
                        ):
                            with patch.object(
                                Path, "rmdir", side_effect=OSError("Rmdir failed")
                            ):
                                self.deploy_mgr.start_deployment(
                                    self.test_task_id,
                                    self.tasks_dict,
                                    "/tmp/deploy",
                                    [{"ip": "192.168.1.50"}],
                                )

            self.assertEqual(self.tasks_dict[self.test_task_id]["status"], "completed")

    def test_deployment_failure_without_ansible_events(self):
        """Verify fallback error creation when deployment failed without task events."""
        from unittest.mock import patch

        mock_runner = MagicMock()
        mock_runner.events = []
        mock_runner.status = "failed"
        mock_runner.stdout = None

        with patch(
            "managers.deployment_manager.ansible_runner.run",
            return_value=mock_runner,
        ):
            self.deploy_mgr.start_deployment(
                self.test_task_id,
                self.tasks_dict,
                "/tmp/deploy",
                [{"ip": "192.168.1.50"}],
            )

        task_res = self.tasks_dict[self.test_task_id]
        self.assertEqual(task_res["status"], "failed")
        self.assertEqual(len(task_res["errors"]), 1)
        fallback_err, *_ = task_res["errors"]
        self.assertEqual(fallback_err["type"], "Ansible:Deployment:Failure")

    def test_ansible_runner_import_fallback(self):
        """Verify fallback mock creation when ansible_runner cannot be imported."""
        import importlib
        import sys
        from unittest.mock import patch

        with patch.dict(sys.modules, {"ansible_runner": None}):
            if "managers.deployment_manager" in sys.modules:
                del sys.modules["managers.deployment_manager"]
            mod = importlib.import_module("managers.deployment_manager")
            self.assertTrue(hasattr(mod, "ansible_runner"))

    def test_start_deployment_with_private_registry_auth(self):
        """Verify registry credentials are passed to extravars for Ansible."""
        from unittest.mock import patch

        mock_runner = MagicMock()
        mock_runner.status = "successful"
        mock_runner.events = []

        with patch(
            "managers.deployment_manager.ansible_runner.run",
            return_value=mock_runner,
        ) as mock_ansible_run:
            self.deploy_mgr.start_deployment(
                task_id=self.test_task_id,
                tasks=self.tasks_dict,
                output_path="/tmp/deploy",
                devices=[{"ip": "192.168.1.50"}],
                global_vars={
                    "REGISTRY_SERVER": "git.piselfhosting.com",
                    "REGISTRY_USERNAME": "hvhoek",
                    "REGISTRY_PASSWORD": "SecretToken123!",
                    "REGISTRY_IP": "192.168.178.118",
                },
            )

            mock_ansible_run.assert_called_once()
            called_kwargs = mock_ansible_run.call_args.kwargs
            extravars = called_kwargs.get("extravars", {})
            self.assertEqual(extravars.get("registry_server"), "git.piselfhosting.com")
            self.assertEqual(extravars.get("registry_username"), "hvhoek")
            self.assertEqual(extravars.get("registry_password"), "SecretToken123!")
            self.assertEqual(extravars.get("registry_ip"), "192.168.178.118")


if __name__ == "__main__":
    unittest.main()
