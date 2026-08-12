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
#   - Deterministic versioned compiler-challenge generation.
# - Must-Not:
#   - Depend on host randomness, host integer overflow, or compiler internals.
# - Allows:
#   - Inputs: explicit family/version/seed/profile/difficulty and output root.
#   - Outputs: one C source, binary oracle, and canonical JSON manifest.
#   - Side effects: atomic publication below the requested output root.
# - Split-When:
#   - Another family requires an independent semantic oracle or input model.
# - Merge-When:
#   - Another generator has identical identity and oracle semantics.
# - Summary:
#   - Deterministic parametric compiler challenge generator.
# - Description:
#   - Generates replayable versioned C32 challenge families with exact oracles.
# - Usage:
#   - `python benchmarks/challenges/generate.py arithmetic-dag ...`.
# - Defaults:
#   - Invalid identities, collisions, and difficulty parameters fail closed.
#

"""Deterministic parametric compiler challenge generation."""

from __future__ import annotations

import argparse
import ctypes
from dataclasses import dataclass
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Final
from typing import Never
from typing import Protocol
from typing import cast

_WINDOWS_OS_NAME: Final = "nt"
_LINUX_PLATFORM: Final = "linux"
_AT_FDCWD: Final = -100
_RENAME_NOREPLACE: Final = 1

_ARITHMETIC_DAG_FAMILY: Final = "arithmetic-dag"
_BRANCH_MIX_FAMILY: Final = "branch-mix"
_CALL_CHAIN_FAMILY: Final = "call-chain"
_LINEAR_MIX_FAMILY: Final = "linear-mix"
_MEMORY_WALK_FAMILY: Final = "memory-walk"
_POINTER_WALK_FAMILY: Final = "pointer-walk"
_ALIAS_WALK_FAMILY: Final = "alias-walk"
_STREAM_STATE_FAMILY: Final = "stream-state"
_GRAPH_REDUCE_FAMILY: Final = "graph-reduce"
_GRID_ACCUMULATE_FAMILY: Final = "grid-accumulate"
_LAYOUT_CHAIN_FAMILY: Final = "layout-chain"
_TERNARY_FOLD_FAMILY: Final = "ternary-fold"
_NESTED_STATE_FAMILY: Final = "nested-state"
_FAMILY_ALGORITHMS: Final = {
    _ARITHMETIC_DAG_FAMILY: "splitmix64-arithmetic-dag-v1",
    _BRANCH_MIX_FAMILY: "splitmix64-branch-mix-v1",
    _CALL_CHAIN_FAMILY: "splitmix64-call-chain-v1",
    _LINEAR_MIX_FAMILY: "splitmix64-linear-mix-v1",
    _MEMORY_WALK_FAMILY: "splitmix64-memory-walk-v1",
    _POINTER_WALK_FAMILY: "splitmix64-pointer-walk-v1",
    _ALIAS_WALK_FAMILY: "splitmix64-alias-walk-v1",
    _STREAM_STATE_FAMILY: "splitmix64-stream-state-v1",
    _GRAPH_REDUCE_FAMILY: "splitmix64-graph-reduce-v1",
    _GRID_ACCUMULATE_FAMILY: "splitmix64-grid-accumulate-v1",
    _LAYOUT_CHAIN_FAMILY: "splitmix64-layout-chain-v1",
    _TERNARY_FOLD_FAMILY: "splitmix64-ternary-fold-v1",
    _NESTED_STATE_FAMILY: "splitmix64-nested-state-v1",
}
_FAMILIES: Final = frozenset(_FAMILY_ALGORITHMS)
_VERSION: Final = 1
_BRANCH_MIX_SEED_SALT: Final = 0x4252_414E_4348_4D58
_CALL_CHAIN_SEED_SALT: Final = 0x4341_4C4C_4348_414E
_LINEAR_MIX_SEED_SALT: Final = 0x4C49_4E45_4152_4D58
_MEMORY_WALK_SEED_SALT: Final = 0x4D45_4D4F_5259_574B
_POINTER_WALK_SEED_SALT: Final = 0x5054_5257_414C_4B31
_ALIAS_WALK_SEED_SALT: Final = 0x414C_4941_5357_4B31
_STREAM_STATE_SEED_SALT: Final = 0x5354_524D_5354_4154
_GRAPH_REDUCE_SEED_SALT: Final = 0x4752_4150_4852_4431
_GRID_ACCUMULATE_SEED_SALT: Final = 0x4752_4944_5F41_4343
_LAYOUT_CHAIN_SEED_SALT: Final = 0x4C41_594F_5554_4348
_TERNARY_FOLD_SEED_SALT: Final = 0x5445_524E_4152_5931
_NESTED_STATE_SEED_SALT: Final = 0x4E45_5354_5354_4154
_NESTED_STATE_LANES: Final = 4
_MEMORY_WALK_CELLS: Final = 8
_CLASSIC_TRITS: Final = 10
_CLASSIC_MODULUS: Final = 59_049
_MASK32: Final = (1 << 32) - 1
_MASK64: Final = (1 << 64) - 1
_MAX_NODES: Final = 1_000_000
_OP_ADD: Final = 0
_OP_XOR: Final = 1
_OP_MULTIPLY: Final = 2
_ORACLE_BYTES: Final = 4
_ENTRY_SYMBOL: Final = "malbolge_challenge"
_PROFILE_CANONICALIZATION: Final = "malbolge-profile-v1"
_PROFILE_PREFIX: Final = f"{_PROFILE_CANONICALIZATION}:sha256:"
_ROOT: Final = Path(__file__).resolve().parents[2]
_COMPOSITION_ROOT: Final = (
    _ROOT / "src" / "automation" / "repository" / "composition"
)
if str(_COMPOSITION_ROOT) not in sys.path:
    sys.path.insert(0, str(_COMPOSITION_ROOT))

