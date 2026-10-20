# tests/test_setup_manager.py
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from src.managers.component_reader import ComponentReader
from src.managers.setup_manager import SetupManager


class TestSetupManager(unittest.TestCase):
    """
    Test suite for the refactored SetupManager.
    """

    def setUp(self):
        """Set up the test environment with a temporary path."""
        self.mock_reader = MagicMock(spec=ComponentReader)
        self.test_dir = Path("./tmp_setup_test")
        self.setup_manager = SetupManager(
            component_manager=self.mock_reader, output_dir=self.test_dir
        )

    def tearDown(self):
        """Clean up temporary directory after tests."""
        if self.test_dir.exists():
            import shutil

            shutil.rmtree(self.test_dir)

    def test_initialize_environment_creates_directories(self):
        """Test if the manager creates the base and log directories."""
        success = self.setup_manager.initialize_environment()

        self.assertTrue(success)
        self.assertTrue(self.test_dir.exists())
        self.assertTrue((self.test_dir / "logs").exists())

    def test_verify_component_setup_success(self):
        """Test component verification when it exists in metadata."""
        self.mock_reader.get_component_details.return_value = {"name": "Test"}

        result = self.setup_manager.verify_component_setup("existing-app")

        self.assertTrue(result)
        self.mock_reader.get_component_details.assert_called_with("existing-app")

    def test_get_setup_report(self):
        """Verify the structure of the setup report."""
        self.mock_reader.get_all_components.return_value = {"a": {}, "b": {}}

        # Initialize first to set status to ready
        self.setup_manager.initialize_environment()
        report = self.setup_manager.get_setup_report()

        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["components_available"], 2)
        self.assertIn("base_path", report)

    def test_prepare_deployment_package_docs(self):
        """Verify that prepare_deployment_package copies docs correctly."""
        # Create a mock templates directory
        mock_templates = Path("./tmp_templates_test")
        mock_templates.mkdir(exist_ok=True)
        docs_template = mock_templates / "njorddeploy-docs"
        docs_template.mkdir(exist_ok=True)
        (docs_template / "src-docs" / "docs").mkdir(parents=True, exist_ok=True)

        self.mock_reader.templates_path = str(mock_templates)

        try:
            # We run the preparation
            success, errors = self.setup_manager.prepare_deployment_package(
                selected_components=["njorddeploy-docs"],
                user_variables={"VAR": "val"},
                managed_devices=[],
            )

            self.assertTrue(success)
            self.assertEqual(len(errors), 0)

            # Check if src-docs was created
            target_docs_dir = self.test_dir / "njorddeploy-docs" / "src-docs"
            self.assertTrue(target_docs_dir.exists())

            # Documentation files exist in the project root and
            # should have been copied to the target directory.
            self.assertTrue((target_docs_dir / "index.md").exists())
            self.assertTrue((target_docs_dir / "contributing.md").exists())
            self.assertTrue((target_docs_dir / "utilities.md").exists())
            self.assertTrue((target_docs_dir / "docs").exists())

            # Run a second time to verify dst_docs_dir overwrite
            success2, _ = self.setup_manager.prepare_deployment_package(
                selected_components=["njorddeploy-docs"],
                user_variables={"VAR": "val2"},
                managed_devices=[],
            )
            self.assertTrue(success2)

        finally:
            # Clean up the mock templates directory
            if mock_templates.exists():
                import shutil

                shutil.rmtree(mock_templates)

    def test_verify_component_setup_failure(self):
        """Test component verification when not found."""
        self.mock_reader.get_component_details.return_value = None
        self.assertFalse(self.setup_manager.verify_component_setup("unknown"))

    def test_initialize_environment_exception(self):
        """Test initialize_environment catching exceptions."""
        from unittest.mock import patch

        with patch.object(Path, "mkdir", side_effect=PermissionError("denied")):
            self.assertFalse(self.setup_manager.initialize_environment())

    def test_prepare_deployment_package_overwrite_and_errors(self):
        """Test overwriting existing destination dir and error handling."""
        mock_templates = Path("./tmp_templates_test2")
        mock_templates.mkdir(exist_ok=True)
        comp_dir = mock_templates / "app"
        comp_dir.mkdir(exist_ok=True)
        self.mock_reader.templates_path = str(mock_templates)

        try:
            # First run creates app
            ok1, _ = self.setup_manager.prepare_deployment_package(
                ["app"], {"A": "1"}, []
            )
            self.assertTrue(ok1)

            # Second run overwrites existing app dir
            ok2, _ = self.setup_manager.prepare_deployment_package(
                ["app"], {"A": "2"}, []
            )
            self.assertTrue(ok2)

            # Component template directory does not exist
            ok3, _ = self.setup_manager.prepare_deployment_package(
                ["missing_comp"], {}, []
            )
            self.assertTrue(ok3)

            # Exception during prepare
            from unittest.mock import patch

            with patch("builtins.open", side_effect=IOError("Disk locked")):
                ok_err, errs = self.setup_manager.prepare_deployment_package(
                    ["app"], {}, []
                )
                self.assertFalse(ok_err)
                self.assertTrue(len(errs) > 0)
        finally:
            import shutil

            if mock_templates.exists():
                shutil.rmtree(mock_templates)
