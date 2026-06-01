#pragma once

// Marantec 49-bit static-code OOK decoder for ESPHome.
//
// Decodes raw remote_receiver timings (signed microseconds, mark/space
// alternating) into the 49-bit Marantec code, validated by its embedded
// CRC-8 (polynomial 0x1D, init 0x01). Returns the code only on a CRC match,
// so false positives are effectively impossible; the failure mode is silence.
//
// Usage (from a remote_receiver on_raw lambda):
//
//   uint64_t code;
//   if (esphome::marantec::decode(x, &code))
//     ESP_LOGI("marantec", "Learned: 0x%013llX", (unsigned long long) code);
//
// The decode mirrors the Marantec transmit framing:
//   * 49 bits, MSB first, Manchester-coded over OOK.
//   * Bit 1 = low half then high half; bit 0 = high half then low half.
//   * The first bit is carried as a lone high half-bit (its leading low half
//     is absorbed into the inter-frame gap).
//   * The final bit's trailing half is frequently truncated at the end of a
//     capture and is inferred from its single present half.
//   * Frames within a multi-frame burst are separated by a long (~10 ms) gap,
//     which appears as an out-of-spec pulse; the decoder splits on these and
//     decodes each frame independently, returning the first valid one.
//
// Validated against real over-the-air captures from a Marantec remote.

#include <cstdint>
#include <vector>

namespace esphome {
namespace marantec {

static const uint32_t TE = 1000;   // base half-bit duration (us)
static const uint32_t TOL = 450;   // matching tolerance (us)
static const int NBITS = 49;

// Classify a raw timing: 1 = short (one half-bit), 2 = long (two half-bits of
// the same polarity), 0 = out of spec (gap / noise / frame boundary).
inline int classify(int32_t v) {
  uint32_t a = v < 0 ? static_cast<uint32_t>(-v) : static_cast<uint32_t>(v);
  if (a > TE - TOL && a < TE + TOL) return 1;
  if (a > 2 * TE - TOL && a < 2 * TE + TOL) return 2;
  return 0;
}

// CRC-8 over the top six bytes of the 49-bit code (poly 0x1D, init 0x01).
inline uint8_t crc8(uint64_t code) {
  uint8_t crc = 0x01;
  for (int s = 48; s >= 8; s -= 8) {
    crc ^= static_cast<uint8_t>((code >> s) & 0xFF);
    for (int j = 0; j < 8; j++)
      crc = (crc & 0x80) ? static_cast<uint8_t>((crc << 1) ^ 0x1D)
                         : static_cast<uint8_t>(crc << 1);
  }
  return crc;
}

// Decode one run of in-spec half-bits into a CRC-valid code, or return false.
inline bool decode_run(const bool *hb, int n, uint64_t *out) {
  for (int lone = 1; lone >= 0; lone--) {
    uint64_t code = 0;
    int p = 0;
    bool ok = true;
    for (int idx = 0; idx < NBITS; idx++) {
      int bit;
      if (idx == 0 && lone == 1) {
        if (p >= n || hb[p] != true) { ok = false; break; }
        bit = 1; p++;
      } else if (p + 1 >= n) {
        if (p >= n) { ok = false; break; }
        bit = (hb[p] == false) ? 1 : 0;  // lone trailing half-bit
        p++;
      } else {
        bool a = hb[p], b = hb[p + 1];
        p += 2;
        if (!a && b) bit = 1;
        else if (a && !b) bit = 0;
        else { ok = false; break; }
      }
      code = (code << 1) | static_cast<uint64_t>(bit);
    }
    if (ok && (code & 0xFF) == crc8(code)) {
      *out = code;
      return true;
    }
  }
  return false;
}

// Decode a full remote_receiver raw buffer. Splits into frames at out-of-spec
// gaps and returns the first CRC-valid frame found. Returns true on success.
inline bool decode(const std::vector<int32_t> &timings, uint64_t *out) {
  static const int MAX_HB = 210;
  bool hb[MAX_HB];
  int n = 0;
  const size_t len = timings.size();
  for (size_t i = 0; i <= len; i++) {
    int c = (i < len) ? classify(timings[i]) : 0;  // force flush at end
    if (c == 0) {
      if (n > 0) {
        if (decode_run(hb, n, out)) return true;
        n = 0;
      }
    } else {
      bool level = timings[i] > 0;
      if (c == 1 && n < MAX_HB - 1) {
        hb[n++] = level;
      } else if (c == 2 && n < MAX_HB - 2) {
        hb[n++] = level;
        hb[n++] = level;
      }
    }
  }
  return false;
}

}  // namespace marantec
}  // namespace esphome
