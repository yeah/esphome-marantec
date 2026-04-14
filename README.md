# esphome-marantec

ESPHome external component for **Marantec** garage door remotes (868.35 / 433.92 MHz, 49-bit static protocol).

Works with all Marantec remotes that use the older static code system (D302, D304, D313, D321, D323, D382, D384, Command 131, etc.). **Not** compatible with the newer *bi.linked* system (128-bit AES rolling code).

## Hardware

| Part | Notes |
|------|-------|
| ESP32 (any variant) | ESP32-DevKit, ESP32-S3 Super Mini, etc. |
| CC1101 module (868 MHz) | Must be the 868 MHz tuned version! |

### Wiring (ESP32 ↔ CC1101)

| CC1101 Pin | ESP32 GPIO | Function |
|-----------|-----------|----------|
| VCC | 3.3V | Power |
| GND | GND | Ground |
| CSN | GPIO5 | SPI Chip Select |
| SCK | GPIO18 | SPI Clock |
| MOSI | GPIO23 | SPI Data In |
| MISO | GPIO19 | SPI Data Out |
| GDO0 | GPIO22 | TX data line |
| GDO2 | GPIO21 | RX data line (optional) |

> **Tip:** GPIOs are flexible – adjust to your board. The example uses the default VSPI pins.

## Finding your Marantec code

### Option A: Flipper Zero (recommended)

1. Sub-GHz → Read → Frequency 868.35 MHz, Modulation AM650
2. Press your Marantec remote
3. Flipper decodes e.g.: `Protocol: Marantec  Key: 0x1AABBCCDDEE01`
4. Copy that hex value into `code:` in your YAML

### Option B: ESPHome remote_receiver

Enable the `remote_receiver` section in the example YAML, flash, and check the log output while pressing your remote. You'll see raw pulse timings that can be decoded.

## Installation

Add to your ESPHome YAML:

```yaml
external_components:
  - source:
      type: git
      url: https://github.com/yeah/esphome-marantec
    components: [marantec]
```

## Configuration

```yaml
button:
  - platform: marantec
    name: "Garage Door"
    transmitter_id: rf_tx
    code: 0x1AABBCCDDEE01   # your 49-bit code in hex
    repeat: 4                # optional, default 4
```

| Key | Required | Default | Description |
|-----|----------|---------|-------------|
| `transmitter_id` | yes | – | ID of the `remote_transmitter` |
| `code` | yes | – | 49-bit Marantec code as hex (from Flipper or receiver) |
| `repeat` | no | 4 | Number of frame repetitions (1–20) |

See `example.yaml` for a complete working configuration.

## Protocol Details

| Parameter | Value |
|-----------|-------|
| Frequency | 868.35 MHz (EU) / 433.92 MHz |
| Modulation | OOK / ASK |
| Bits | 49 (static, no rolling code) |
| te (time element) | 802 µs |
| Bit "1" | HIGH 2406 µs, LOW 802 µs |
| Bit "0" | HIGH 802 µs, LOW 2406 µs |
| Sync | HIGH 802 µs, LOW 12832 µs |
| Bit order | MSB first |

## Home Assistant

After flashing, the button entity appears in Home Assistant automatically. You can use it in automations, dashboards, or scripts.

For a `cover` entity (open/close/stop), wrap the button in a [template cover](https://esphome.io/components/cover/template.html).

## Troubleshooting

- **No response from gate:** Double-check that your CC1101 module is the 868 MHz version (not 433 MHz). The chip works on both frequencies but the board's matching network is frequency-specific.
- **SPI errors (FF0F / 0000):** Check wiring, especially MISO/MOSI and CS pin.
- **Flipper works but ESP doesn't:** Increase `repeat:` to 6–8. Also verify the exact frequency — some Marantec systems use 868.3 instead of 868.35 MHz.

## License

MIT
