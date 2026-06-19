# Shark Vacuum Local: Local Interface Research

Research date: 2026-06-19.

## Confirmed

- The Reference download and current `charger68/sharkiq_local_unofficial`
  integration have identical Python behavior. Upstream 0.3.x only changes the
  domain/branding and adds brand images.
- `sharkiqlibs/sharklocal` 0.2.0 adds a second REST mapping on HTTP port 8080
  and mapping priority/probing. Shark Vacuum Local deliberately retains the
  Reference integration's single configured mapping instead of auto-probing.
- The local REST routes published by `sharklocal` are `/get/status`,
  `/get/event_log`, `/get/robot_id`, `/get/wifi_status`, `/set/clean_all`,
  `/set/stop`, `/set/go_home`, and `/set/explore`.
- The local MQTT broker uses port 1883, command topic `/qfeel/PbInput`, status
  topic `/qfeel/PbOutput`, and base64-wrapped protobuf messages.
- Public Shark cloud SDKs name the property `Power_Mode` and define Normal=0,
  Eco=1, Max=2. They can read and write it through Ayla's cloud property API.

## Not confirmed

- No inspected public source defines a local REST fan-speed route.
- `sharklocal` does not decode fan speed from local REST or MQTT status.
- `sharklocal` does not contain a fan-speed MQTT command payload, and its
  schema-free decoder is insufficient to derive one safely.

The default `/set/power_mode?mode={value}` route is therefore an isolated,
editable hypothesis. A failed route produces an error and does not update the
optimistic Home Assistant value. Capturing the SharkClean app's LAN request or
obtaining the firmware's HTTP route table is needed to replace the hypothesis
with a verified command.

## Sources inspected

- <https://github.com/charger68/sharkiq_local_unofficial>
- <https://github.com/sharkiqlibs/sharklocal>
- <https://github.com/sharkiqlibs/sharkiq>
- <https://github.com/ajmarks/sharkiq>
- <https://github.com/homebridge-plugins/homebridge-sharkiq>
