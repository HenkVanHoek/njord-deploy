import json
from unittest.mock import patch

from managers.component_reader import ComponentReader


def test_reader_retrieves_metadata(tmp_path):
    """Test if the reader correctly loads component data from master JSON."""
    meta_path = tmp_path / "metadata.json"
    temp_path = tmp_path / "templates"
    temp_path.mkdir()

    data = {
        "packages": {"core_pkg": {"name": "Core"}},
        "components": {
            "traefik": {
                "name": "Traefik Proxy",
                "group": "core",
                "docker_service_name": "traefik-svc",
            },
            "pihole": {"name": "Pi-hole", "group": "network"},
        },
    }
    meta_path.write_text(json.dumps(data), encoding="utf-8")

    reader = ComponentReader(metadata_path=meta_path, templates_path=temp_path)

    components = reader.get_all_components()
    assert len(components) == 2
    assert components["traefik"]["name"] == "Traefik Proxy"

    details = reader.get_component_details("pihole")
    assert details is not None
    assert details["group"] == "network"

    # docker service name
    assert reader.get_docker_service_name("traefik") == "traefik-svc"
    assert reader.get_docker_service_name("pihole") == "pihole"

    # packages
    pkgs = reader.get_all_packages()
    assert "core_pkg" in pkgs


def test_reader_loads_component_variables(tmp_path):
    """Test if the reader retrieves variables from template-config subfolder."""
    meta_path = tmp_path / "metadata.json"
    meta_path.write_text(json.dumps({"components": {"app": {}}}), encoding="utf-8")

    temp_path = tmp_path / "templates"
    app_config_dir = temp_path / "app" / "template-config"
    app_config_dir.mkdir(parents=True)

    vars_data = {"variables": [{"name": "API_KEY", "default": "secret"}]}
    (app_config_dir / "variables.json").write_text(
        json.dumps(vars_data), encoding="utf-8"
    )

    reader = ComponentReader(metadata_path=meta_path, templates_path=temp_path)
    variables = reader.get_component_variables("app")

    assert len(variables) == 1
    var_first, *_ = variables
    assert var_first["name"] == "API_KEY"


def test_reader_retrieves_test_status_from_template_header(tmp_path):
    """Test that reader extracts status header from docker-compose.template.yml."""
    meta_path = tmp_path / "metadata.json"
    temp_path = tmp_path / "templates"
    temp_path.mkdir()

    comp_dir = temp_path / "adguard"
    comp_dir.mkdir()
    (comp_dir / "docker-compose.template.yml").write_text(
        '# status: "tested"\nservices:\n', encoding="utf-8"
    )

    data = {"components": {"adguard": {"name": "AdGuard"}}}
    meta_path.write_text(json.dumps(data), encoding="utf-8")

    reader = ComponentReader(metadata_path=meta_path, templates_path=temp_path)
    components = reader.get_all_components()
    assert components["adguard"]["test_status"] == "tested"


def test_reader_error_handling_and_fallbacks(tmp_path):
    """Test JSON load error, template read errors, and config file handling."""
    meta_path = tmp_path / "corrupt_metadata.json"
    meta_path.write_text("{ not valid json", encoding="utf-8")
    temp_path = tmp_path / "templates"
    temp_path.mkdir()

    reader = ComponentReader(metadata_path=meta_path, templates_path=temp_path)
    assert reader.get_all_components() == {}

    # Template reading fallback when file does not exist
    content_missing = reader.get_template_content("nonexistent")
    assert content_missing == "services:\n"

    # Template read error simulation
    comp_dir = temp_path / "io_error_comp"
    comp_dir.mkdir()
    tmpl_file = comp_dir / "docker-compose.template.yml"
    tmpl_file.write_text("services:\n", encoding="utf-8")

    with patch("pathlib.Path.read_text", side_effect=IOError("Disk error")):
        content_err = reader.get_template_content("io_error_comp")
        assert "Template for io_error_comp not found" in content_err

    # Configs in template-config
    cfg_dir = comp_dir / "template-config"
    cfg_dir.mkdir()
    (cfg_dir / "conf.d").write_text("server {}", encoding="utf-8")

    configs = reader.get_component_configs("io_error_comp")
    assert "conf.d" in configs
    assert configs["conf.d"] == "server {}"


