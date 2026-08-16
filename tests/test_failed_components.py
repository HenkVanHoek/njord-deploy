# tests/test_failed_components.py
from utils.failed_components import (
    add_or_update_untestable_component,
    is_component_untestable,
    load_untestable_components,
    remove_untestable_component,
)


def test_load_untestable_components(tmp_path):
    doc_file = tmp_path / "FAILED_COMPONENTS.md"
    sample_content = """# Failed Components

## Skipped / Untestable Components

### `service-a`
*   **Date**: 2026-07-15
*   **Reason**: Missing physical hardware.
*   **Action**: Skipped.

### `service-b` (Special Description)
*   **Date**: 2026-07-16
*   **Reason**: Broken template.
*   **Action**: Needs rewrite.

### `service-c`
*   **Status**: Fixed (2026-07-20)
*   **Fix**: Already repaired.

## Other Section
### `service-d`
*   **Reason**: In other section.
"""
    doc_file.write_text(sample_content, encoding="utf-8")

    untestable = load_untestable_components(doc_path=doc_file)
    assert "service-a" in untestable
    assert "service-b" in untestable
    assert "service-c" not in untestable  # Marked as Fixed
    assert "service-d" not in untestable  # Not under Skipped / Untestable

    assert untestable["service-a"]["reason"] == "Missing physical hardware."
    assert is_component_untestable("service-a", doc_path=doc_file) is True
    assert is_component_untestable("service-c", doc_path=doc_file) is False


def test_remove_untestable_component(tmp_path):
    doc_file = tmp_path / "FAILED_COMPONENTS.md"
    sample_content = """# Failed Components

## Skipped / Untestable Components

### `service-a`
*   **Date**: 2026-07-15
*   **Reason**: Missing physical hardware.
*   **Action**: Skipped.

### `service-b`
*   **Date**: 2026-07-16
*   **Reason**: Broken template.
*   **Action**: Needs rewrite.
"""
    doc_file.write_text(sample_content, encoding="utf-8")

    # Remove service-a
    res = remove_untestable_component("service-a", doc_path=doc_file)
    assert res is True
    assert is_component_untestable("service-a", doc_path=doc_file) is False
    assert is_component_untestable("service-b", doc_path=doc_file) is True

    # Removing non-existent returns False
    res_non_existent = remove_untestable_component("non-existent", doc_path=doc_file)
    assert res_non_existent is False


def test_add_or_update_untestable_component(tmp_path):
    doc_file = tmp_path / "FAILED_COMPONENTS.md"

    add_or_update_untestable_component(
        "new-service",
        reason="Requires /dev/net/tun",
        action="Skipped on LXC",
        date_str="2026-08-14",
        doc_path=doc_file,
    )

    untestable = load_untestable_components(doc_path=doc_file)
    assert "new-service" in untestable
    assert untestable["new-service"]["reason"] == "Requires /dev/net/tun"
    assert is_component_untestable("new-service", doc_path=doc_file) is True
