# tests/utils/test_generation_logger.py

"""
Unit tests for GenerationLogger.
"""

from pathlib import Path
from unittest.mock import patch

from utils.generation_logger import GenerationLogger


def test_generation_logger_full_workflow(tmp_path: Path):
    out_dir = tmp_path / "sub" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    logger = GenerationLogger(out_dir)
    assert logger.log_path == out_dir.parent / "generation.log"

    logger.log_section_header("Pipeline Start")
    logger.log_entry("Simple Step")
    logger.log_entry("Detailed Step", details="Additional info")
    logger.log_dict("Configs", {"key": "val"})
    logger.log_list("Components", ["adguard-home", "caddy"])
    logger.log_initial_components(["adguard-home"])
    logger.log_full_component_list(["adguard-home", "caddy"])
    logger.log_global_vars({"DOMAIN": "example.com"})
    logger.log_initial_context({"a": 1})
    logger.log_resolved_context({"b": 2})
    logger.log_final_context({"c": 3})
    logger.log_raw_template_output("caddy", "services:\n  caddy:\n")
    logger.log_generated_file("compose.yml", Path("/tmp/compose.yml"))

    logger.write_log()

    assert logger.log_path.exists()
    content = logger.log_path.read_text(encoding="utf-8")
    assert "Pipeline Start" in content
    assert "Additional info" in content
    assert "adguard-home" in content
    assert "caddy" in content


def test_generation_logger_write_error(tmp_path: Path):
    out_dir = tmp_path / "output"
    logger = GenerationLogger(out_dir)
    with patch("builtins.open", side_effect=IOError("Disk full")):
        # Should catch and log error gracefully
        logger.write_log()
