import json
import os

# Fallback URLs for components that do not have project_url in the metadata
FALLBACK_URLS = {
    "filebrowser": "https://filebrowser.org/",
    "lora-service": "https://github.com/HenkVanHoek/lora-letterbox-notifier",
    "nextcloud": "https://nextcloud.com/",
    "nextcloud-db": "https://mariadb.org/",
    "nextcloud-db-dumper": "https://github.com/HenkVanHoek/njord-deploy",
    "nextcloud-redis": "https://redis.io/",
    "notify-push": "https://github.com/nextcloud/notify_push",
    "octoprint": "https://octoprint.org/",
    "prosody": "https://prosody.im/",
    "test-playwright": "https://playwright.dev/",
    "uptime-kuma": "https://github.com/louislam/uptime-kuma",
}


def main():
    metadata_path = os.path.join("config", "components_metadata.json")
    if not os.path.exists(metadata_path):
        print(f"Error: {metadata_path} not found.")
        return

    with open(metadata_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    components = data.get("components", {})
    group_rules = data.get("_njorddeploy", {}).get("group_rules", {})
    group_order = data.get("_njorddeploy", {}).get("group_order", [])

    # Group components
    grouped_components = {}
    for comp_id, comp_info in components.items():
        group_id = comp_info.get("group", "general")
        if group_id not in grouped_components:
            grouped_components[group_id] = []
        grouped_components[group_id].append((comp_id, comp_info))

    # Ensure all groups in group_order are represented in output order
    ordered_groups = []
    for g in group_order:
        if g in grouped_components:
            ordered_groups.append(g)
    for g in grouped_components:
        if g not in ordered_groups:
            ordered_groups.append(g)

    # Generate Markdown content
    lines = [
        "# Supported Services",
        "",
        "This document is automatically generated from the project metadata. "
        "It lists the open-source software packages that can be deployed "
        "using NjordDeploy, along with links to their official repositories "
        "and homepages.",
        "",
    ]

    for group_id in ordered_groups:
        group_info = group_rules.get(group_id, {})
        group_name = group_info.get("name", group_id.replace("_", " ").title())

        lines.append(f"## {group_name}")
        lines.append("")
        lines.append("| Service | Description | Project Homepage / Repository |")
        lines.append("|---|---|---|")

        # Sort components by name inside the group
        comps = grouped_components[group_id]
        comps.sort(key=lambda x: x[1].get("name", x[0]).lower())

        for comp_id, comp_info in comps:
            name = comp_info.get("name", comp_id)
            desc = comp_info.get("description", "No description provided.")
            desc = " ".join(desc.replace("\r", " ").replace("\n", " ").split())
            url = comp_info.get("project_url") or FALLBACK_URLS.get(comp_id)

            url_link = f"[Link]({url})" if url else "N/A"
            lines.append(f"| {name} | {desc} | {url_link} |")

        lines.append("")

    output_path = os.path.join("docs", "SUPPORTED_SERVICES.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")
    print(f"Successfully generated {output_path}")


if __name__ == "__main__":
    main()
