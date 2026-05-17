# Home Assistant Hunonic

Unofficial Home Assistant custom integration for Hunonic smart-home devices.

This project is based on clean-room observation of the public Hunonic Android app traffic/API shape and is not affiliated with Hunonic.

## Status

**Alpha / read-only MVP.**

Implemented:

- Config flow login with phone/email + password.
- Cloud polling via `https://api.hunonicpro.com/v2/`.
- Device discovery from `device/listDeviceOfHomeSelect`.
- Sensor entities for temperature, humidity, battery, switch state, and AC target/power state.
- Binary door sensors.

Not implemented yet:

- Switch entities/control.
- Climate entities/control.
- Local control.
- MQTT state subscription/control.

The Hunonic app exposes MQTT topics in device metadata, but command payloads still need safe validation before write-control is enabled.

## Installation

### Manual

Copy `custom_components/hunonic` into your Home Assistant `custom_components` folder:

```bash
mkdir -p /config/custom_components
cp -R custom_components/hunonic /config/custom_components/hunonic
```

Restart Home Assistant, then add the integration:

```text
Settings → Devices & services → Add integration → Hunonic
```

### HACS custom repository

After this repository is published on GitHub:

1. HACS → Integrations → ⋮ → Custom repositories
2. Add repository URL
3. Category: Integration
4. Install `Hunonic`
5. Restart Home Assistant

## Development

Run basic syntax validation:

```bash
python3 -m compileall custom_components/hunonic
python3 -m json.tool custom_components/hunonic/manifest.json >/dev/null
python3 -m json.tool custom_components/hunonic/strings.json >/dev/null
```

## Security notes

- The integration stores the Hunonic token in Home Assistant's config entry.
- The password is only used during setup and is not stored.
- This is a cloud integration; traffic goes through Hunonic's API/MQTT infrastructure.

## Reverse-engineered API notes

Observed endpoints:

- `POST /v2/user/login`
- `GET /v2/user/getFullProfile`
- `GET /v2/device/listDeviceOfHomeSelect`

The Android app hashes the password with MD5 before login and signs requests with app constants present in the public APK. Those constants are included here solely for interoperability.

## Contributing

Useful test reports:

- Device type/root_type/name/value JSON.
- Whether entity state matches the Hunonic app.
- MQTT command payload captures for safe switch/AC control validation.

Please redact tokens, phone numbers, exact addresses, and MQTT credentials before posting logs.
