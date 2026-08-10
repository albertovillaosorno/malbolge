# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Pure classic-Malbolge primitives used by bounded static transfer models.
# - Must-Not:
#   - Execute guest loops, perform I/O, or decide verifier admission policy.
# - Allows:
#   - Inputs: exact classic words, pointers, and admitted initial source words.
#   - Outputs: deterministic decode, encryption, arithmetic, and recurrence
#     data.
#   - Side effects: none.
# - Split-When:
#   - Profile-generic arithmetic needs a separately versioned semantic model.
# - Merge-When:
#   - The verifier no longer has multiple bounded transfer consumers.
# - Summary:
#   - Shared pure primitives for bounded classic Malbolge static analysis.
# - Description:
#   - Mirrors preserved historical decode, encryption, crazy, rotate, and wrap.
# - Usage:
#   - Imported by verifier transfer modules; never used as an execution loop.
# - Defaults:
#   - Non-graphical decode/encryption inputs return None fail-closed.
#

"""Pure classic-Malbolge primitives for bounded verifier transfer models."""

from __future__ import annotations

from typing import Final

PROFILE_MEMORY_WORDS: Final = 59_049
GRAPHICAL_START: Final = 33
GRAPHICAL_END: Final = 126
_DECODE_PERIOD: Final = 94
_CRAZY_TRIT: Final = ((1, 0, 0), (1, 0, 2), (2, 2, 1))
_XLAT1: Final = (
    b'+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA"lI'
    rb".v%{gJh4G\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha"
)
_XLAT2_HEX_PARTS: Final = (
    "357a5d2667717479667224287765347b575029482d5a6e2c5b255c33644c2b51",
    "3b3e5521704a53373246684f4131434236765e3d495f302f387c6a7362396d3c",
    "2e545661636075592a4d4b27587e78446c7d52456f6b4e3a233f47226940",
)
_XLAT2: Final = bytes.fromhex("".join(_XLAT2_HEX_PARTS))


def is_graphical(value: int) -> bool:
    """Check one classic word against the historical table domain.

    Returns:
        Whether the word is graphical ASCII.

    """
    return GRAPHICAL_START <= value <= GRAPHICAL_END


def decode(value: int, code_pointer: int) -> int | None:
    """Decode one exact classic cell at one code-pointer phase.

    Returns:
        Decoded translation-table byte, or ``None`` when non-graphical.

    """
    if not is_graphical(value):
        return None
    index = (value - GRAPHICAL_START + code_pointer) % _DECODE_PERIOD
    return _XLAT1[index]


def encrypt(value: int) -> int | None:
    """Encrypt one classic cell with the historical xlat2 table.

    Returns:
        Encrypted byte, or ``None`` when the input is non-graphical.

    """
    if not is_graphical(value):
        return None
    return _XLAT2[value - GRAPHICAL_START]


def crazy(data: int, accumulator: int) -> int:
    """Apply the classic ten-trit crazy operation in VM operand orientation.

    Returns:
        Exact classic-word crazy result.

    """
    result = 0
    place = 1
    for _ in range(10):
        data_trit = data % 3
        accumulator_trit = accumulator % 3
        result += _CRAZY_TRIT[data_trit][accumulator_trit] * place
        data //= 3
        accumulator //= 3
        place *= 3
    return result


def rotate(value: int) -> int:
    """Rotate one classic ten-trit word right by one trit.

    Returns:
        Exact rotated classic word.

    """
    return value // 3 + value % 3 * 19_683


def initial_memory_value(words: tuple[int, ...], address: int) -> int:
    """Resolve one initial-memory value including recurrence expansion.

    Returns:
        Exact word stored at the requested historical address.

    """
    if address < len(words):
        return words[address]
    memory = list(words)
    while len(memory) <= address:
        memory.append(crazy(memory[-2], memory[-1]))
    return memory[address]


def pointer_successor(pointer: int) -> int:
    """Advance one historical pointer with modulo-59,049 wraparound.

    Returns:
        Exact successor pointer.

    """
    return (pointer + 1) % PROFILE_MEMORY_WORDS