from scripts.validate import (  # ruff: ignore[module-import-not-at-top-of-file]
    target_profile,
)

_PROFILE_MANIFEST: Final = target_profile.FINGERPRINT_MANIFEST
_EXPECTED_ARTIFACTS: Final = frozenset({
    "manifest.json",
    "oracle.bin",
    "program.c",
})


class _RenameAt2(Protocol):
    """Typed view of the Linux libc renameat2 entry point."""

    argtypes: tuple[object, ...]
    restype: object

    def __call__(self, *arguments: int | bytes) -> int:
        """Rename one path with the fixed Linux renameat2 ABI arguments."""
        ...


class ChallengeError(ValueError):
    """Raised when challenge identity or publication cannot fail safely."""


def _fail(message: str, cause: BaseException | None = None) -> Never:
    if cause is None:
        raise ChallengeError(message)
    raise ChallengeError(message) from cause


def _canonical_profile_document() -> target_profile.JsonObject:
    try:
        return target_profile.load_document(target_profile.DEFAULT_PROFILE)
    except (OSError, target_profile.ProfileValidationError) as error:
        message = "canonical target profile authority is unavailable or invalid"
        _fail(message, error)


def _verify_profile_projection(canonical: target_profile.JsonObject) -> None:
    try:
        observed_projection = _PROFILE_MANIFEST.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        message = "canonical profile fingerprint manifest is unavailable"
        _fail(message, error)
    expected_projection = target_profile.render_profile_fingerprint_manifest(
        canonical
    )
    if observed_projection != expected_projection:
        message = (
            "canonical profile fingerprint manifest disagrees with registry"
        )
        _fail(message)


def _canonical_profile_fingerprint(profile_id: str) -> str:
    canonical = _canonical_profile_document()
    _verify_profile_projection(canonical)
    try:
        return target_profile.profile_fingerprint(canonical, profile_id)
    except target_profile.ProfileValidationError as error:
        message = f"unsupported canonical target profile: {profile_id}"
        _fail(message, error)


@dataclass(frozen=True, slots=True)
class ChallengeIdentity:
    """Stable identity of one generated challenge."""

    family: str
    version: int
    seed: int
    profile: str
    nodes: int

    def validate(self) -> None:
        """Validate exact family/version/profile/difficulty identity."""
        _validate_family_version(self.family, self.version)
        _validate_seed(self.seed)
        _validate_profile(self.profile)
        _validate_nodes(self.nodes)


def _validate_family_version(family: str, version: int) -> None:
    if type(family) is not str or family not in _FAMILIES:
        message = f"unsupported challenge family: {family}"
        _fail(message)
    if type(version) is not int or version != _VERSION:
        message = f"unsupported {family} version: {version}"
        _fail(message)


def _validate_seed(seed: int) -> None:
    if type(seed) is not int or not 0 <= seed <= _MASK64:
        message = "seed must be an unsigned 64-bit integer"
        _fail(message)


def _validate_profile(profile: str) -> None:
    if type(profile) is not str or not profile or profile != profile.strip():
        message = "profile must be a non-empty unpadded identity"
        _fail(message)
    _ = _canonical_profile_fingerprint(profile)


def _validate_nodes(nodes: int) -> None:
    if type(nodes) is not int or not 1 <= nodes <= _MAX_NODES:
        message = f"nodes must be in [1, {_MAX_NODES}]"
        _fail(message)


@dataclass(frozen=True, slots=True)
class GeneratedChallenge:
    """One generated source/oracle/manifest payload."""

    source: bytes
    oracle: bytes
    manifest: bytes


class _SplitMix64:
    """Version-stable SplitMix64 stream used only for challenge construction."""

    def __init__(self, seed: int) -> None:
        self._state: int = seed & _MASK64

    def next_u64(self) -> int:
        """Return the next SplitMix64 word.

        Returns:
            The next deterministic unsigned 64-bit stream value.

        """
        self._state = (self._state + 0x9E3779B97F4A7C15) & _MASK64
        value = self._state
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & _MASK64
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & _MASK64
        return (value ^ (value >> 31)) & _MASK64

    def next_u32(self) -> int:
        """Return the low 32 bits of the next word.

        Returns:
            The next deterministic unsigned 32-bit stream value.

        """
        return self.next_u64() & _MASK32


def _rotate_left(value: int, shift: int) -> int:
    shift &= 31
    if shift == 0:
        return value & _MASK32
    return ((value << shift) | (value >> (32 - shift))) & _MASK32


def _node_expression(
    rng: _SplitMix64, index: int, values: list[int]
) -> tuple[str, int]:
    left_index = len(values) - 1
    right_index = rng.next_u64() % len(values)
    left = values[left_index]
    right = values[right_index]
    operation = rng.next_u64() % 4
    if operation == _OP_ADD:
        expression = f"v{left_index} + v{right_index}"
        value = (left + right) & _MASK32
    elif operation == _OP_XOR:
        expression = f"v{left_index} ^ v{right_index}"
        value = left ^ right
    elif operation == _OP_MULTIPLY:
        multiplier = rng.next_u32() | 1
        expression = f"v{left_index} * UINT32_C({multiplier})"
        value = (left * multiplier) & _MASK32
    else:
        shift = int((rng.next_u64() % 31) + 1)
        expression = (
            f"(v{left_index} << {shift}) | (v{left_index} >> {32 - shift})"
        )
        value = _rotate_left(left, shift)
    return f"    uint32_t v{index} = {expression};", value


