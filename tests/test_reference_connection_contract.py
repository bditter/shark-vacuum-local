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
