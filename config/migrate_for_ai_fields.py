import json
from pathlib import Path


def migrate_metadata(input_file: str, output_file: str):
    """
    Migrates existing component metadata to include AI-specific fields.
    """
    path = Path(input_file)
    if not path.exists():
        print(f"Error: {input_file} not found.")
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Initialize packages section if missing
    if "packages" not in data:
        data["packages"] = {
            "general-stack": {
                "name": "General Stack",
                "description": "Default collection of standalone services.",
                "network_type": "bridge",
            }
        }

    # 2. Enrich components with AI tags and resource profiles
    for comp_id, metadata in data.get("components", {}).items():
        # Set default values for AI orchestration
        metadata.setdefault("package_id", "general-stack")
        metadata.setdefault("tags", ["self-hosted"])
        metadata.setdefault("intent_questions", [])

        if "resource_profile" not in metadata:
            metadata["resource_profile"] = {
                "cpu": "medium",
                "ram": "medium",
                "storage_type": "persistent",
            }

    # 3. Save as a new version for safety
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Migration successful! New file created: {output_file}")


if __name__ == "__main__":
    migrate_metadata("components_metadata.json", "components_metadata_v2.json")
