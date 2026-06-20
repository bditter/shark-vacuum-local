# Shark Vacuum Local

<p align="center">
  <img src="custom_components/shark_vacuum_local/brand/logo@2x.png"
       alt="Shark Vacuum Local"
       width="256">
</p>

[![GitHub Release](https://img.shields.io/github/v/release/bditter/shark-vacuum-local?style=for-the-badge)](https://github.com/bditter/shark-vacuum-local/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5?style=for-the-badge&logo=home-assistant-community-store)](https://hacs.xyz/docs/faq/custom_repositories/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-18BCF2?style=for-the-badge&logo=home-assistant&logoColor=white)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/github/license/bditter/shark-vacuum-local?style=for-the-badge)](LICENSE)

[![GitHub Stars](https://img.shields.io/github/stars/bditter/shark-vacuum-local?style=flat-square)](https://github.com/bditter/shark-vacuum-local/stargazers)
[![GitHub Issues](https://img.shields.io/github/issues/bditter/shark-vacuum-local?style=flat-square)](https://github.com/bditter/shark-vacuum-local/issues)
[![Last Commit](https://img.shields.io/github/last-commit/bditter/shark-vacuum-local?style=flat-square)](https://github.com/bditter/shark-vacuum-local/commits/main)

An unofficial Home Assistant integration for direct local control of compatible
Shark robot vacuums over LAN REST and MQTT interfaces.

## Installation

Copy `custom_components/shark_vacuum_local` into the same directory under your
Home Assistant configuration, restart Home Assistant, and add
**Shark Vacuum Local**
from Devices & Services.

To change a vacuum's IP address later, open its integration entry menu and
select **Reconfigure**. The current address is prefilled and the new address is
tested before the entry is updated and reloaded.

Entity IDs use the configured vacuum name and entity name only. Assigned Home
Assistant areas are deliberately excluded; for example, a vacuum named
`Rosey` produces `select.rosey_vacuum_level` even when assigned to Hallway.

## Vacuum level

Each vacuum has a **Vacuum level** select entity with `Eco`, `Normal`, and
`Max`. The local interface cannot report the current level, so the selector is
optimistic and resets to `Normal` whenever the integration entry is loaded.
The selected level is included in every start/resume command. Changing the
selector while the vacuum is cleaning applies the new fan level immediately.

The commands were captured from the official app and verified against a local
vacuum:

| Home Assistant | Local fan value | MQTT payload |
|---|---:|---|
| Eco | 50 | `OgQKAhAygAEJ` |
| Normal | 75 | `OgQKAhBLgAEJ` |
| Max | 100 | `OgQKAhBkgAEJ` |

These write-only local MQTT commands do not expose the current level, so the
select remains optimistic and defaults to Normal after an integration reload.

## Local preferences

The capture also confirmed optimistic controls for **Recharge and resume**,
**Evacuate and resume**, **Save power level**, and **Notification volume**.
Their current values cannot be queried from the local status response, so they
default to off and 50 percent after a reload. Extended Clean and Do Not Disturb
did not produce distinguishable local commands in the supplied capture and are
not exposed yet.

## Local transports

The default `sharkiq_v1` setting follows the downloaded Reference integration's
connection behavior exactly:

- REST uses the configured mapping on HTTPS port 443.
- MQTT uses the same configured mapping on port 1883 when enabled.
- REST is attempted first and MQTT is the library fallback when REST cannot
  connect.

See [PROTOCOL_RESEARCH.md](PROTOCOL_RESEARCH.md) for findings and limitations.

## Interface probe

Run the bundled read-only probe from another machine on the vacuum's LAN:

```powershell
python .\tools\shark_local_probe.py 192.168.1.100 > shark-report.json
```

It checks the known read endpoints over HTTPS/443 and HTTP/8080. It does not
send a command unless `--set-fan eco|normal|max` is explicitly supplied. Use
`--path /another/read/path` to inspect an additional route.

Home Assistant also exposes a **Download diagnostics** action for the config
entry. It includes the selected REST/MQTT mappings and raw status structure,
with host, IP, MAC, and SSID fields redacted.

### Vacuum-level protocol capture

The guided research tool records local REST v1 (HTTPS/443), REST v2
(HTTP/8080), and MQTT status at each app level and reports which raw fields
changed:

```powershell
py -m venv .capture-venv
.\.capture-venv\Scripts\python -m pip install sharklocal==0.2.0
.\.capture-venv\Scripts\python .\tools\capture_vacuum_levels.py 192.168.1.100
```

Start a normal cleaning run first. The tool waits until local MQTT reports
`cleaning`. For each prompt, select Eco, Normal, or Max in the official Shark
app, wait five seconds, and press Enter. The generated
`vacuum-levels-<IP>.json` file contains
the complete samples and a field-by-field comparison. Run it separately for
each vacuum because models or firmware may encode the levels differently.
