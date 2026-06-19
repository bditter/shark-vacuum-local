#!/usr/bin/env python3
"""Capture and compare local Shark status fields at each vacuum level."""
from __future__ import annotations

import argparse
import asyncio
from collections.abc import Mapping
from enum import Enum
import json
from pathlib import Path
import sys
from typing import Any

from sharklocal import (
    MQTTVacuumClient,
    RESTVacuumClient,
    load_mqtt_mapping,
    load_rest_mapping,
)


LEVELS = ("Low", "Normal", "Max")


def _json_safe(value: Any) -> Any:
    """Convert protobuf bytes, enums, and integer keys to JSON-safe values."""
    if isinstance(value, bytes):
        return {"hex": value.hex(), "length": len(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten nested status fields into dotted paths for comparison."""
    if isinstance(value, dict):
        flattened: dict[str, Any] = {}
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(_flatten(item, path))
        return flattened
    if isinstance(value, list):
        flattened = {}
        for index, item in enumerate(value):
            path = f"{prefix}[{index}]"
            flattened.update(_flatten(item, path))
        return flattened
    return {prefix: value}


def _changed_fields(captures: dict[str, Any], transport: str) -> dict[str, Any]:
    """Return fields whose values differ across captured levels."""
    by_level = {
        level: _flatten(sample[transport]["raw"])
        for level, sample in captures.items()
        if "raw" in sample.get(transport, {})
    }
    paths = sorted({path for fields in by_level.values() for path in fields})
    changed: dict[str, Any] = {}
    for path in paths:
        values = {level: fields.get(path) for level, fields in by_level.items()}
        serialized = {json.dumps(value, sort_keys=True) for value in values.values()}
        if len(serialized) > 1:
            changed[path] = values
    return changed


async def _capture_rest(client: RESTVacuumClient) -> dict[str, Any]:
    """Capture one REST status sample."""
    try:
        status = await client.call("get_status")
    except Exception as err:  # noqa: BLE001 - preserve research failures
        return {"error": f"{type(err).__name__}: {err}"}
    return {
        "mode": status.mode,
        "battery_level": status.battery_level,
        "charging": status.charging,
        "raw": status.raw,
    }


async def _capture_mqtt(client: MQTTVacuumClient) -> dict[str, Any]:
    """Capture one local MQTT protobuf status sample."""
    try:
        status = await client.call("get_status")
    except Exception as err:  # noqa: BLE001 - preserve research failures
        return {"error": f"{type(err).__name__}: {err}"}
    return {
        "mode": status.mode,
        "battery_level": status.battery_level,
        "charging": status.charging,
        "raw": status.raw,
    }


async def capture(host: str, output: Path) -> None:
    """Guide the user through three app settings and save comparison data."""
    rest_clients = {
        "rest_v1": RESTVacuumClient(host, load_rest_mapping("sharkiq_v1")),
        "rest_v2": RESTVacuumClient(host, load_rest_mapping("sharkiq_v2")),
    }
    mqtt = MQTTVacuumClient(host, load_mqtt_mapping("sharkiq_v1"))
    captures: dict[str, Any] = {}

    print(f"Vacuum: {host}")
    print("This tool sends status requests only; it does not start the vacuum.")
    print("Keep the vacuum in the same operating state for all three captures.\n")

    try:
        for level in LEVELS:
            await asyncio.to_thread(
                input,
                f"Set the vacuum to {level} in the Shark app, wait 5 seconds, "
                "then press Enter... ",
            )
            captures[level] = {"mqtt": await _capture_mqtt(mqtt)}
            for name, client in rest_clients.items():
                captures[level][name] = await _capture_rest(client)
            errors = {
                name: result["error"]
                for name, result in captures[level].items()
                if "error" in result
            }
            if errors:
                print(f"Captured {level} with transport errors: {errors}")
            else:
                print(f"Captured {level}.")
    finally:
        for client in rest_clients.values():
            await client.close()

    safe_captures = _json_safe(captures)
    report = {
        "host": host,
        "instructions": "Low, Normal, and Max selected in official Shark app",
        "captures": safe_captures,
        "changed_fields": {
            "mqtt": _changed_fields(safe_captures, "mqtt"),
            "rest_v1": _changed_fields(safe_captures, "rest_v1"),
            "rest_v2": _changed_fields(safe_captures, "rest_v2"),
        },
    }
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    print(f"\nReport saved to {output.resolve()}")
    print("Fields that changed:")
    print(json.dumps(report["changed_fields"], indent=2, sort_keys=True))


def main() -> None:
    """Parse arguments and run the guided capture."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", help="Vacuum IP address")
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON path (default: vacuum-levels-<host>.json)",
    )
    args = parser.parse_args()
    output = args.output or Path(f"vacuum-levels-{args.host}.json")
    if sys.platform == "win32":
        # aiomqtt uses add_reader/add_writer, which the default Windows
        # ProactorEventLoop does not implement.
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(capture(args.host, output))


if __name__ == "__main__":
    main()
