# tests/conftest.py
"""Test configuration and module aliasing for unified test coverage."""

import sys

import src.configurator_app.app as configurator_app_module
import src.editor_app.app as editor_app_module

# Alias un-prefixed imports to the src.-prefixed modules so coverage and mocks
# are unified across all test files.
sys.modules["configurator_app.app"] = configurator_app_module
sys.modules["editor_app.app"] = editor_app_module
