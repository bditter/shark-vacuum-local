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

## Fan speed

The vacuum entity exposes Home Assistant's standard fan speed control with
`Eco`, `Normal`, and `Max`. The values are confirmed by the Shark cloud SDKs:

| Home Assistant | Shark `Power_Mode` value |
|---|---:|
| Normal | 0 |
| Eco | 1 |
| Max | 2 |

The local status payload does not expose `Power_Mode`, so fan speed is
optimistic: Home Assistant displays the last value successfully sent during the
current integration session.

The local command route is not documented publicly. This integration defaults
to `/set/power_mode?mode={value}` and deliberately makes it editable under the
integration's **Configure** dialog. The template accepts `{value}` (0, 1, 2)
and `{speed}` (`normal`, `eco`, `max`). An HTTP error is surfaced to the service
caller and logged; it is never treated as a successful setting.

## Local transport discovery

With the default `sharkiq_v1` setting, the integration asks `sharklocal>=0.2.0`
to probe both public REST mappings:

- `sharkiq_v1`: HTTPS port 443
- `sharkiq_v2`: HTTP port 8080

The higher-priority reachable mapping is used. MQTT port 1883 remains enabled
when selected in the config flow.

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