def test_reader_additional_edge_cases(tmp_path):
    """Test raw list variables, config read IOError, and template header exception."""
    meta_path = tmp_path / "metadata.json"
    temp_path = tmp_path / "templates"
    temp_path.mkdir()

    # Metadata file does not exist
    reader_missing = ComponentReader(
        metadata_path=tmp_path / "nonexistent.json", templates_path=temp_path
    )
    assert reader_missing.get_all_metadata() == {}

    # Component with list-format variables.json
    comp_dir = temp_path / "list_comp"
    cfg_dir = comp_dir / "template-config"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "variables.json").write_text(
        json.dumps([{"name": "DIRECT_LIST"}]), encoding="utf-8"
    )

    meta_path.write_text(
        json.dumps({"components": {"list_comp": {}}}), encoding="utf-8"
    )
    reader = ComponentReader(metadata_path=meta_path, templates_path=temp_path)
    vars_list = reader.get_component_variables("list_comp")
    assert len(vars_list) == 1
    var_first, *_ = vars_list
    assert var_first["name"] == "DIRECT_LIST"

    # Template status parsing exception fallback
    tmpl_file = comp_dir / "docker-compose.template.yml"
    tmpl_file.write_text("invalid", encoding="utf-8")
    with patch("pathlib.Path.read_text", side_effect=RuntimeError("Read fail")):
        status = reader.get_template_status("list_comp")
        assert status == "untested"

    # Configs with IOError during read
    (cfg_dir / "test.conf").write_text("content", encoding="utf-8")
    with patch("pathlib.Path.read_text", side_effect=IOError("Permission denied")):
        cfgs = reader.get_component_configs("list_comp")
        assert cfgs == {}

    # get_docker_service_name for nonexistent component (line 80)
    assert reader.get_docker_service_name("unknown_comp_xyz") == "unknown_comp_xyz"

    # get_component_details with comp missing test_status (line 72)
    with patch.object(
        reader, "get_all_components", return_value={"mock_c": {"name": "Mock"}}
    ):
        details = reader.get_component_details("mock_c")
        assert details["test_status"] == "untested"


def test_reader_private_overlay(tmp_path):
    """Test loading components and templates from private overlays."""
    public_meta = tmp_path / "public_meta.json"
    public_meta.write_text(
        json.dumps({"components": {"public_app": {"name": "Public"}}}),
        encoding="utf-8",
    )
    public_templates = tmp_path / "public_templates"
    public_templates.mkdir()

    priv_meta = tmp_path / "private_meta.json"
    priv_meta.write_text(
        json.dumps(
            {
                "components": {
                    "nedfact": {
                        "name": "NedFact",
                        "image_name": "git.piselfhosting.com/hvhoek/nedfact",
                    }
                },
                "packages": {"priv_pkg": {"name": "Private Package"}},
            }
        ),
        encoding="utf-8",
    )
    priv_templates = tmp_path / "private_templates"
    priv_comp = priv_templates / "nedfact"
    priv_comp.mkdir(parents=True)
    priv_tpl = priv_comp / "docker-compose.template.yml"
    priv_tpl.write_text(
        "services:\n  nedfact:\n    image: nedfact:latest\n", encoding="utf-8"
    )

    priv_cfg = priv_comp / "template-config"
    priv_cfg.mkdir()
    (priv_cfg / "variables.json").write_text(
        json.dumps({"variables": [{"id": "SECRET_KEY"}]}),
        encoding="utf-8",
    )
    (priv_cfg / "app.conf").write_text("env = prod", encoding="utf-8")

    reader = ComponentReader(
        metadata_path=public_meta,
        templates_path=public_templates,
        private_templates_path=priv_templates,
        private_metadata_path=priv_meta,
    )

    all_meta = reader.get_all_metadata()
    assert "public_app" in all_meta["components"]
    assert "nedfact" in all_meta["components"]
    assert all_meta["components"]["nedfact"]["private"] is True
    assert all_meta["packages"]["priv_pkg"]["private"] is True

    # Template path resolution
    assert reader.get_template_path("nedfact") == priv_tpl

    # Variables resolution
    vars_list = reader.get_component_variables("nedfact")
    assert len(vars_list) == 1
    first_var, *_ = vars_list
    assert first_var["id"] == "SECRET_KEY"

    # Configs resolution
    cfgs = reader.get_component_configs("nedfact")
    assert "app.conf" in cfgs
    assert cfgs["app.conf"] == "env = prod"
