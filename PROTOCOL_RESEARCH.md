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
- Captured and hardware-verified fan/start payloads are Eco
  `OgQKAhAygAEJ`, Normal `OgQKAhBLgAEJ`, and Max `OgQKAhBkgAEJ`.
- The local fan values are 50, 75, and 100. The Normal payload is also the
  existing `sharklocal` start-cleaning command.
- Captured settings use an outer protobuf field 7 with nested fields 8
  (Recharge and Resume), 7 (Save Power Level), 13 (Evacuate and Resume), and
  2 (Notification Volume, 0-100).

## Not confirmed

- The vacuum does not report fan speed or the captured preferences in its
  decoded local status, so Home Assistant state is optimistic.
- Extended Clean and Do Not Disturb did not produce distinguishable commands
  in the supplied capture. They remain unavailable pending a focused capture.

## Sources inspected

- <https://github.com/charger68/sharkiq_local_unofficial>
- <https://github.com/sharkiqlibs/sharklocal>
- <https://github.com/sharkiqlibs/sharkiq>
- <https://github.com/ajmarks/sharkiq>
- <https://github.com/homebridge-plugins/homebridge-sharkiq>
