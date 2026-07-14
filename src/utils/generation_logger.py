import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class GenerationLogger:
    """
    Creates a detailed, human-readable log of a single file generation run.
    The log is a timestamped Markdown file for easy reading and comparison.
    """

    def __init__(self, output_dir: Path):
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        # FIX: Save the log in the parent of the temporary output directory
        # to prevent it from being deleted during cleanup operations.
        self.log_path = output_dir.parent / "generation.log"
        self._log_content = [
            "## NjordDeploy Configuration Generation Log\n",
            f"**Timestamp:** `{timestamp}`\n",
        ]

    def log_section_header(self, title: str):
        """Logs a major step in the process."""
        self._log_content.append(f"\n## {title}\n")

    def log_entry(self, title: str, details: Optional[str] = None):
        """Logs a simple entry with an optional details line."""
        self._log_content.append(f"### {title}\n")
        if details:
            self._log_content.append(f"{details}\n")

    def log_dict(self, name: str, data: Dict[str, Any]):
        """Logs a dictionary as a formatted JSON block."""
        self._log_content.append(f"### {name}\n")
        pretty_json = json.dumps(data, indent=2)
        self._log_content.append(f"```json\n{pretty_json}\n```\n")

    def log_list(self, name: str, data: List[str]):
        """Logs a list of strings."""
        self._log_content.append(f"### {name}\n")
        for item in data:
            self._log_content.append(f"- `{item}`\n")
        self._log_content.append("\n")

    def log_initial_components(self, components: List[str]):
        self.log_list("Initial Components Selected by User", components)

    def log_full_component_list(self, components: List[str]):
        self.log_list("Full Component List (after dependency resolution)", components)

    def log_global_vars(self, variables: Dict[str, Any]):
        self.log_dict("Global Variables Loaded from .env", variables)

    def log_initial_context(self, context: Dict[str, Any]):
        self.log_section_header("Variable Resolution and Context Building")
        self.log_dict("1. Initial Context", context)

    def log_resolved_context(self, context: Dict[str, Any]):
        self.log_dict("2. Resolved Context (Pass 1)", context)

    def log_final_context(self, context: Dict[str, Any]):
        self.log_dict("4. Final Context (After Nested Resolution)", context)

    def log_raw_template_output(self, component_id: str, content: str):
        """Logs the raw rendered string of a component's template."""
        self.log_entry(f"RAW TEMPLATE OUTPUT for '{component_id}'")
        self._log_content.append(f"```yaml\n{content}\n```\n")

    def log_generated_file(self, filename: str, path: Path):
        self.log_entry(f"Generated file: {filename}", f"Location: `{path}`")

    def write_log(self):
        """Writes the collected log content to the final Markdown file."""
        try:
            with open(self.log_path, "w", encoding="utf-8") as f:
                f.write("\n".join(self._log_content))
        except IOError as e:
            # Log an error to the main application log if this fails
            print(
                "CRITICAL: Failed to write generation log file at "
                f"{self.log_path}: {e}"
            )
