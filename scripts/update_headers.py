import os


def find_template_files(root_dir):
    """Find all files ending in template.yml in component_templates."""
    target_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for name in filenames:
            if name.endswith("template.yml"):
                target_files.append(os.path.join(dirpath, name))
    return target_files


def needs_arm_notes(filepath, content):
    """Determine if the file targets ARM architecture."""
    # Check filename
    if "arm" in filepath.lower() or "arm based" in filepath.lower():
        return True
    # Check contents
    content_lower = content.lower()
    if "arm" in content_lower or "arm based" in content_lower:
        return True
    return False


def main():
    """Update all template.yml files with the metadata header."""
    root_dir = "component_templates"
    files = find_template_files(root_dir)
    updated_count = 0
    skipped_count = 0

    for filepath in files:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Check if the header is already present
        if content.startswith("# status:"):
            skipped_count += 1
            continue

        is_arm = needs_arm_notes(filepath, content)

        if is_arm:
            status = "testing"
            platform_notes = "Targeted for ARM architecture."
        else:
            status = "untested"
            platform_notes = "None"

        header = (
            f'# status: "{status}"\n'
            f'# last_tested_version: "none"\n'
            f'# platform_notes: "{platform_notes}"\n'
            f'# breaking_changes: "None"\n'
        )

        new_content = header + content
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)

        updated_count += 1
        print(f"Updated: {filepath} (ARM: {is_arm})")

    print(f"Done. Updated: {updated_count}, Skipped: {skipped_count}")


if __name__ == "__main__":
    main()
