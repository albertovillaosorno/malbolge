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
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Independent compatibility evidence for version-one fallback capsules.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Independent compatibility evidence for version-one fallback capsules."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = (
    ROOT / "tests" / "compatibility" / "capsule" / "current-profile-capsule.hex"
)
HISTORICAL_C = (
    ROOT / "src/interoperability/historical-malbolge/adapter-outbound/main.c"
)

BITS_PER_BYTE = 8
CHECKSUM_BYTES = 8
DECODED_FALLBACK = b"jopp<*v"
FILL_LIMIT = 64
GRAPHICAL_MAX = 126
GRAPHICAL_MIN = 33
HISTORICAL_OPEN_FRAGMENT = 'fopen( argv[1], "r" )'
HISTORICAL_SPACE_FRAGMENT = "if ( isspace( x ) ) continue;"
SENTINEL = b"!"
SPACE_BYTE = 0x20
TAB_BYTE = 0x09
FALLBACK = b'(C<;_"K'
FRAME_MAGIC = b"MALBCAP1"
FRAME_VERSION = 1
FRAME_FLAGS = 0
CURRENT_PROFILE = b"malbolge-2026"
CURRENT_FINGERPRINT = (
    b"malbolge-profile-v1:sha256:"
    b"1006b5fc06808f54aa5089cef0237539770c1d79a73c822e6e26e0e0ebfb0c76"
)
PAYLOAD = b"ubO\n"
FNV1A64_OFFSET = 0xCBF2_9CE4_8422_2325
FNV1A64_PRIME = 0x0000_0100_0000_01B3
FNV1A64_MASK = (1 << 64) - 1
TERNARY_ROTATE_HIGH = 19_683
WORD_TRITS = 10
XLAT1 = (
    b'+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA"lI'
    b".v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha"
)
XLAT2 = (
    b"5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1C"
    b"B6v^=I_0/8|jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@"
)
CRAZY_TABLE = (
    (1, 0, 0),
    (1, 0, 2),
    (2, 2, 1),
)


def _fixture_bytes() -> bytes:
    return bytes.fromhex(FIXTURE.read_text(encoding="ascii"))


def _crazy(left: int, right: int) -> int:
    result = 0
    place = 1
    for _ in range(WORD_TRITS):
        left_digit = left % 3
        right_digit = right % 3
        result += CRAZY_TABLE[right_digit][left_digit] * place
        left //= 3
        right //= 3
        place *= 3
    return result


def _decode_sideband(source: bytes) -> bytes:
    sideband = source[len(FALLBACK) :]
    assert sideband
    assert set(sideband) <= {SPACE_BYTE, TAB_BYTE}
    assert len(sideband) % BITS_PER_BYTE == 0
    decoded = bytearray()
    for start in range(0, len(sideband), BITS_PER_BYTE):
        value = 0
        for symbol in sideband[start : start + BITS_PER_BYTE]:
            value = (value << 1) | (1 if symbol == TAB_BYTE else 0)
        decoded.append(value)
    return bytes(decoded)


def _fnv1a64(data: bytes) -> int:
    value = FNV1A64_OFFSET
    for byte in data:
        value ^= byte
        value = (value * FNV1A64_PRIME) & FNV1A64_MASK
    return value


def _fill_fallback_memory() -> list[int]:
    memory = list(FALLBACK)
    while len(memory) <= FILL_LIMIT:
        memory.append(_crazy(memory[-1], memory[-2]))
    return memory


def _encrypt_current(memory: list[int], code: int) -> None:
    cell = memory[code]
    assert GRAPHICAL_MIN <= cell <= GRAPHICAL_MAX
    memory[code] = XLAT2[cell - GRAPHICAL_MIN]


def _historical_fallback_output() -> bytes:
    memory = _fill_fallback_memory()
    decoded = bytes(
        XLAT1[(cell - GRAPHICAL_MIN + position) % len(XLAT1)]
        for position, cell in enumerate(FALLBACK)
    )
    assert decoded == DECODED_FALLBACK

    accumulator = 0
    data = memory[0]
    _encrypt_current(memory, 0)
    data += 1

    _encrypt_current(memory, 1)
    data += 1

    accumulator = _crazy(accumulator, memory[data])
    memory[data] = accumulator
    _encrypt_current(memory, 2)
    data += 1

    accumulator = _crazy(accumulator, memory[data])
    memory[data] = accumulator
    _encrypt_current(memory, 3)
    data += 1

    output = bytes([accumulator & 0xFF])
    _encrypt_current(memory, 4)
    data += 1

    word = memory[data]
    accumulator = word // 3 + (word % 3) * TERNARY_ROTATE_HIGH
    memory[data] = accumulator
    _encrypt_current(memory, 5)

    return output


def test_capsule_frame_decodes_exact_identity_payload_and_checksum() -> None:
    """The checked-in frame has one deterministic version-one interpretation."""
    frame = _decode_sideband(_fixture_bytes())
    assert frame.startswith(FRAME_MAGIC)
    assert frame[8] == FRAME_VERSION
    assert frame[9] == FRAME_FLAGS
    profile_len = int.from_bytes(frame[10:12], "big")
    fingerprint_len = int.from_bytes(frame[12:14], "big")
    payload_len = int.from_bytes(frame[14:18], "big")
    profile_start = 18
    fingerprint_start = profile_start + profile_len
    payload_start = fingerprint_start + fingerprint_len
    checksum_start = payload_start + payload_len
    assert frame[profile_start:fingerprint_start] == CURRENT_PROFILE
    assert frame[fingerprint_start:payload_start] == CURRENT_FINGERPRINT
    assert frame[payload_start:checksum_start] == PAYLOAD
    stored = int.from_bytes(frame[checksum_start:], "big")
    assert len(frame[checksum_start:]) == CHECKSUM_BYTES
    assert stored == _fnv1a64(frame[:checksum_start])


def test_historical_loader_sees_only_fixed_fallback() -> None:
    """Space/tab sideband bytes disappear under the historical loader rule."""
    source = _fixture_bytes()
    visible = bytes(
        byte for byte in source if byte not in {SPACE_BYTE, TAB_BYTE}
    )
    assert visible == FALLBACK
    historical_source = HISTORICAL_C.read_text(encoding="ascii")
    assert HISTORICAL_OPEN_FRAGMENT in historical_source
    assert HISTORICAL_SPACE_FRAGMENT in historical_source


def test_historical_fallback_is_safe_bang_sentinel() -> None:
    """The isolated Ben-mode fallback emits `!` without input or xlat2 UB."""
    assert _historical_fallback_output() == SENTINEL
