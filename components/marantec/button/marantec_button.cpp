#include "marantec_button.h"
#include "esphome/core/log.h"

namespace esphome {
namespace marantec {

static const char *const TAG = "marantec.button";

void MarantecButton::dump_config() {
  LOG_BUTTON("", "Marantec Button", this);
  ESP_LOGCONFIG(TAG, "  Code: 0x%013llX (%d bits)", (unsigned long long) this->code_, NUM_BITS);
  ESP_LOGCONFIG(TAG, "  Repeat: %d", this->repeat_);
}

void MarantecButton::encode_frame_(std::vector<int32_t> &raw) {
  // --- Sync / preamble: SHORT pulse, LONG gap ---
  raw.push_back(TE);          //  802 us  HIGH
  raw.push_back(-(TE * 16));  // 12832 us LOW

  // --- 49 data bits, MSB first ---
  for (int i = NUM_BITS - 1; i >= 0; i--) {
    bool bit = (this->code_ >> i) & 1;
    if (bit) {
      // "1" -> long pulse, short gap
      raw.push_back(TE * 3);   // 2406 us HIGH
      raw.push_back(-TE);      //  802 us LOW
    } else {
      // "0" -> short pulse, long gap
      raw.push_back(TE);       //  802 us HIGH
      raw.push_back(-(TE * 3));// 2406 us LOW
    }
  }
}

void MarantecButton::press_action() {
  ESP_LOGI(TAG, "Sending Marantec code 0x%013llX (%dx)", (unsigned long long) this->code_, this->repeat_);

  auto call = this->transmitter_->transmit();
  auto *data = call.get_data();

  // Encode N repetitions into one raw buffer.
  // Between repetitions the last LOW of the frame and the sync gap
  // of the next frame merge naturally, providing enough dead time.
  std::vector<int32_t> raw;
  raw.reserve((2 + NUM_BITS * 2) * this->repeat_);

  for (int r = 0; r < this->repeat_; r++) {
    this->encode_frame_(raw);
  }

  // Feed the raw pulse/gap pairs into remote_transmitter
  for (auto v : raw) {
    if (v > 0)
      data->mark(v);
    else
      data->space(-v);
  }

  // Ensure the frame ends LOW so the transmitter goes idle
  data->space(0);

  call.set_send_times(1);   // we handle repetition ourselves
  call.set_send_wait(0);
  call.perform();
}

}  // namespace marantec
}  // namespace esphome