def _arithmetic_dag_payload(identity: ChallengeIdentity) -> tuple[bytes, bytes]:
    rng = _SplitMix64(identity.seed)
    initial = rng.next_u32()
    lines = [
        "#include <stdint.h>",
        "",
        f"uint32_t {_ENTRY_SYMBOL}(void) {{",
        f"    uint32_t v0 = UINT32_C({initial});",
    ]
    values = [initial]
    for index in range(1, identity.nodes + 1):
        line, value = _node_expression(rng, index, values)
        lines.append(line)
        values.append(value)
    final = values[-1]
    lines.extend((
        f"    return v{identity.nodes};",
        "}",
        "",
        "int main(void) {",
        f"    uint32_t result = {_ENTRY_SYMBOL}();",
        "    return (int)(result & UINT32_C(2147483647));",
        "}",
        "",
    ))
    source = "\n".join(lines).encode()
    oracle = final.to_bytes(_ORACLE_BYTES, byteorder="little")
    return source, oracle


def _linear_mix_node_expression(
    rng: _SplitMix64, index: int, previous: int
) -> tuple[str, int]:
    previous_index = index - 1
    operation = rng.next_u64() % 4
    if operation == _OP_ADD:
        constant = rng.next_u32()
        expression = f"v{previous_index} + UINT32_C({constant})"
        value = (previous + constant) & _MASK32
    elif operation == _OP_XOR:
        constant = rng.next_u32()
        expression = f"v{previous_index} ^ UINT32_C({constant})"
        value = previous ^ constant
    elif operation == _OP_MULTIPLY:
        multiplier = rng.next_u32() | 1
        expression = f"v{previous_index} * UINT32_C({multiplier})"
        value = (previous * multiplier) & _MASK32
    else:
        shift = int((rng.next_u64() % 31) + 1)
        expression = (
            f"(v{previous_index} << {shift}) | "
            f"(v{previous_index} >> {32 - shift})"
        )
        value = _rotate_left(previous, shift)
    return f"    uint32_t v{index} = {expression};", value


def _linear_mix_payload(identity: ChallengeIdentity) -> tuple[bytes, bytes]:
    rng = _SplitMix64(identity.seed ^ _LINEAR_MIX_SEED_SALT)
    initial = rng.next_u32()
    lines = [
        "#include <stdint.h>",
        "",
        f"uint32_t {_ENTRY_SYMBOL}(void) {{",
        f"    uint32_t v0 = UINT32_C({initial});",
    ]
    value = initial
    for index in range(1, identity.nodes + 1):
        line, value = _linear_mix_node_expression(rng, index, value)
        lines.append(line)
    lines.extend((
        f"    return v{identity.nodes};",
        "}",
        "",
        "int main(void) {",
        f"    uint32_t result = {_ENTRY_SYMBOL}();",
        "    return (int)(result & UINT32_C(2147483647));",
        "}",
        "",
    ))
    source = "\n".join(lines).encode()
    oracle = value.to_bytes(_ORACLE_BYTES, byteorder="little")
    return source, oracle


def _branch_mix_payload(identity: ChallengeIdentity) -> tuple[bytes, bytes]:
    rng = _SplitMix64(identity.seed ^ _BRANCH_MIX_SEED_SALT)
    initial = rng.next_u32()
    lines = [
        "#include <stdint.h>",
        "",
        f"uint32_t {_ENTRY_SYMBOL}(void) {{",
        f"    uint32_t v0 = UINT32_C({initial});",
    ]
    value = initial
    for index in range(1, identity.nodes + 1):
        previous_index = index - 1
        mask = 1 << int(rng.next_u64() % 32)
        addend = rng.next_u32()
        xor_mask = rng.next_u32()
        lines.extend((
            f"    uint32_t v{index};",
            (
                f"    if ((v{previous_index} & UINT32_C({mask})) "
                "!= UINT32_C(0)) {"
            ),
            f"        v{index} = v{previous_index} + UINT32_C({addend});",
            "    } else {",
            f"        v{index} = v{previous_index} ^ UINT32_C({xor_mask});",
            "    }",
        ))
        if value & mask:
            value = (value + addend) & _MASK32
        else:
            value ^= xor_mask
    lines.extend((
        f"    return v{identity.nodes};",
        "}",
        "",
        "int main(void) {",
        f"    uint32_t result = {_ENTRY_SYMBOL}();",
        "    return (int)(result & UINT32_C(2147483647));",
        "}",
        "",
    ))
    source = "\n".join(lines).encode()
    oracle = value.to_bytes(_ORACLE_BYTES, byteorder="little")
    return source, oracle


def _call_chain_payload(identity: ChallengeIdentity) -> tuple[bytes, bytes]:
    rng = _SplitMix64(identity.seed ^ _CALL_CHAIN_SEED_SALT)
    initial = rng.next_u32()
    lines = [
        "#include <stdint.h>",
        "",
        "uint32_t malbolge_challenge_mix(",
        "    uint32_t value, uint32_t addend, uint32_t mask",
        ") {",
        "    return (value + addend) ^ mask;",
        "}",
        "",
        f"uint32_t {_ENTRY_SYMBOL}(void) {{",
        f"    uint32_t value = UINT32_C({initial});",
    ]
    value = initial
    for _ in range(identity.nodes):
        addend = rng.next_u32()
        mask = rng.next_u32()
        lines.extend((
            "    value = malbolge_challenge_mix(",
            f"        value, UINT32_C({addend}), UINT32_C({mask})",
            "    );",
        ))
        value = ((value + addend) & _MASK32) ^ mask
    lines.extend((
        "    return value;",
        "}",
        "",
        "int main(void) {",
        f"    uint32_t result = {_ENTRY_SYMBOL}();",
        "    return (int)(result & UINT32_C(2147483647));",
        "}",
        "",
    ))
    source = chr(10).join(lines).encode()
    oracle = value.to_bytes(_ORACLE_BYTES, byteorder="little")
    return source, oracle


