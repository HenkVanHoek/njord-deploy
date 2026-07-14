# tests/test_component_writer.py

import json

from src.managers.component_writer import ComponentWriter


def test_writer_creates_component_skeleton(tmp_path):
    """
    Test if the writer correctly creates the directory structure
    under template-config and updates the metadata.
    """
    # Setup: Define paths within the temporary directory
    meta_path = tmp_path / "metadata.json"
    meta_path.write_text(json.dumps({"components": {}}), encoding="utf-8")

    temp_path = tmp_path / "templates"
    temp_path.mkdir()

    # Initialize the writer
    writer = ComponentWriter(metadata_path=meta_path, templates_path=temp_path)

    # Execute
    component_id = "new-app"
    meta_data = {"name": "New App", "version": "1.0.0"}
    success = writer.create_component_skeleton(component_id, meta_data)

    # Verify: Check structural paths
    assert success is True
    assert (temp_path / component_id).exists()
    assert (temp_path / component_id / "template-config" / "variables.json").exists()
    assert (temp_path / component_id / "docker-compose.template.yml").exists()

    # Verify: Master metadata
    with open(meta_path, "r", encoding="utf-8") as f:
        updated_meta = json.load(f)

    assert component_id in updated_meta["components"]
    assert updated_meta["components"][component_id]["name"] == "New App"
