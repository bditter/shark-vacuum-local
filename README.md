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

## Vacuum level

Each vacuum has a **Vacuum level** select entity with `Low`, `Normal`, and
`Max`. The local interface cannot report the current level, so the selector is
optimistic and resets to `Normal` whenever the integration entry is loaded.
The selected level is sent immediately before every start command.

The values are confirmed by the Shark cloud SDKs; the app's `Low` label maps to
the SDK's `Eco` value:

| Home Assistant | Shark `Power_Mode` value |
|---|---:|
| Normal | 0 |
| Low | 1 |
| Max | 2 |

The local command route is not documented publicly. This integration defaults
to `/set/power_mode?mode={value}` and deliberately makes it editable under the
integration's **Configure** dialog. The template accepts `{value}` (0, 1, 2)
and `{speed}` (`normal`, `low`, `max`). If a level command fails, the failure is
logged but the cleaning start command is still sent.

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