def _memory_walk_step(
    rng: _SplitMix64, cells: list[int], value: int
) -> tuple[tuple[str, str], int]:
    read_index = int(rng.next_u64() % _MEMORY_WALK_CELLS)
    write_index = int(rng.next_u64() % _MEMORY_WALK_CELLS)
    addend = rng.next_u32()
    mask = rng.next_u32()
    written = (cells[read_index] + value + addend) & _MASK32
    cells[write_index] = written
    lines = (
        (
            f"    cells[{write_index}] = cells[{read_index}] + value "
            f"+ UINT32_C({addend});"
        ),
        f"    value = cells[{write_index}] ^ UINT32_C({mask});",
    )
    return lines, written ^ mask


def _memory_walk_payload(identity: ChallengeIdentity) -> tuple[bytes, bytes]:
    rng = _SplitMix64(identity.seed ^ _MEMORY_WALK_SEED_SALT)
    cells = [rng.next_u32() for _index in range(_MEMORY_WALK_CELLS)]
    initializer = ", ".join(f"UINT32_C({cell})" for cell in cells)
    lines = [
        "#include <stdint.h>",
        "",
        f"uint32_t {_ENTRY_SYMBOL}(void) {{",
        f"    uint32_t cells[{_MEMORY_WALK_CELLS}] = {{{initializer}}};",
        "    uint32_t value = cells[0];",
    ]
    value = cells[0]
    for _ in range(identity.nodes):
        step_lines, value = _memory_walk_step(rng, cells, value)
        lines.extend(step_lines)
    lines.extend((
        "    return value;",
        "}",
        "",
        "int main(void) {",
        f"    uint32_t result = {_ENTRY_SYMBOL}();",
        "    return (int)(result & UINT32_C(2147483647));",
        "}",
        "",
    ))
    source = chr(10).join(lines).encode()
    oracle = value.to_bytes(_ORACLE_BYTES, byteorder="little")
    return source, oracle


def _pointer_walk_payload(identity: ChallengeIdentity) -> tuple[bytes, bytes]:
    rng = _SplitMix64(identity.seed ^ _POINTER_WALK_SEED_SALT)
    cells = [rng.next_u32() for _index in range(_MEMORY_WALK_CELLS)]
    initializer = ", ".join(f"UINT32_C({cell})" for cell in cells)
    lines = [
        "#include <stdint.h>",
        "",
        f"uint32_t {_ENTRY_SYMBOL}(void) {{",
        f"    uint32_t cells[{_MEMORY_WALK_CELLS}] = {{{initializer}}};",
        "    uint32_t value = cells[0];",
    ]
    value = cells[0]
    for index in range(identity.nodes):
        slot = value & (_MEMORY_WALK_CELLS - 1)
        addend = rng.next_u32()
        mask = rng.next_u32()
        lines.extend((
            (
                f"    uint32_t *slot{index} = "
                "&cells[value & UINT32_C(7)];"
            ),
            (
                f"    value = (*slot{index} + value + "
                f"UINT32_C({addend})) ^ UINT32_C({mask});"
            ),
            f"    *slot{index} = value;",
        ))
        value = ((cells[slot] + value + addend) & _MASK32) ^ mask
        cells[slot] = value
    lines.extend((
        "    return value;",
        "}",
        "",
        "int main(void) {",
        f"    uint32_t result = {_ENTRY_SYMBOL}();",
        "    return (int)(result & UINT32_C(2147483647));",
        "}",
        "",
    ))
    source = chr(10).join(lines).encode()
    oracle = value.to_bytes(_ORACLE_BYTES, byteorder="little")
    return source, oracle


def _alias_walk_payload(identity: ChallengeIdentity) -> tuple[bytes, bytes]:
    rng = _SplitMix64(identity.seed ^ _ALIAS_WALK_SEED_SALT)
    cells = [rng.next_u32() for _index in range(_MEMORY_WALK_CELLS)]
    initializer = ", ".join(f"UINT32_C({cell})" for cell in cells)
    lines = [
        "#include <stdint.h>",
        "",
        f"uint32_t {_ENTRY_SYMBOL}(void) {{",
        f"    uint32_t cells[{_MEMORY_WALK_CELLS}] = {{{initializer}}};",
        "    uint32_t value = cells[0];",
    ]
    value = cells[0]
    for index in range(identity.nodes):
        left = value & (_MEMORY_WALK_CELLS - 1)
        right = (value >> 3) & (_MEMORY_WALK_CELLS - 1)
        addend = rng.next_u32()
        mask = rng.next_u32()
        lines.extend((
            f"    uint32_t *left{index} = &cells[value & UINT32_C(7)];",
            (
                f"    uint32_t *right{index} = "
                "&cells[(value >> UINT32_C(3)) & UINT32_C(7)];"
            ),
            (
                f"    uint32_t mixed{index} = *left{index} + *right{index} + "
                f"value + UINT32_C({addend});"
            ),
            f"    value = mixed{index} ^ UINT32_C({mask});",
            f"    *left{index} = value;",
            f"    *right{index} ^= value;",
        ))
        value = (
            (cells[left] + cells[right] + value + addend) & _MASK32
        ) ^ mask
        cells[left] = value
        cells[right] ^= value
    lines.extend((
        "    return value;",
        "}",
        "",
        "int main(void) {",
        f"    uint32_t result = {_ENTRY_SYMBOL}();",
        "    return (int)(result & UINT32_C(2147483647));",
        "}",
        "",
    ))
    return (
        chr(10).join(lines).encode(),
        value.to_bytes(_ORACLE_BYTES, byteorder="little"),
    )


