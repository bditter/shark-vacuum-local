# Shark Vacuum Local

An unofficial Home Assistant integration for direct local control of compatible
Shark robot vacuums over LAN REST and MQTT interfaces.

Repository: <https://github.com/bditter/shark-vacuum-local>

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
