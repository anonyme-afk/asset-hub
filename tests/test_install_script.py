"""
Tests du script d'installation (scripts/install.py), en particulier la
fonction `merge_config` qui doit JAMAIS écraser une config MCP existante.
Aucun réseau requis.
"""

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "install_script", Path(__file__).resolve().parent.parent / "scripts" / "install.py"
)
install_script = importlib.util.module_from_spec(_SPEC)
sys.modules["install_script"] = install_script
_SPEC.loader.exec_module(install_script)

merge_config = install_script.merge_config
build_entry = install_script.build_entry


def test_creates_config_file_if_missing():
    with tempfile.TemporaryDirectory() as tmp:
        config_path = Path(tmp) / "nested" / "claude_desktop_config.json"
        entry = build_entry(Path("/fake/python"))

        wrote = merge_config(config_path, entry, "asset-hub", dry_run=False)

        assert wrote is True
        assert config_path.exists()
        data = json.loads(config_path.read_text())
        assert data["mcpServers"]["asset-hub"]["command"] == "/fake/python"


def test_preserves_existing_servers_and_other_keys():
    with tempfile.TemporaryDirectory() as tmp:
        config_path = Path(tmp) / "config.json"
        config_path.write_text(
            json.dumps(
                {
                    "mcpServers": {"filesystem": {"command": "npx", "args": ["whatever"]}},
                    "unrelatedTopLevelKey": "do-not-touch",
                }
            )
        )
        entry = build_entry(Path("/fake/python"))

        merge_config(config_path, entry, "asset-hub", dry_run=False)

        data = json.loads(config_path.read_text())
        assert "filesystem" in data["mcpServers"]  # pas écrasé
        assert data["unrelatedTopLevelKey"] == "do-not-touch"  # pas écrasé
        assert "asset-hub" in data["mcpServers"]  # bien ajouté


def test_rerun_is_idempotent_not_duplicated():
    with tempfile.TemporaryDirectory() as tmp:
        config_path = Path(tmp) / "config.json"
        entry = build_entry(Path("/fake/python"))

        merge_config(config_path, entry, "asset-hub", dry_run=False)
        merge_config(config_path, entry, "asset-hub", dry_run=False)

        data = json.loads(config_path.read_text())
        assert len(data["mcpServers"]) == 1


def test_invalid_json_leaves_file_untouched():
    with tempfile.TemporaryDirectory() as tmp:
        config_path = Path(tmp) / "config.json"
        original_content = "{ceci n'est pas du json valide"
        config_path.write_text(original_content)
        entry = build_entry(Path("/fake/python"))

        wrote = merge_config(config_path, entry, "asset-hub", dry_run=False)

        assert wrote is False
        assert config_path.read_text() == original_content  # strictement inchangé


def test_dry_run_does_not_write_anything():
    with tempfile.TemporaryDirectory() as tmp:
        config_path = Path(tmp) / "config.json"
        entry = build_entry(Path("/fake/python"))

        merge_config(config_path, entry, "asset-hub", dry_run=True)

        assert not config_path.exists()


def test_creates_backup_before_overwriting_existing_file():
    with tempfile.TemporaryDirectory() as tmp:
        config_path = Path(tmp) / "config.json"
        config_path.write_text(json.dumps({"mcpServers": {}}))
        entry = build_entry(Path("/fake/python"))

        merge_config(config_path, entry, "asset-hub", dry_run=False)

        backup_path = config_path.with_suffix(".json.bak")
        assert backup_path.exists()


def test_default_config_path_matches_current_platform():
    path = install_script.default_claude_desktop_config_path()
    assert path.name == "claude_desktop_config.json"
    assert "Claude" in str(path)
