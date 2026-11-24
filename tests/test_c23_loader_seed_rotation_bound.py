# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - Apache-2.0
# Confidential:
#   - false
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - Finite scalar search for a signed EOF two-crazy loader operand pair.
# - Must-Not:
#   - Claim this abstract operand grammar links valid guest C control.
# - Allows:
#   - Inputs: all graphical seed pairs and 15 rotations in 15-trit words.
#   - Outputs: exact byte/EOF conversion candidates and lower bound.
#   - Side effects: no compiler, VM, network or external process.
# - Split-When:
#   - A general source-loaded operand synthesizer owns the same search.
# - Merge-When:
#   - A physical signed EOF converter independently validates this bound.
# - Summary:
#   - No fewer than nine rotations in the frozen two-crazy seed grammar.

"""Independent finite N15 scalar bound, not a physical C23 guest linker."""

from __future__ import annotations

import unittest
from functools import lru_cache
from typing import Final, final

TRITS: Final = 15
MODULUS: Final = 3**TRITS
EOF_WORD: Final = MODULUS - 1
TOP_TRIT_PLACE: Final = 3 ** (TRITS - 1)
TRIT_CRAZY: Final = ((1, 0, 0), (1, 0, 2), (2, 2, 1))
# This filter cannot accept a false positive: all 256 bytes are subsequently
# checked for surviving candidates. It only discards definite mismatches.
PROBE_BYTES: Final = (0, 1, 2, 3, 42, 174, 255)


@lru_cache(maxsize=100_000)
def scalar_crazy(data: int, accumulator: int) -> int:
    """Apply the independent 15-trit crazy truth table, least trit first."""
    result = 0
    place = 1
    for _ in range(TRITS):
        result += TRIT_CRAZY[data % 3][accumulator % 3] * place
        data //= 3
        accumulator //= 3
        place *= 3
    return result


def scalar_rotate(word: int) -> int:
    """Rotate one 15-trit Malbolge word right by one trit."""
    return word // 3 + word % 3 * TOP_TRIT_PLACE


def loader_phases(first: int, second: int) -> tuple[int, ...]:
    """Enumerate six adjacent recurrence candidates from two seed words."""
    words = [first, second]
    for _ in range(6):
        words.append(scalar_crazy(words[-2], words[-1]))
    return tuple(words[2:8])


def exact_c23_low_byte(first: int, second: int) -> bool:
    """Check successful getchar bytes and signed EOF after two crazy writes."""

    def output(raw: int) -> int:
        return scalar_crazy(second, scalar_crazy(first, raw)) % 256

    if any(output(byte) != byte for byte in PROBE_BYTES):
        return False
    if output(EOF_WORD) != 255:
        return False
    return all(output(byte) == byte for byte in range(256))


@final
class TwoCrazySeedRotationBoundTests(unittest.TestCase):
    def test_all_graphical_seed_pairs_need_nine_rotations(self) -> None:
        """Freeze 94² seeds × 6² phase choices × 15 first-word rotations."""
        witnesses: list[tuple[int, int, int, int, int, int, int]] = []
        for first_seed in range(33, 127):
            for second_seed in range(33, 127):
                phases = loader_phases(first_seed, second_seed)
                for first_phase, original in enumerate(phases):
                    rotated = original
                    for count in range(15):
                        for second_phase, second in enumerate(phases):
                            if exact_c23_low_byte(rotated, second):
                                witnesses.append(
                                    (
                                        first_seed,
                                        second_seed,
                                        first_phase,
                                        count,
                                        second_phase,
                                        rotated,
                                        second,
                                    )
                                )
                        rotated = scalar_rotate(rotated)
        self.assertEqual(len(witnesses), 12)
        self.assertEqual({item[3] for item in witnesses}, {9})
        self.assertEqual({item[1] for item in witnesses}, {121})
        # 'Iy' is the earlier source-validated loader seed. This scalar
        # witness alone does not execute any program or link its nine *.
        self.assertIn((73, 121, 0, 9, 5, 7_138_732, 121), witnesses)
        self.assertEqual(
            scalar_crazy(121, scalar_crazy(7_138_732, EOF_WORD)) % 256,
            255,
        )
