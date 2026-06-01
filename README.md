# esphome-marantec

Decode **Marantec** garage door remote codes on an ESP32 + CC1101 — no Flipper Zero needed.

Works with Marantec remotes using the older 49-bit static code system (D302, D304,
D313, D321, D323, D382, D384, Command 131, etc.). **Not** compatible with the newer
*bi.linked* system (128-bit AES rolling code).

This is a header-only helper: drop `marantec.h` next to your ESPHome config, include
it, and call `esphome::marantec::decode()` from a `remote_receiver` `on_raw` lambda.
The decoder validates each frame against its embedded CRC-8, so a logged code is
guaranteed correct — the only failure mode is silence.

## Hardware

| Part | Notes |
|------|-------|
| ESP32 | any variant |
| CC1101 (868 MHz) | must be the 868 MHz tuned board |

### Wiring (ESP32 ↔ CC1101)

| CC1101 | ESP32 GPIO | Function |
|--------|-----------|----------|
| VCC | 3.3V | Power |
| GND | GND | Ground |
| CSN | GPIO5 | SPI chip select |
| SCK | GPIO18 | SPI clock |
| MOSI | GPIO23 | SPI data in |
| MISO | GPIO19 | SPI data out |
| GDO2 | GPIO33 | RX data line |

## Usage

1. Copy `marantec.h` into your ESPHome config directory (next to your device YAML).
2. Include it and wire up a `remote_receiver` (see `example.yaml` for a full config):

```yaml
esphome:
  name: marantec-learner
  includes:
    - marantec.h

remote_receiver:
  id: rf_rx
  pin: GPIO33                 # CC1101 GDO2
  idle: 15ms                  # above Marantec's ~10 ms inter-frame gap
  buffer_size: 6kb
  on_raw:
    then:
      - lambda: |-
          uint64_t code;
          if (esphome::marantec::decode(x, &code)) {
            ESP_LOGI("marantec", "Learned code: 0x%013llX (CRC ok)",
                     (unsigned long long) code);
          }
```

3. Flash, open the logs, and press your remote near the CC1101:

```
[I][marantec]: Learned code: 0x130CF7B95865A (CRC ok)
```

Use that hex value wherever you need the code.

## Why `idle: 15ms`?

Marantec sends a burst of repeated frames separated by a ~10 ms gap. With the default
`idle`, `remote_receiver` flushes mid-burst and splits frames across callbacks, so no
single callback holds a complete frame. Raising `idle` above the gap keeps the whole
burst together; the decoder then splits it back into frames internally and decodes the
first valid one.

## Protocol

| Parameter | Value |
|-----------|-------|
| Frequency | 868.35 MHz (EU) |
| Modulation | OOK |
| Bits | 49 (static, no rolling code), MSB first |
| Encoding | Manchester, ~1000 µs half-bit |
| CRC | CRC-8, poly 0x1D, init 0x01, over the top 6 bytes |

The decode mirrors the transmit framing: the first bit is a lone high half-bit (its
leading low is absorbed into the inter-frame gap), and the final bit's trailing half is
often truncated at capture end and inferred from its single present half.

## AI Disclaimer

This code was written in part by an AI assistant, but the decoder logic was validated
against real over-the-air captures from a physical Marantec remote (cross-checked with a
Flipper Zero). Review and use at your own discretion. No warranties.

## License

MIT