def _stream_state_payload(identity: ChallengeIdentity) -> tuple[bytes, bytes]:
    rng = _SplitMix64(identity.seed ^ _STREAM_STATE_SEED_SALT)
    initial = rng.next_u32()
    addend = rng.next_u32()
    mask = rng.next_u32()
    tokens = [rng.next_u32() for _index in range(identity.nodes)]
    lines = [
        "#include <stdint.h>",
        "",
        f"uint32_t {_ENTRY_SYMBOL}(void) {{",
        f"    uint32_t stream[{identity.nodes}] = {{",
        *(f"        UINT32_C({token})," for token in tokens),
        "    };",
        f"    uint32_t state = UINT32_C({initial});",
        (
            "    for (uint32_t index = UINT32_C(0); "
            f"index < UINT32_C({identity.nodes}); "
            "index += UINT32_C(1)) {"
        ),
        "        uint32_t token = stream[index];",
        "        if (((state ^ token) & UINT32_C(1)) != UINT32_C(0)) {",
        (
            "            state = (state + token + "
            f"UINT32_C({addend})) ^ UINT32_C({mask});"
        ),
        "        } else {",
        (
            "            state = (state ^ token ^ "
            f"UINT32_C({mask})) + UINT32_C({addend});"
        ),
        "        }",
        "    }",
        "    return state;",
        "}",
        "",
        "int main(void) {",
        f"    uint32_t result = {_ENTRY_SYMBOL}();",
        "    return (int)(result & UINT32_C(2147483647));",
        "}",
        "",
    ]
    state = initial
    for token in tokens:
        if (state ^ token) & 1:
            state = ((state + token + addend) & _MASK32) ^ mask
        else:
            state = ((state ^ token ^ mask) + addend) & _MASK32
    return (
        chr(10).join(lines).encode(),
        state.to_bytes(_ORACLE_BYTES, byteorder="little"),
    )


def _graph_reduce_payload(identity: ChallengeIdentity) -> tuple[bytes, bytes]:
    rng = _SplitMix64(identity.seed ^ _GRAPH_REDUCE_SEED_SALT)
    initial = rng.next_u32()
    mask = rng.next_u32()
    parents: list[int] = []
    weights: list[int] = []
    states = [initial]
    for index in range(identity.nodes):
        parent = int(rng.next_u64() % (index + 1))
        weight = rng.next_u32()
        parents.append(parent)
        weights.append(weight)
        combined = (states[parent] + states[index] + weight) & _MASK32
        states.append(combined ^ mask)
    lines = [
        "#include <stdint.h>",
        "",
        f"uint32_t {_ENTRY_SYMBOL}(void) {{",
        f"    uint32_t parents[{identity.nodes}] = {{",
        *(f"        UINT32_C({parent})," for parent in parents),
        "    };",
        f"    uint32_t weights[{identity.nodes}] = {{",
        *(f"        UINT32_C({weight})," for weight in weights),
        "    };",
        f"    uint32_t states[{identity.nodes + 1}] = {{",
        f"        UINT32_C({initial}),",
        *("        UINT32_C(0)," for _index in range(identity.nodes)),
        "    };",
        (
            "    for (uint32_t index = UINT32_C(0); "
            f"index < UINT32_C({identity.nodes}); "
            "index += UINT32_C(1)) {"
        ),
        "        uint32_t parent = parents[index];",
        "        uint32_t previous = states[index];",
        (
            "        states[index + UINT32_C(1)] = "
            "(states[parent] + previous + weights[index]) "
            f"^ UINT32_C({mask});"
        ),
        "    }",
        f"    return states[{identity.nodes}];",
        "}",
        "",
        "int main(void) {",
        f"    uint32_t result = {_ENTRY_SYMBOL}();",
        "    return (int)(result & UINT32_C(2147483647));",
        "}",
        "",
    ]
    return (
        chr(10).join(lines).encode(),
        states[-1].to_bytes(_ORACLE_BYTES, byteorder="little"),
    )


def _grid_accumulate_payload(
    identity: ChallengeIdentity,
) -> tuple[bytes, bytes]:
    rng = _SplitMix64(identity.seed ^ _GRID_ACCUMULATE_SEED_SALT)
    initial = rng.next_u32()
    bias = rng.next_u32()
    tokens = [rng.next_u32() for _index in range(identity.nodes)]
    token_sum = sum(tokens)
    row_sum = identity.nodes * (identity.nodes - 1) // 2
    increment = (
        identity.nodes * token_sum
        + identity.nodes * row_sum
        + identity.nodes * identity.nodes * bias
    )
    state = (initial + increment) & _MASK32
    token_initializer = ", ".join(
        f"UINT32_C({token})" for token in tokens
    )
    lines = [
        "#include <stdint.h>",
        "",
        f"uint32_t {_ENTRY_SYMBOL}(void) {{",
        f"    uint32_t tokens[{identity.nodes}] = {{{token_initializer}}};",
        f"    uint32_t state = UINT32_C({initial});",
        (
            "    for (uint32_t row = UINT32_C(0); "
            f"row < UINT32_C({identity.nodes}); "
            "row += UINT32_C(1)) {"
        ),
        (
            "        for (uint32_t column = UINT32_C(0); "
            f"column < UINT32_C({identity.nodes}); "
            "column += UINT32_C(1)) {"
        ),
        (
            "            state += tokens[column] + row + "
            f"UINT32_C({bias});"
        ),
        "        }",
        "    }",
        "    return state;",
        "}",
        "",
        "int main(void) {",
        f"    uint32_t result = {_ENTRY_SYMBOL}();",
        "    return (int)(result & UINT32_C(2147483647));",
        "}",
        "",
    ]
    return (
        chr(10).join(lines).encode(),
        state.to_bytes(_ORACLE_BYTES, byteorder="little"),
    )


