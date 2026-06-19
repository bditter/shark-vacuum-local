#!/usr/bin/env python3
"""Inspect the known Shark local REST interfaces without changing the vacuum."""
from __future__ import annotations

import argparse
import json
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


READ_ONLY_PATHS = (
    "/",
    "/get/status",
    "/get/robot_id",
    "/get/wifi_status",
    "/get/event_log",
)
FAN_VALUES = {"normal": 0, "eco": 1, "max": 2}


def request(url: str) -> dict[str, Any]:
    """Return status, headers, and a bounded response body."""
    req = Request(url, headers={"User-Agent": "shark-local-probe/1.0"})
    context = ssl._create_unverified_context() if url.startswith("https:") else None
    try:
        with urlopen(req, timeout=5, context=context) as response:
            body = response.read(65536).decode("utf-8", errors="replace")
            return {
                "status": response.status,
                "content_type": response.headers.get("Content-Type"),
                "server": response.headers.get("Server"),
                "body": body,
            }
    except HTTPError as err:
        return {
            "status": err.code,
            "content_type": err.headers.get("Content-Type"),
            "server": err.headers.get("Server"),
            "body": err.read(65536).decode("utf-8", errors="replace"),
        }
    except (URLError, TimeoutError, OSError) as err:
        return {"error": str(err)}


def main() -> None:
    """Probe both published REST mappings and print a JSON report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", help="Vacuum IP address or hostname")
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        help="Additional read-only path to request (repeatable)",
    )
    parser.add_argument(
        "--set-fan",
        choices=FAN_VALUES,
        help="Explicitly test the experimental fan route (changes the vacuum)",
    )
    parser.add_argument(
        "--fan-path",
        default="/set/power_mode?mode={value}",
        help="Fan path template; accepts {value} and {speed}",
    )
    args = parser.parse_args()

    bases = (f"https://{args.host}:443", f"http://{args.host}:8080")
    paths = list(dict.fromkeys((*READ_ONLY_PATHS, *args.path)))
    report: dict[str, Any] = {"host": args.host, "interfaces": {}}

    for base in bases:
        report["interfaces"][base] = {
            path: request(f"{base}{path}") for path in paths
        }

    if args.set_fan:
        path = args.fan_path.format(
            value=FAN_VALUES[args.set_fan], speed=args.set_fan
        )
        if not path.startswith("/") or path.startswith("//"):
            parser.error("--fan-path must begin with one slash")
        report["fan_test"] = {
            base: request(f"{base}{path}") for base in bases
        }

    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
