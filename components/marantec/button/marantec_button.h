#pragma once

#include "esphome/core/component.h"
#include "esphome/components/button/button.h"
#include "esphome/components/remote_transmitter/remote_transmitter.h"

namespace esphome {
namespace marantec {

/// Marantec 868/433 MHz static 49-bit garage door protocol.
///
/// Encoding (OOK / PWM):
///   te  = 802 us   (one time element)
///   Bit "1":  HIGH 3xte,  LOW 1xte   (2406 us / 802 us)
///   Bit "0":  HIGH 1xte,  LOW 3xte   ( 802 us / 2406 us)
///   Sync:     HIGH 1xte,  LOW 16xte  ( 802 us / 12832 us)
///
/// Frame is sent MSB-first, repeated N times.

class MarantecButton : public button::Button, public Component {
 public:
  void set_transmitter(remote_transmitter::RemoteTransmitterComponent *transmitter) {
    this->transmitter_ = transmitter;
  }
  void set_code(uint64_t code) { this->code_ = code; }
  void set_repeat(int repeat) { this->repeat_ = repeat; }

  void dump_config() override;

 protected:
  void press_action() override;

  /// Build one complete Marantec frame (sync + 49 data bits) into raw us codes.
  void encode_frame_(std::vector<int32_t> &raw);

  remote_transmitter::RemoteTransmitterComponent *transmitter_{nullptr};
  uint64_t code_{0};
  int repeat_{4};

  static constexpr int32_t TE = 802;           // us - one time element
  static constexpr int      NUM_BITS = 49;     // data bits per frame
};

}  // namespace marantec
}  // namespace esphome