def _layout_chain_payload(identity: ChallengeIdentity) -> tuple[bytes, bytes]:
    rng = _SplitMix64(identity.seed ^ _LAYOUT_CHAIN_SEED_SALT)
    initial = rng.next_u32()
    steps = [
        (rng.next_u32(), rng.next_u32())
        for _index in range(identity.nodes)
    ]
    lines = ["#include <stdint.h>", ""]
    value = initial
    for index, (addend, mask) in enumerate(steps):
        lines.extend((
            f"uint32_t malbolge_layout_{index}(uint32_t value) {{",
            (
                "    return (value + "
                f"UINT32_C({addend})) ^ UINT32_C({mask});"
            ),
            "}",
            "",
        ))
        value = ((value + addend) & _MASK32) ^ mask
    lines.extend((
        f"uint32_t {_ENTRY_SYMBOL}(void) {{",
        f"    uint32_t value = UINT32_C({initial});",
    ))
    lines.extend(
        f"    value = malbolge_layout_{index}(value);"
        for index in range(identity.nodes)
    )
    lines.extend((
        "    return value;",
        "}",
        "",
        "int main(void) {",
        f"    uint32_t result = {_ENTRY_SYMBOL}();",
        "    return (int)(result & UINT32_C(2147483647));",
        "}",
        "",
    ))
    return (
        chr(10).join(lines).encode(),
        value.to_bytes(_ORACLE_BYTES, byteorder="little"),
    )


def _nested_state_payload(identity: ChallengeIdentity) -> tuple[bytes, bytes]:
    rng = _SplitMix64(identity.seed ^ _NESTED_STATE_SEED_SALT)
    initial = rng.next_u32()
    tokens = [rng.next_u32() for _index in range(identity.nodes)]
    addends = [rng.next_u32() for _index in range(_NESTED_STATE_LANES)]
    masks = [rng.next_u32() for _index in range(_NESTED_STATE_LANES)]
    state = initial
    for token in tokens:
        for lane in range(_NESTED_STATE_LANES):
            state = ((state + token + addends[lane]) & _MASK32) ^ masks[lane]
    token_initializer = ", ".join(f"UINT32_C({token})" for token in tokens)
    addend_initializer = ", ".join(
        f"UINT32_C({value})" for value in addends
    )
    mask_initializer = ", ".join(f"UINT32_C({value})" for value in masks)
    lines = [
        "#include <stdint.h>",
        "",
        f"uint32_t {_ENTRY_SYMBOL}(void) {{",
        f"    uint32_t tokens[{identity.nodes}] = {{{token_initializer}}};",
        (
            f"    uint32_t addends[{_NESTED_STATE_LANES}] = "
            f"{{{addend_initializer}}};"
        ),
        (
            f"    uint32_t masks[{_NESTED_STATE_LANES}] = "
            f"{{{mask_initializer}}};"
        ),
        f"    uint32_t state = UINT32_C({initial});",
        (
            "    for (uint32_t index = UINT32_C(0); "
            f"index < UINT32_C({identity.nodes}); "
            "index += UINT32_C(1)) {"
        ),
        "        uint32_t token = tokens[index];",
        (
            "        for (uint32_t lane = UINT32_C(0); "
            f"lane < UINT32_C({_NESTED_STATE_LANES}); "
            "lane += UINT32_C(1)) {"
        ),
        (
            "            state = (state + token + addends[lane]) "
            "^ masks[lane];"
        ),
        "        }",
        "    }",
        "    return state;",
        "}",
        "",
        "int main(void) {",
        f"    uint32_t result = {_ENTRY_SYMBOL}();",
        "    return (int)(result & UINT32_C(2147483647));",
        "}",
        "",
    ]
    return (
        chr(10).join(lines).encode(),
        state.to_bytes(_ORACLE_BYTES, byteorder="little"),
    )


def _ternary_mix_value(value: int, token: int) -> int:
    result = 0
    place = 1
    for _ in range(_CLASSIC_TRITS):
        left = value % 3
        right = token % 3
        result += ((left + (2 * right) + 1) % 3) * place
        value //= 3
        token //= 3
        place *= 3
    return result


def _ternary_fold_payload(identity: ChallengeIdentity) -> tuple[bytes, bytes]:
    rng = _SplitMix64(identity.seed ^ _TERNARY_FOLD_SEED_SALT)
    initial = rng.next_u32() % _CLASSIC_MODULUS
    tokens = [
        rng.next_u32() % _CLASSIC_MODULUS for _index in range(identity.nodes)
    ]
    state = initial
    for token in tokens:
        state = _ternary_mix_value(state, token)
    lines = [
        "#include <stdint.h>",
        "",
        "uint32_t malbolge_ternary_mix(uint32_t value, uint32_t token) {",
        "    uint32_t result = UINT32_C(0);",
        "    uint32_t place = UINT32_C(1);",
        (
            "    for (uint32_t trit = UINT32_C(0); "
            f"trit < UINT32_C({_CLASSIC_TRITS}); "
            "trit += UINT32_C(1)) {"
        ),
        "        uint32_t left = value % UINT32_C(3);",
        "        uint32_t right = token % UINT32_C(3);",
        (
            "        uint32_t mixed = (left + (UINT32_C(2) * right) + "
            "UINT32_C(1)) % UINT32_C(3);"
        ),
        "        result += mixed * place;",
        "        value /= UINT32_C(3);",
        "        token /= UINT32_C(3);",
        "        place *= UINT32_C(3);",
        "    }",
        "    return result;",
        "}",
        "",
        f"uint32_t {_ENTRY_SYMBOL}(void) {{",
        f"    uint32_t tokens[{identity.nodes}] = {{",
        *(f"        UINT32_C({token})," for token in tokens),
        "    };",
        f"    uint32_t state = UINT32_C({initial});",
        (
            "    for (uint32_t index = UINT32_C(0); "
            f"index < UINT32_C({identity.nodes}); "
            "index += UINT32_C(1)) {"
        ),
        "        state = malbolge_ternary_mix(state, tokens[index]);",
        "    }",
        "    return state;",
        "}",
        "",
        "int main(void) {",
        f"    uint32_t result = {_ENTRY_SYMBOL}();",
        "    return (int)(result & UINT32_C(2147483647));",
        "}",
        "",
    ]
    return (
        chr(10).join(lines).encode(),
        state.to_bytes(_ORACLE_BYTES, byteorder="little"),
    )


