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


def test_vacuum_level_is_applied_before_start_without_blocking_start() -> None:
    """Keep the level attempt separate and ahead of the cleaning command."""
    tree = _tree("vacuum.py")
    start = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "async_start"
    )
    tries = [node for node in start.body if isinstance(node, ast.Try)]

    assert len(tries) == 2
    first_calls = [
        node.func.attr
        for node in ast.walk(tries[0])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    second_calls = [
        node.func.attr
        for node in ast.walk(tries[1])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    assert "set_level" in first_calls
    assert "start_cleaning" in second_calls


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
    assert assignments["VACUUM_LEVEL_VALUES"] == {"Low": 1, "Normal": 0, "Max": 2}
    assert "select" in assignments["PLATFORMS"]
