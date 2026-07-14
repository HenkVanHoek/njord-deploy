# src/utils/dashy_updater.py
import json
import os
import sys

import yaml

# Define file paths relative to the project root
# These paths will be mapped by Docker volumes
DASHY_CONFIG_PATH = "/app/data/dashy/conf.yml"
METADATA_PATH = "/app/config/components_metadata.json"
SELECTED_COMPONENTS_PATH = "/app/selected_components.txt"


def get_default_dashy_config():
    """Returns a default, minimal Dashy config structure."""
    return {
        "pageInfo": {"title": "NjordDeploy Dashboard"},
        "appConfig": {"theme": "dark"},
        "sections": [{"name": "My Services", "icon": "fas fa-rocket", "items": []}],
    }


def ensure_config_exists():
    """
    Checks if the Dashy config file and its directory exist.
    If not, it creates them with a default configuration.
    This makes the script robust for first-time runs.
    """
    config_dir = os.path.dirname(DASHY_CONFIG_PATH)
    if not os.path.exists(config_dir):
        print(f"Directory not found. Creating {config_dir}...")
        os.makedirs(config_dir)

    if not os.path.isfile(DASHY_CONFIG_PATH):
        print(f"Config file not found. Creating default {DASHY_CONFIG_PATH}...")
        with open(DASHY_CONFIG_PATH, "w") as f:
            yaml.dump(get_default_dashy_config(), f, sort_keys=False, indent=2)


def load_yaml(path):
    """Safely loads a YAML file."""
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file {path}: {e}")
        sys.exit(1)


def load_json(path):
    """Safely loads a JSON file."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found at {path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON file {path}: {e}")
        sys.exit(1)


def get_selected_components(path):
    """Reads component names from a space-separated text file."""
    try:
        with open(path, "r") as f:
            return f.read().strip().split()
    except FileNotFoundError:
        print(f"Error: Selected components file not found at {path}")
        sys.exit(1)


def main(host_ip):
    """Main function to update Dashy config."""
    ensure_config_exists()

    dashy_config = load_yaml(DASHY_CONFIG_PATH)
    metadata = load_json(METADATA_PATH)
    selected_components = get_selected_components(SELECTED_COMPONENTS_PATH)

    # Ensure the config has the expected structure
    if not isinstance(dashy_config, dict) or "sections" not in dashy_config:
        print("Warning: Dashy config seems malformed. Re-initializing with defaults.")
        dashy_config = get_default_dashy_config()

    if not dashy_config["sections"] or "items" not in dashy_config["sections"][0]:
        dashy_config["sections"] = [
            {"name": "My Services", "icon": "fas fa-rocket", "items": []}
        ]

    # Get a list of existing tile titles to prevent duplicates
    existing_titles = {
        item.get("title", "") for item in dashy_config["sections"][0]["items"]
    }

    added_count = 0
    for component_name in selected_components:
        comp_meta = metadata.get(component_name)

        # Check if the component has a UI and is not already in Dashy
        if (
            comp_meta
            and comp_meta.get("has_ui")
            and comp_meta.get("name") not in existing_titles
        ):
            print(f"Found new component with UI: {comp_meta['name']}")

            url = (
                f"{comp_meta.get('protocol', 'http')}://"
                f"{host_ip}:{comp_meta.get('ui_port')}"
            )
            new_tile = {
                "title": comp_meta["name"],
                "icon": comp_meta.get("icon", "fas fa-server"),
                "url": url,
            }

            dashy_config["sections"][0]["items"].append(new_tile)
            added_count += 1
            existing_titles.add(new_tile["title"])

    if added_count > 0:
        try:
            with open(DASHY_CONFIG_PATH, "w") as f:
                yaml.dump(dashy_config, f, sort_keys=False, indent=2)
            print(f"\nSuccessfully added {added_count} new tile(s) to Dashy config.")
            print(f"\nDashy config path: {DASHY_CONFIG_PATH}")
        except IOError as e:
            print(f"Error writing to Dashy config file: {e}")
            sys.exit(1)
    else:
        print(
            "\nNo new components with a UI to add. Dashy config is already up-to-date."
        )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python dashy_updater.py <HOST_IP_ADDRESS>")
        sys.exit(1)

    # Use a different variable name to avoid shadowing the 'main' function's parameter.
    # This makes the code clearer and resolves the linter warning.
    ip_address_from_arg = sys.argv[1]
    main(ip_address_from_arg)
