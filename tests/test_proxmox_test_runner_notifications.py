# tests/test_proxmox_test_runner_notifications.py
from scripts.proxmox_package_test_runner import build_package_signal_report_message
from scripts.proxmox_test_runner import build_signal_report_message


def test_build_signal_report_message_single_component_success():
    """Verify notification formatting when a single component passes."""
    results = [
        {
            "component_id": "semaphore",
            "mode": "LXC",
            "engine": "DOCKER",
            "status": "success",
        }
    ]
    matrix = [("lxc", "docker")]
    msg = build_signal_report_message(
        results_summary=results,
        matrix=matrix,
        passed_count=1,
        skipped_count=0,
        failed_count=0,
    )

    assert "🚢 NjordDeploy Proxmox Test Report: semaphore" in msg
    assert "Component: semaphore" in msg
    assert "Environments: LXC+DOCKER" in msg
    assert "Status: ✅ ALL SUCCESSFUL" in msg
    assert "Total tested: 1" in msg
    assert "Passed: 1" in msg
    assert "Failed: 0" in msg


def test_build_signal_report_message_multi_component_mixed():
    """Verify notification formatting with multiple components and mixed outcomes."""
    results = [
        {
            "component_id": "adguard-home",
            "mode": "LXC",
            "engine": "DOCKER",
            "status": "success",
        },
        {
            "component_id": "immich",
            "mode": "LXC",
            "engine": "DOCKER",
            "status": "failed",
        },
        {
            "component_id": "wireguard",
            "mode": "LXC",
            "engine": "DOCKER",
            "status": "skipped",
        },
    ]
    matrix = [("lxc", "docker")]
    msg = build_signal_report_message(
        results_summary=results,
        matrix=matrix,
        passed_count=1,
        skipped_count=1,
        failed_count=1,
    )

    assert "🚢 NjordDeploy Proxmox Test Report (3 components)" in msg
    assert "Components: adguard-home, immich, wireguard" in msg
    assert "Status: ❌ FAILED" in msg
    assert "Total tested: 3" in msg
    assert "Passed: 1" in msg
    assert "Skipped: 1" in msg
    assert "Failed: 1" in msg
    assert "Passed: adguard-home" in msg
    assert "Skipped: wireguard" in msg
    assert "Failed: immich (LXC/DOCKER)" in msg


def test_build_signal_report_message_large_catalog():
    """Verify formatting when more than 8 components are tested."""
    results = [
        {
            "component_id": f"service-{i}",
            "mode": "LXC",
            "engine": "DOCKER",
            "status": "success",
        }
        for i in range(12)
    ]
    matrix = [("lxc", "docker")]
    msg = build_signal_report_message(
        results_summary=results,
        matrix=matrix,
        passed_count=12,
        skipped_count=0,
        failed_count=0,
    )

    assert "🚢 NjordDeploy Proxmox Test Report (12 components)" in msg
    assert "Components: 12 items (" in msg
    assert "Status: ✅ ALL SUCCESSFUL" in msg
    assert "Total tested: 12" in msg
    assert "Passed: 12" in msg


def test_build_signal_report_message_empty():
    """Verify formatting when no tests were executed."""
    msg = build_signal_report_message(
        results_summary=[],
        matrix=[("lxc", "docker")],
        passed_count=0,
        skipped_count=0,
        failed_count=0,
    )

    assert "🚢 NjordDeploy Proxmox Test Report" in msg
    assert "Status: ❌ INCOMPLETE / NO TESTS EXECUTED" in msg
    assert "Total tested: 0" in msg


def test_build_package_signal_report_message_single_success():
    """Verify notification formatting for single package tests."""
    results = [
        {
            "package_id": "homelab-essential",
            "mode": "LXC",
            "status": "success",
        }
    ]
    msg = build_package_signal_report_message(
        results_summary=results,
        passed_count=1,
        failed_count=0,
    )

    assert "🚢 NjordDeploy Proxmox Package Test Report: homelab-essential" in msg
    assert "Package: homelab-essential" in msg
    assert "Status: ✅ ALL SUCCESSFUL" in msg
    assert "Total packages tested: 1" in msg
    assert "Passed: 1" in msg


def test_build_package_signal_report_message_multi_mixed():
    """Verify notification formatting for multiple packages with failures."""
    results = [
        {"package_id": "pkg-a", "mode": "LXC", "status": "success"},
        {"package_id": "pkg-b", "mode": "VM", "status": "failed"},
    ]
    msg = build_package_signal_report_message(
        results_summary=results,
        passed_count=1,
        failed_count=1,
    )

    assert "🚢 NjordDeploy Proxmox Package Test Report (2 packages)" in msg
    assert "Packages: pkg-a, pkg-b" in msg
    assert "Status: ❌ FAILED" in msg
    assert "Total packages tested: 2" in msg
    assert "Passed: pkg-a (LXC)" in msg
    assert "Failed: pkg-b (VM)" in msg
