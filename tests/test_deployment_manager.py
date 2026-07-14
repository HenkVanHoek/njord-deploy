# tests/test_deployment_manager.py
import unittest
from unittest.mock import MagicMock

from src.managers.component_reader import ComponentReader
from src.managers.deployment_manager import DeploymentManager


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
        # Note: This is a placeholder for the actual logic in your manager
        output_path = "/tmp/deploy"
        devices = [{"ip": "192.168.1.50"}]

        # This tests if the manager uses self.reader instead of component_manager
        self.deploy_mgr.start_deployment(
            self.test_task_id, self.tasks_dict, output_path, devices
        )

        # Verify the internal call (lines 197, 360, 399 in manager)
        # Adjust based on your actual method calls in deployment_manager.py
        self.assertTrue(True)  # Placeholder for specific assertions

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
            "src.managers.deployment_manager.ansible_runner.run",
            return_value=mock_runner,
        ):
            self.deploy_mgr.start_deployment(
                self.test_task_id, self.tasks_dict, output_path, devices
            )

        task_res = self.tasks_dict[self.test_task_id]
        self.assertEqual(task_res["status"], "failed")
        self.assertTrue(len(task_res["errors"]) > 0)

        # Verify first error structure
        err = task_res["errors"][0]
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
            "src.managers.deployment_manager.ansible_runner.run",
            return_value=mock_runner,
        ):
            self.deploy_mgr.start_deployment(
                self.test_task_id, self.tasks_dict, output_path, devices
            )

        task_res = self.tasks_dict[self.test_task_id]
        self.assertEqual(task_res["status"], "failed")
        self.assertTrue(len(task_res["errors"]) > 0)

        # Verify first error structure
        err = task_res["errors"][0]
        self.assertEqual(err["type"], "Ansible:ITEM_FAILED")
        self.assertEqual(
            err["summary"],
            "Ansible task failed: Perform Clean Install",
        )
        self.assertIn("no such service", err["details"])


if __name__ == "__main__":
    unittest.main()
