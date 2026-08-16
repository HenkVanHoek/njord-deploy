# tests/test_proxmox_gui.py
import json

from scripts.proxmox_gui import TestRunnerManager, create_app, project_root


def test_proxmox_gui_app_routes(tmp_path, monkeypatch):
    # Isolate results and reports file to avoid touching workspace history
    dummy_rec = [{"component_id": "dummy", "status": "success"}]
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "proxmox_results.json").write_text(json.dumps(dummy_rec))
    (tmp_path / "docs" / "PROXMOX_TESTS.md").write_text("# Test Report")

    class FakeRoot:
        def __truediv__(self, other):
            if other in ("tests", "docs"):
                return tmp_path / other
            return project_root / other

    monkeypatch.setattr("scripts.proxmox_gui.project_root", FakeRoot())

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    # 1. Test index HTML route
    res = client.get("/")
    assert res.status_code == 200
    assert b"NjordDeploy Proxmox Test Suite" in res.data

    # 2. Test config API
    res = client.get("/api/config")
    assert res.status_code == 200
    config_data = json.loads(res.data)
    assert "node" in config_data
    assert "engine" in config_data
    assert "mode" in config_data

    # 3. Test components API
    res = client.get("/api/components")
    assert res.status_code == 200
    components = json.loads(res.data)
    assert isinstance(components, list)
    assert len(components) > 0
    first_comp = components[0]
    assert "id" in first_comp
    assert "name" in first_comp
    assert "status" in first_comp
    assert "is_untestable" in first_comp
    assert "untestable_reason" in first_comp

    # 4. Test report API
    res = client.get("/api/report")
    assert res.status_code == 200
    report_data = json.loads(res.data)
    assert "report" in report_data

    # 5. Test stream API endpoint headers
    res_stream = client.get("/api/stream")
    assert res_stream.status_code == 200
    assert "text/event-stream" in res_stream.content_type
    assert "Connection" not in res_stream.headers

    # 6. Test results history API
    res_results = client.get("/api/results")
    assert res_results.status_code == 200
    assert isinstance(json.loads(res_results.data), list)

    # 7. Test clear results API
    res_clear = client.post("/api/results/clear")
    assert res_clear.status_code == 200
    assert json.loads(res_clear.data).get("success") is True


def test_runner_manager_inspect_log():
    mgr = TestRunnerManager()
    mgr._inspect_log_line(
        "Testing component: adguard-home (Engine: PODMAN, Mode: LXC)", "podman"
    )
    assert mgr.current_component == "adguard-home"

    msg = mgr.log_queue.get_nowait()
    assert msg.get("type") == "record"
    record = msg.get("record", {})
    assert record.get("component_id") == "adguard-home"
    assert record.get("engine") == "PODMAN"
    assert record.get("mode") == "LXC"
    assert record.get("status") == "running"
    assert "timestamp" in record

    mgr._inspect_log_line("✅ Component adguard-home verified successfully!", "podman")
    msg2 = mgr.log_queue.get_nowait()
    assert msg2.get("type") == "record"
    assert msg2.get("record", {}).get("status") == "success"
    assert msg2.get("record", {}).get("engine") == "PODMAN"
    assert msg2.get("record", {}).get("mode") == "LXC"


def test_api_run_matrix_modes(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "scripts.proxmox_gui.TestRunnerManager.start_test",
        lambda self, components, engine, mode, node, template_id: True,
    )
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    res = client.post(
        "/api/run",
        json={"components": ["web-notepad"], "engine": "both", "mode": "both"},
    )
    assert res.status_code == 200
    assert res.json.get("success") is True


def test_runner_manager_completion_counters():
    mgr = TestRunnerManager()
    mgr.current_run_passed = 2
    mgr.current_run_failures = 0

    assert mgr.current_run_passed == 2
    assert mgr.current_run_failures == 0


def test_ai_endpoints_mocked(tmp_path, monkeypatch):
    class FakeRoot:
        def __truediv__(self, other):
            if other in ("tests", "docs", "component_templates"):
                return tmp_path / other
            return project_root / other

    monkeypatch.setattr("scripts.proxmox_gui.project_root", FakeRoot())

    comp_dir = tmp_path / "component_templates" / "traefik"
    comp_dir.mkdir(parents=True, exist_ok=True)
    (comp_dir / "docker-compose.template.yml").write_text(
        "services:\n  traefik:\n    image: traefik:v3\n"
    )

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    # 1. AI status
    res = client.get("/api/ai/status")
    assert res.status_code == 200
    assert "configured" in res.json

    # 2. Single diagnose mocked
    mock_diag = {
        "component_id": "traefik",
        "summary": "Missing flag",
        "root_cause_analysis": "Port 8080 404",
        "fix_description": "Add flag",
        "suggested_template": (
            "services:\n  traefik:\n    command: ['--api.insecure=true']\n"
        ),
        "diff": "+ command",
    }

    monkeypatch.setattr(
        "utils.ai_failure_diagnoser.AIFailureDiagnoser.is_configured",
        lambda self: True,
    )
    monkeypatch.setattr(
        "utils.ai_failure_diagnoser.AIFailureDiagnoser.diagnose_single_failure",
        lambda self, test_record, template_content, container_logs="", **kwargs: (
            mock_diag
        ),
    )
    monkeypatch.setattr(
        "utils.ai_failure_diagnoser.AIFailureDiagnoser.diagnose_batch_failures",
        lambda self, failed_records, templates_map=None: {
            "total_analyzed": len(failed_records),
            "systemic_summary": "Systemic batch pattern",
            "clusters": [],
        },
    )

    res_diag = client.post(
        "/api/ai/diagnose",
        json={"component_id": "traefik", "record": {"status": "failed"}},
    )
    assert res_diag.status_code == 200
    assert res_diag.json["diagnosis"]["component_id"] == "traefik"

    # 3. Batch diagnose mocked
    res_batch = client.post(
        "/api/ai/diagnose",
        json={
            "batch": True,
            "records": [{"component_id": "traefik", "status": "failed"}],
        },
    )
    assert res_batch.status_code == 200
    assert res_batch.json["batch"] is True
    assert res_batch.json["diagnosis"]["total_analyzed"] == 1

    # 4. Apply patch
    res_patch = client.post(
        "/api/ai/apply-patch",
        json={
            "component_id": "traefik",
            "template_content": (
                "services:\n  traefik:\n    command: ['--api.insecure=true']\n"
            ),
        },
    )
    assert res_patch.status_code == 200
    assert res_patch.json.get("success") is True

    # 5. Apply matrix constraint
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "components_metadata.json").write_text(
        json.dumps({"components": {"traefik": {"name": "Traefik"}}}),
        encoding="utf-8",
    )
    res_matrix = client.post(
        "/api/ai/apply-matrix-constraint",
        json={
            "component_id": "traefik",
            "modes": ["vm"],
            "engines": ["docker"],
            "notes": "Requires VM mode",
        },
    )
    assert res_matrix.status_code == 200
    assert res_matrix.json.get("success") is True
