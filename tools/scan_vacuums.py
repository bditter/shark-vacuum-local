"""Scan a local subnet for Shark vacuums.

This is a helper for finding candidate IP addresses. It only attempts TCP
connects and read-only sharklocal status calls; it does not publish commands.
"""
from __future__ import annotations

import argparse
import asyncio
import ipaddress
import json
import socket
from dataclasses import asdict, dataclass
from typing import Iterable

from sharklocal import SharklocalError, VacuumClient


DEFAULT_TIMEOUT = 1.5
DEFAULT_MAPPING = "sharkiq_v1"


@dataclass
class Candidate:
    host: str
    mqtt_1883: bool
    https_443: bool
    status_ok: bool
    mac_address: str | None = None
    ssid: str | None = None
    error: str | None = None


def _default_networks() -> list[ipaddress.IPv4Network]:
    """Infer likely /24 networks from the machine's active outbound IP."""
    networks: list[ipaddress.IPv4Network] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            local_ip = ipaddress.ip_address(sock.getsockname()[0])
    except OSError:
        return networks

    if isinstance(local_ip, ipaddress.IPv4Address) and not local_ip.is_loopback:
        network = ipaddress.ip_network(f"{local_ip}/24", strict=False)
        networks.append(network)
    return networks


async def _port_open(host: str, port: int, timeout: float) -> bool:
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout,
        )
    except OSError:
        return False
    except asyncio.TimeoutError:
        return False

    writer.close()
    await writer.wait_closed()
    # Silence linters: reader is intentionally created by open_connection.
    _ = reader
    return True


async def _read_status(
    host: str, mapping: str, use_mqtt: bool
) -> tuple[bool, str | None, str | None, str | None]:
    client = VacuumClient(
        host,
        rest_mappings=mapping,
        mqtt_mappings=mapping if use_mqtt else None,
    )
    try:
        async with client:
            await client.get_status()
            try:
                wifi = await client.get_wifi_status()
            except SharklocalError:
                wifi = None
            return (
                True,
                getattr(wifi, "mac_address", None),
                getattr(wifi, "ssid", None),
                None,
            )
    except Exception as err:  # noqa: BLE001
        return False, None, None, f"{type(err).__name__}: {err}"


async def _check_host(
    host: str, mapping: str, timeout: float, verify_status: bool
) -> Candidate | None:
    mqtt_open, https_open = await asyncio.gather(
        _port_open(host, 1883, timeout),
        _port_open(host, 443, timeout),
    )
    if not mqtt_open and not https_open:
        return None

    candidate = Candidate(
        host=host,
        mqtt_1883=mqtt_open,
        https_443=https_open,
        status_ok=False,
    )
    if verify_status:
        status_ok, mac_address, ssid, error = await _read_status(
            host, mapping, mqtt_open
        )
        candidate.status_ok = status_ok
        candidate.mac_address = mac_address
        candidate.ssid = ssid
        candidate.error = error
    return candidate


def _hosts(networks: Iterable[ipaddress.IPv4Network]) -> list[str]:
    return [str(host) for network in networks for host in network.hosts()]


async def _scan(args: argparse.Namespace) -> list[Candidate]:
    networks = [
        ipaddress.ip_network(network, strict=False) for network in args.network
    ]
    if not networks:
        networks = _default_networks()
    if not networks:
        raise SystemExit("No network supplied and no local /24 could be inferred.")

    semaphore = asyncio.Semaphore(args.concurrency)

    async def limited(host: str) -> Candidate | None:
        async with semaphore:
            return await _check_host(
                host,
                args.mapping,
                args.timeout,
                not args.skip_status,
            )

    results = await asyncio.gather(*(limited(host) for host in _hosts(networks)))
    return sorted(
        (candidate for candidate in results if candidate is not None),
        key=lambda candidate: ipaddress.ip_address(candidate.host),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "network",
        nargs="*",
        help="CIDR network(s) to scan, for example 10.0.0.0/24",
    )
    parser.add_argument("--mapping", default=DEFAULT_MAPPING)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--concurrency", type=int, default=64)
    parser.add_argument(
        "--skip-status",
        action="store_true",
        help="Only check open ports; do not call sharklocal get_status.",
    )
    args = parser.parse_args()

    candidates = asyncio.run(_scan(args))
    print(json.dumps([asdict(candidate) for candidate in candidates], indent=2))


if __name__ == "__main__":
    main()
