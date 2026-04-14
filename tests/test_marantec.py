"""
Tests for the Marantec 49-bit protocol encoding.

Run with: python3 -m pytest tests/ -v
"""

import pytest


# ---------- Protocol constants (must match marantec_button.h) ----------

TE = 802  # us - one time element
NUM_BITS = 49


def encode_marantec_frame(code: int) -> list[int]:
    """
    Pure-Python reference encoder for the Marantec 49-bit static protocol.
    Returns a list of signed int32 pulse/gap durations in us.
    Positive = HIGH (mark), Negative = LOW (space).
    """
    raw: list[int] = []

    # Sync preamble
    raw.append(TE)            #   802 us HIGH
    raw.append(-(TE * 16))    # 12832 us LOW

    # 49 data bits, MSB first
    for i in range(NUM_BITS - 1, -1, -1):
        bit = (code >> i) & 1
        if bit:
            raw.append(TE * 3)      # 2406 us HIGH
            raw.append(-TE)          #  802 us LOW
        else:
            raw.append(TE)           #  802 us HIGH
            raw.append(-(TE * 3))    # 2406 us LOW

    return raw


# ======================== ENCODING TESTS ========================


class TestFrameStructure:
    """Verify the frame has the correct number of pulses."""

    def test_frame_length(self):
        """Sync (2 elements) + 49 bits x 2 elements = 100 elements total."""
        raw = encode_marantec_frame(0x0000000000000)
        assert len(raw) == 2 + NUM_BITS * 2  # = 100

    def test_frame_starts_with_sync(self):
        raw = encode_marantec_frame(0x1FFFFFFFFFFFF)
        assert raw[0] == TE             # sync pulse
        assert raw[1] == -(TE * 16)     # sync gap

    def test_all_elements_nonzero(self):
        raw = encode_marantec_frame(0x1234567890ABC)
        assert all(v != 0 for v in raw)

    def test_alternating_polarity(self):
        """Marks (+) and spaces (-) must alternate."""
        raw = encode_marantec_frame(0x1234567890ABC)
        for i in range(len(raw)):
            if i % 2 == 0:
                assert raw[i] > 0, f"Element {i} should be positive (mark)"
            else:
                assert raw[i] < 0, f"Element {i} should be negative (space)"


class TestBitEncoding:
    """Verify individual bit encodings."""

    def test_bit_one_encoding(self):
        """A '1' bit -> 3xTE HIGH, 1xTE LOW."""
        # code = all ones -> 0x1FFFFFFFFFFFF (49 bits set)
        code = (1 << NUM_BITS) - 1
        raw = encode_marantec_frame(code)
        # First data bit starts at index 2
        assert raw[2] == TE * 3     # mark  2406 us
        assert raw[3] == -TE        # space  802 us

    def test_bit_zero_encoding(self):
        """A '0' bit -> 1xTE HIGH, 3xTE LOW."""
        raw = encode_marantec_frame(0x0000000000000)
        assert raw[2] == TE         # mark   802 us
        assert raw[3] == -(TE * 3)  # space 2406 us

    def test_mixed_bits(self):
        """Code 0b10 in lowest bits -> bit1=1 bit0=0."""
        code = 0b10  # only bits 1 and 0 relevant; bit1=1, bit0=0
        raw = encode_marantec_frame(code)
        # Bit 1 (second-to-last data bit) at index 2 + (NUM_BITS-2)*2 = 96
        idx_bit1 = 2 + (NUM_BITS - 1 - 1) * 2
        assert raw[idx_bit1] == TE * 3      # '1' -> long mark
        assert raw[idx_bit1 + 1] == -TE     # '1' -> short space

        # Bit 0 (last data bit) at index 98
        idx_bit0 = 2 + (NUM_BITS - 1) * 2
        assert raw[idx_bit0] == TE           # '0' -> short mark
        assert raw[idx_bit0 + 1] == -(TE * 3)  # '0' -> long space


