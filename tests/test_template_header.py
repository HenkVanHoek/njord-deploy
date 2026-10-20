# tests/test_template_header.py
from utils.template_header import merge_platform_notes, update_template_header_content


def test_merge_platform_notes_initial():
    notes = merge_platform_notes(
        existing_notes="None",
        mode="LXC",
        engine="docker",
        version="v1.2.3",
        test_date="2026-08-14",
    )
    assert notes == "Tested on Proxmox LXC: docker (v1.2.3, 2026-08-14)."


def test_merge_platform_notes_cumulative_engines():
    # 1. First test: LXC + docker
    notes1 = merge_platform_notes(
        existing_notes="None",
        mode="LXC",
        engine="docker",
        version="v1.0.0",
        test_date="2026-08-14",
    )
    assert notes1 == "Tested on Proxmox LXC: docker (v1.0.0, 2026-08-14)."

    # 2. Second test: LXC + podman
    notes2 = merge_platform_notes(
        existing_notes=notes1,
        mode="LXC",
        engine="podman",
        version="v1.0.0",
        test_date="2026-08-14",
    )
    assert notes2 == (
        "Tested on Proxmox LXC: docker (v1.0.0, 2026-08-14), "
        "podman (v1.0.0, 2026-08-14)."
    )

    # 3. Third test: VM + docker
    notes3 = merge_platform_notes(
        existing_notes=notes2,
        mode="VM",
        engine="docker",
        version="v1.0.1",
        test_date="2026-08-15",
    )
    expected = (
        "Tested on Proxmox LXC: docker (v1.0.0, 2026-08-14), "
        "podman (v1.0.0, 2026-08-14); Proxmox VM: docker (v1.0.1, 2026-08-15)."
    )
    assert notes3 == expected


def test_merge_platform_notes_legacy_string():
    legacy = "Tested successfully on Proxmox LXC (docker)."
    notes = merge_platform_notes(
        existing_notes=legacy,
        mode="LXC",
        engine="podman",
        version="v2.5.0",
        test_date="2026-08-14",
    )
    assert notes == (
        "Tested on Proxmox LXC: docker (latest, 2026-08-14), "
        "podman (v2.5.0, 2026-08-14)."
    )


def test_update_template_header_content():
    content = (
        '# status: "untested"\n'
        '# last_tested_version: "none"\n'
        '# platform_notes: "None"\n'
        '# breaking_changes: "None"\n'
        "services:\n"
        "  app:\n"
        "    image: app:latest\n"
    )

    updated = update_template_header_content(
        content=content,
        mode="LXC",
        engine="docker",
        tested_version="v3.0.0",
        test_date="2026-08-14",
    )

    assert '# last_tested_version: "v3.0.0"' in updated
    assert (
        '# platform_notes: "Tested on Proxmox LXC: docker (v3.0.0, 2026-08-14)."'
        in updated
    )
    assert "services:\n  app:\n" in updated


def test_template_header_edge_cases():
    """Test VM legacy notes, default date, version retention, and header prepending."""
    # 1. Default test_date is None
    notes_date_none = merge_platform_notes(
        "None", mode="LXC", engine="docker", version="v1.0"
    )
    assert "Tested on Proxmox LXC: docker" in notes_date_none

    # 2. Existing notes with Proxmox VM section
    vm_legacy = "Tested on Proxmox VM: docker (v1.0, 2026-01-01)."
    notes_merged = merge_platform_notes(
        vm_legacy, mode="VM", engine="podman", version="v1.1"
    )
    assert "Proxmox VM: docker" in notes_merged
    assert "podman (v1.1" in notes_merged

    # 3. Content without header comments: prepends missing headers
    headerless = "services:\n  web:\n    image: nginx\n"
    res_prepended = update_template_header_content(
        content=headerless,
        mode="VM",
        engine="docker",
        tested_version="v2.0",
    )
    assert '# status: "tested"' in res_prepended
    assert '# last_tested_version: "v2.0"' in res_prepended
    assert "services:\n  web:\n" in res_prepended

    # 4. Retaining existing version when tested_version is 'latest'
    content_with_ver = (
        '# status: "tested"\n'
        '# last_tested_version: "v5.4.1"\n'
        '# platform_notes: "None"\n'
        "services:\n"
    )
    res_kept = update_template_header_content(
        content=content_with_ver,
        mode="LXC",
        engine="docker",
        tested_version="latest",
    )
    assert '# last_tested_version: "v5.4.1"' in res_kept


def test_merge_platform_notes_custom_platform_and_engine():
    """Verify ordering with custom engine (containerd)."""
    notes = merge_platform_notes(
        existing_notes="Tested on Proxmox LXC: docker (v1.0, 2026-01-01).",
        mode="LXC",
        engine="containerd",
        version="v1.7.0",
        test_date="2026-09-01",
    )
    assert "containerd (v1.7.0, 2026-09-01)" in notes
    assert "docker (v1.0, 2026-01-01)" in notes