_PAYLOAD_RENDERERS: Final = {
    _ARITHMETIC_DAG_FAMILY: _arithmetic_dag_payload,
    _BRANCH_MIX_FAMILY: _branch_mix_payload,
    _CALL_CHAIN_FAMILY: _call_chain_payload,
    _LINEAR_MIX_FAMILY: _linear_mix_payload,
    _MEMORY_WALK_FAMILY: _memory_walk_payload,
    _POINTER_WALK_FAMILY: _pointer_walk_payload,
    _ALIAS_WALK_FAMILY: _alias_walk_payload,
    _STREAM_STATE_FAMILY: _stream_state_payload,
    _GRAPH_REDUCE_FAMILY: _graph_reduce_payload,
    _GRID_ACCUMULATE_FAMILY: _grid_accumulate_payload,
    _LAYOUT_CHAIN_FAMILY: _layout_chain_payload,
    _TERNARY_FOLD_FAMILY: _ternary_fold_payload,
    _NESTED_STATE_FAMILY: _nested_state_payload,
}


def _program_payload(identity: ChallengeIdentity) -> tuple[bytes, bytes]:
    renderer = _PAYLOAD_RENDERERS.get(identity.family)
    if renderer is None:
        message = f"unsupported challenge family: {identity.family}"
        _fail(message)
    return renderer(identity)


def _family_algorithm(family: str) -> str:
    algorithm = _FAMILY_ALGORITHMS.get(family)
    if algorithm is None:
        message = f"unsupported challenge family: {family}"
        _fail(message)
    return algorithm


def _manifest_bytes(
    identity: ChallengeIdentity,
    source: bytes,
    oracle: bytes,
    *,
    profile_fingerprint: str,
) -> bytes:
    manifest_object = {
        "schema": "malbolge-parametric-challenge/v1",
        "identity": {
            "family": identity.family,
            "version": identity.version,
            "seed": identity.seed,
            "target_profile": identity.profile,
            "target_profile_fingerprint": profile_fingerprint,
            "difficulty": {"nodes": identity.nodes},
        },
        "artifacts": {
            "source": "program.c",
            "source_sha256": hashlib.sha256(source).hexdigest(),
            "oracle": "oracle.bin",
            "oracle_sha256": hashlib.sha256(oracle).hexdigest(),
            "oracle_bytes": len(oracle),
        },
        "oracle_semantics": "entry-return-u32-little-endian",
        "entry_symbol": _ENTRY_SYMBOL,
        "standalone_main": "low-31-bits-only-not-oracle",
        "generator": {
            "family_algorithm": _family_algorithm(identity.family),
            "unsigned_arithmetic": "modulo-2-to-32",
        },
    }
    text = json.dumps(manifest_object, sort_keys=True, separators=(",", ":"))
    return f"{text}\n".encode()


def _validated_identity(value: object) -> ChallengeIdentity:
    if type(value) is not ChallengeIdentity:
        message = "challenge identity must use the exact immutable type"
        _fail(message)
    return value


def _validated_output_root(value: object) -> Path:
    if not isinstance(value, Path):
        message = "challenge output root must use pathlib Path"
        _fail(message)
    return value


def generate(identity: ChallengeIdentity) -> GeneratedChallenge:
    """Generate one deterministic versioned parametric challenge.

    Returns:
        Exact source, oracle, and canonical manifest bytes.

    """
    admitted_identity = _validated_identity(identity)
    admitted_identity.validate()
    profile_fingerprint = _canonical_profile_fingerprint(
        admitted_identity.profile
    )
    source, oracle = _program_payload(admitted_identity)
    manifest = _manifest_bytes(
        admitted_identity,
        source,
        oracle,
        profile_fingerprint=profile_fingerprint,
    )
    return GeneratedChallenge(source=source, oracle=oracle, manifest=manifest)


def _path_redirects(path: Path) -> bool:
    return path.is_symlink() or path.is_junction()


def _published_artifact_paths(
    root: Path,
) -> tuple[Path, Path, Path] | None:
    if _path_redirects(root) or not root.is_dir():
        return None
    entries = frozenset(path.name for path in root.iterdir())
    if entries != _EXPECTED_ARTIFACTS:
        return None
    artifacts = (
        root / "program.c",
        root / "oracle.bin",
        root / "manifest.json",
    )
    redirected = any(
        _path_redirects(path) or not path.is_file() for path in artifacts
    )
    return None if redirected else artifacts