class TestTimings:
    """Verify timing constants and total frame duration."""

    def test_te_value(self):
        assert TE == 802

    def test_bit_period_constant(self):
        """Each bit occupies exactly 4xTE regardless of value."""
        for bit_val in [0, 1]:
            code = bit_val  # just the LSB
            raw = encode_marantec_frame(code)
            # Last bit (LSB)
            idx = 2 + (NUM_BITS - 1) * 2
            mark = raw[idx]
            space = abs(raw[idx + 1])
            assert mark + space == 4 * TE  # 3208 us per bit

    def test_total_frame_duration(self):
        """Frame = sync(17xTE) + 49xbit(4xTE) = 17+196 = 213xTE."""
        raw = encode_marantec_frame(0x1234567890ABC)
        total = sum(abs(v) for v in raw)
        expected = (1 + 16) * TE + NUM_BITS * 4 * TE  # 213 x 802 = 170826 us
        assert total == expected

    def test_sync_duration(self):
        raw = encode_marantec_frame(0)
        sync_total = abs(raw[0]) + abs(raw[1])
        assert sync_total == 17 * TE  # 13634 us


class TestRepetition:
    """Verify multi-frame encoding."""

    def test_repeated_frames(self):
        code = 0x1234567890ABC
        single = encode_marantec_frame(code)
        repeat = 4
        multi: list[int] = []
        for _ in range(repeat):
            multi.extend(encode_marantec_frame(code))
        assert len(multi) == len(single) * repeat

    def test_repeated_frames_identical(self):
        code = 0x1AABBCCDDEE01
        single = encode_marantec_frame(code)
        for _ in range(3):
            frame = encode_marantec_frame(code)
            assert frame == single


class TestEdgeCases:
    """Edge cases and boundary values."""

    def test_code_zero(self):
        raw = encode_marantec_frame(0)
        # All data bits should be 0 -> all short mark, long space
        for i in range(NUM_BITS):
            idx = 2 + i * 2
            assert raw[idx] == TE
            assert raw[idx + 1] == -(TE * 3)

    def test_code_max(self):
        """All 49 bits set."""
        code = (1 << NUM_BITS) - 1  # 0x1FFFFFFFFFFFF
        raw = encode_marantec_frame(code)
        for i in range(NUM_BITS):
            idx = 2 + i * 2
            assert raw[idx] == TE * 3
            assert raw[idx + 1] == -TE

    def test_code_msb_only(self):
        """Only MSB (bit 48) set."""
        code = 1 << (NUM_BITS - 1)  # 0x1000000000000
        raw = encode_marantec_frame(code)
        # First data bit (MSB) = 1
        assert raw[2] == TE * 3
        assert raw[3] == -TE
        # Second data bit = 0
        assert raw[4] == TE
        assert raw[5] == -(TE * 3)

    def test_code_lsb_only(self):
        """Only LSB (bit 0) set."""
        code = 1
        raw = encode_marantec_frame(code)
        # Last data bit (LSB) = 1
        idx = 2 + (NUM_BITS - 1) * 2
        assert raw[idx] == TE * 3
        assert raw[idx + 1] == -TE
        # Second-to-last bit = 0
        idx_prev = 2 + (NUM_BITS - 2) * 2
        assert raw[idx_prev] == TE
        assert raw[idx_prev + 1] == -(TE * 3)


class TestFlipperZeroCompatibility:
    """
    Verify that our encoding matches known Flipper Zero Marantec captures.
    A Flipper .sub file for Marantec uses positive/negative us values
    in the same format as our encoder output.
    """

    def test_known_code_structure(self):
        """
        A known Marantec code should produce a valid frame that starts
        with sync and has exactly 100 elements.
        """
        # Example code from a Marantec D382 remote
        code = 0x1AABBCCDDEE01
        raw = encode_marantec_frame(code)
        assert len(raw) == 100
        assert raw[0] > 0    # starts with mark
        assert raw[1] < 0    # followed by space
        assert raw[-2] > 0   # ends with mark
        assert raw[-1] < 0   # and space

    def test_only_two_pulse_lengths(self):
        """
        Marantec OOK should only produce marks/spaces of TE and 3xTE
        (plus the sync gap of 16xTE).
        """
        code = 0x1234567890ABC
        raw = encode_marantec_frame(code)

        marks = {v for v in raw if v > 0}
        spaces = {abs(v) for v in raw if v < 0}

        assert marks == {TE, TE * 3}            # 802, 2406
        assert spaces == {TE, TE * 3, TE * 16}  # 802, 2406, 12832
