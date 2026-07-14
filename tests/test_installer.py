# tests/test_installer.py
import unittest
from pathlib import Path
from unittest.mock import patch

from njorddeploy_installer import run_installation


class TestInstaller(unittest.TestCase):
    """
    Integration tests for the NjordDeploy Installer.
    Ensures the installer correctly orchestrates the ArtifactGenerator and Ansible.
    """

    @patch("njorddeploy_installer.ArtifactGenerator")
    @patch("njorddeploy_installer.ComponentReader")
    @patch("njorddeploy_installer.get_project_root")
    @patch("ansible_runner.run")
    def test_run_installation_full_flow(
        self,
        _mock_ansible,  # Prefixed with underscore to silence linter warnings
        mock_root,
        _mock_reader,
        mock_generator,
    ):
        """
        Validates the full installation generator sequence.
        Matches the pytest discovery pattern 'test_*'.
        """
        # Arrange: Setup paths and generator return values
        mock_root.return_value = Path("/tmp/fake_project")

        mock_gen_inst = mock_generator.return_value
        mock_gen_inst.create_artifacts.return_value = True

        # Mock the filesystem and environment variables
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", return_value="pi-hole"),
            patch(
                "os.getenv",
                side_effect=lambda k, d=None: (
                    "mock" if k in ["PI_IP", "SSH_USER"] else d
                ),
            ),
        ):
            # Act: Consume the generator to trigger all logic steps
            output = list(run_installation())

            # Assert: Verify the success indicators in the output stream
            success_found = any(
                "Deployment package generated successfully" in line for line in output
            )
            self.assertTrue(
                success_found,
                "The installer failed to yield the generation success message.",
            )

            # Verify that the specific ArtifactGenerator method was executed
            mock_gen_inst.create_artifacts.assert_called()


if __name__ == "__main__":
    unittest.main()
