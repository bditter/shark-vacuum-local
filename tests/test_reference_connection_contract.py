"""Regression tests for the downloaded Reference connection behavior."""
from __future__ import annotations

import ast
from pathlib import Path


INTEGRATION = (
    Path(__file__).parents[1] / "custom_components" / "shark_vacuum_local"
)


def _tree(filename: str) -> ast.Module:
    return ast.parse((INTEGRATION / filename).read_text(encoding="utf-8"))


def test_client_uses_one_configured_mapping_per_transport() -> None:
    """Match Reference: one REST map and optional MQTT with the same map."""
    tree = _tree("client.py")
    factory = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "create_vacuum_client"
    )
    call = next(
        node
        for node in ast.walk(factory)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "VacuumClient"
    )
    keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in call.keywords}

    assert keywords["rest_mappings"] == "mapping"
    assert keywords["mqtt_mappings"] == "mapping if use_mqtt else None"


def test_setup_does_not_eagerly_probe_transport_candidates() -> None:
    """Match Reference: get_status drives normal REST-to-MQTT fallback."""
    for filename in ("config_flow.py", "coordinator.py"):
        calls = [
            node
            for node in ast.walk(_tree(filename))
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "probe"
        ]
        assert calls == [], f"Unexpected probe() call in {filename}"


def test_vacuum_start_uses_confirmed_mqtt_level_command() -> None:
    """The captured level command also starts or resumes cleaning."""
    tree = _tree("vacuum.py")
    start = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "async_start"
    )
    calls = [
        node.func.attr
        for node in ast.walk(start)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    assert "set_level" in calls
    assert "start_cleaning" not in calls


def test_vacuum_level_defaults_to_normal_and_select_platform_is_loaded() -> None:
    """Lock the optimistic default and select platform into the contract."""
    const_tree = _tree("const.py")
    assignments = {
        target.id: ast.literal_eval(node.value)
        for node in const_tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
        and target.id
        in {"DEFAULT_VACUUM_LEVEL", "VACUUM_LEVEL_VALUES", "PLATFORMS"}
    }

    assert assignments["DEFAULT_VACUUM_LEVEL"] == "Normal"
    assert assignments["VACUUM_LEVEL_VALUES"] == {
        "Eco": 50,
        "Normal": 75,
        "Max": 100,
    }
    assert "select" in assignments["PLATFORMS"]
    assert "switch" in assignments["PLATFORMS"]
    assert "number" in assignments["PLATFORMS"]


def test_captured_mqtt_payloads_are_preserved() -> None:
    """Lock all user-verified commands to their exact base64 payloads."""
    tree = _tree("client.py")
    source = (INTEGRATION / "client.py").read_text(encoding="utf-8")
    module = ast.Module(
        body=[
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name in {"_varint", "setting_payload", "vacuum_level_payload"}
        ],
        type_ignores=[],
    )
    namespace = {
        "base64": __import__("base64"),
        "VACUUM_LEVEL_VALUES": {"Eco": 50, "Normal": 75, "Max": 100},
        "HomeAssistantError": ValueError,
    }
    exec(compile(module, source, "exec"), namespace)

    level = namespace["vacuum_level_payload"]
    setting = namespace["setting_payload"]
    assert level("Eco") == "OgQKAhAygAEJ"
    assert level("Normal") == "OgQKAhBLgAEJ"
    assert level("Max") == "OgQKAhBkgAEJ"
    assert setting(8, 2) == "OgJAAg=="
    assert setting(8, 1) == "OgJAAQ=="
    assert setting(7, 2) == "OgI4Ag=="
    assert setting(7, 1) == "OgI4AQ=="
    assert setting(13, 2) == "OgJoAg=="
    assert setting(13, 1) == "OgJoAQ=="
    assert setting(2, 0) == "OgIQAA=="
    assert setting(2, 100) == "OgIQZA=="


def test_entities_explicitly_suggest_ids_without_areas() -> None:
    """Do not let HA's entity-ID generator add the assigned area name."""
    base_tree = _tree("entity.py")
    helper = next(
        node
        for node in ast.walk(base_tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_suggest_object_id"
    )
    assignments = [
        node
        for node in ast.walk(helper)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Attribute)
            and target.attr == "_attr_suggested_object_id"
            for target in node.targets
        )
    ]
    assert assignments

    for filename in ("vacuum.py", "sensor.py", "select.py", "switch.py", "number.py"):
        calls = [
            node
            for node in ast.walk(_tree(filename))
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "_suggest_object_id"
        ]
        assert calls, f"{filename} does not set an explicit suggested object ID"


def test_setup_migrates_only_generated_area_prefixes() -> None:
    """Existing generated IDs are repaired before platforms are loaded."""
    tree = _tree("__init__.py")
    setup = next(
        node
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "async_setup_entry"
    )
    calls = [
        node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
        for node in ast.walk(setup)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Attribute, ast.Name))
    ]
    assert calls.index("_async_remove_generated_area_prefixes") < calls.index(
        "async_forward_entry_setups"
    )


def test_area_migration_removes_orphaned_states() -> None:
    """Both newly renamed and previously orphaned state IDs are cleaned up."""
    tree = _tree("__init__.py")
    migration = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_async_remove_generated_area_prefixes"
    )
    removals = [
        node
        for node in ast.walk(migration)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "async_remove"
    ]
    assert len(removals) == 3

    registry_checks = [
        node
        for node in ast.walk(migration)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "async_get"
    ]
    assert registry_checks, "Stale states must not replace registered entities"

    state_scans = [
        node
        for node in ast.walk(migration)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "async_all"
    ]
    assert state_scans, "Cleanup must work after device and registry deletion"