def _published_payload(root: Path) -> GeneratedChallenge | None:
    try:
        artifacts = _published_artifact_paths(root)
        if artifacts is None:
            return None
        source, oracle, manifest = artifacts
        return GeneratedChallenge(
            source=source.read_bytes(),
            oracle=oracle.read_bytes(),
            manifest=manifest.read_bytes(),
        )
    except OSError:
        return None


def _existing_output_is_replay(
    output_root: Path,
    generated: GeneratedChallenge,
) -> bool:
    if not output_root.exists() and not _path_redirects(output_root):
        return False
    if _published_payload(output_root) == generated:
        return True
    message = f"output path already exists: {output_root}"
    _fail(message)


def _reject_linked_output_ancestor(parent: Path) -> None:
    candidate = parent
    while True:
        if _path_redirects(candidate):
            message = f"output path has linked ancestor: {candidate}"
            _fail(message)
        ancestor = candidate.parent
        if ancestor == candidate:
            return
        candidate = ancestor


def _validate_output_root(output_root: Path) -> None:
    if output_root.name in {"", ".", ".."}:
        message = "output path must name a distinct directory"
        _fail(message)


def _staging_path(output_root: Path) -> Path:
    _validate_output_root(output_root)
    parent = output_root.parent
    _reject_linked_output_ancestor(parent)
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        message = f"output parent cannot be prepared: {parent}"
        _fail(message, error)
    staging = parent / f".{output_root.name}.staging"
    if staging.exists() or _path_redirects(staging):
        message = f"staging path already exists: {staging}"
        _fail(message)
    return staging


def _claim_staging(staging: Path) -> None:
    try:
        staging.mkdir()
    except FileExistsError as error:
        message = f"staging path already exists: {staging}"
        _fail(message, error)
    except OSError as error:
        message = f"staging path cannot be created: {staging}"
        _fail(message, error)


def _write_staging(staging: Path, generated: GeneratedChallenge) -> None:
    _ = (staging / "program.c").write_bytes(generated.source)
    _ = (staging / "oracle.bin").write_bytes(generated.oracle)
    _ = (staging / "manifest.json").write_bytes(generated.manifest)


def _linux_rename_noreplace(source: Path, destination: Path) -> None:
    try:
        library = ctypes.CDLL(None, use_errno=True)
        renameat2 = cast("_RenameAt2", cast("object", library.renameat2))
        renameat2.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        renameat2.restype = ctypes.c_int
    except (AttributeError, OSError) as error:
        raise OSError(
            errno.ENOTSUP,
            "Linux renameat2(RENAME_NOREPLACE) is unavailable",
            destination,
        ) from error
    result = renameat2(
        _AT_FDCWD,
        os.fsencode(source),
        _AT_FDCWD,
        os.fsencode(destination),
        _RENAME_NOREPLACE,
    )
    if result != 0:
        error_number = ctypes.get_errno()
        raise OSError(
            error_number,
            os.strerror(error_number),
            destination,
        )


def _publish_staging_no_replace(
    staging: Path,
    output_root: Path,
    *,
    os_name: str = os.name,
    platform: str = sys.platform,
) -> None:
    if os_name == _WINDOWS_OS_NAME:
        _ = staging.rename(output_root)
        return
    if platform == _LINUX_PLATFORM:
        _linux_rename_noreplace(staging, output_root)
        return
    raise OSError(
        errno.ENOTSUP,
        "atomic no-replace directory publication is unsupported",
        output_root,
    )


def write_challenge(identity: ChallengeIdentity, output_root: Path) -> None:
    """Publish without deleting pre-existing unrelated state."""
    admitted_identity = _validated_identity(identity)
    admitted_output = _validated_output_root(output_root)
    generated = generate(admitted_identity)
    _validate_output_root(admitted_output)
    _reject_linked_output_ancestor(admitted_output.parent)
    if _existing_output_is_replay(admitted_output, generated):
        return
    staging = _staging_path(admitted_output)
    _claim_staging(staging)
    try:
        _write_staging(staging, generated)
        _publish_staging_no_replace(staging, admitted_output)
    except OSError as error:
        shutil.rmtree(staging, ignore_errors=True)
        message = f"challenge publication failed: {error}"
        _fail(message, error)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("family", choices=sorted(_FAMILIES))
    _ = parser.add_argument("--version", type=int, required=True)
    _ = parser.add_argument("--seed", type=int, required=True)
    _ = parser.add_argument("--profile", required=True)
    _ = parser.add_argument("--nodes", type=int, required=True)
    _ = parser.add_argument("--output", type=Path, required=True)
    return parser


def _parsed_identity(
    arguments: dict[str, object],
) -> tuple[ChallengeIdentity, Path]:
    family = arguments.get("family")
    version = arguments.get("version")
    seed = arguments.get("seed")
    profile = arguments.get("profile")
    nodes = arguments.get("nodes")
    output = arguments.get("output")
    if not isinstance(output, Path):
        message = "challenge generation failed: output must be a path"
        raise SystemExit(message)
    if not (
        type(family) is str
        and type(profile) is str
        and type(version) is int
        and type(seed) is int
        and type(nodes) is int
    ):
        message = "challenge generation failed: invalid CLI argument types"
        raise SystemExit(message)
    return ChallengeIdentity(family, version, seed, profile, nodes), output


def main() -> int:
    """Run the deterministic challenge CLI.

    Returns:
        Zero after an exact challenge is published or replayed.

    Raises:
        SystemExit: If CLI arguments or challenge publication are invalid.

    """
    arguments = cast("dict[str, object]", vars(_parser().parse_args()))
    identity, output = _parsed_identity(arguments)
    try:
        write_challenge(identity, output)
    except ChallengeError as error:
        message = f"challenge generation failed: {error}"
        raise SystemExit(message) from error
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
