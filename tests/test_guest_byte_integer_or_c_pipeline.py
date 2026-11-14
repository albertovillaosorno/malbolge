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
#   - Source-proven C integer bitwise OR truth over successful guest bytes.
# - Must-Not:
#   - Treat integer XOR/AND as Boolean or run guest computation on host.
# - Allows:
#   - Inputs: original C, pinned Clang and binary successful guest reads.
#   - Outputs: normative VM parity or refusal without guest publication.
#   - Side effects: isolated temporary artifacts only.
# - Split-When:
#   - General guest-side C arithmetic and branches replace static proofs.
# - Merge-When:
#   - General pure byte-expression proofs subsume bitwise OR.
# - Summary:
#   - Prove non-Boolean bitwise OR zero/nonzero without a Boolean cast.
# - Description:
#   - Execute counted, branching input streams with two independent reads.
# - Usage:
#   - Run with python3.14 -B -m unittest.
# - Defaults:
#   - Reject unproven effects and modified source or Clang evidence.

"""Whole C-to-guest proof of integer bitwise OR truth, not integer XOR."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import tempfile
from typing import cast
from typing import override
import unittest

from tests import test_guest_byte_equivalent_if_c_pipeline as previous
from tests import test_guest_byte_total_if_c_pipeline as total

ROOT = previous.ROOT
COMPILE = previous.COMPILE
RUN = previous.RUN
NORMALIZED = previous.NORMALIZED
PROJECT = previous.PROJECT
BINARY_KIND = "binary-expression"
BITWISE_OR = "|"
EIGHT_STEPS = b"malbolge-steps-v1:8\n"


class GuestByteIntegerOrCPipelineTests(unittest.TestCase):
    """Verify live input, source authenticity and exact integer OR truth."""

    @override
    def setUp(self) -> None:
        if not all(
            path.is_file()
            for path in (
                previous.FRONTEND,
                previous.ADAPTER,
                previous.LAYOUT,
                previous.VM,
            )
        ):
            self.skipTest("pinned C toolchain and normative VM required")

    @staticmethod
    def test_integer_mask_or_preserves_guest_effects() -> None:
        """Different non-Boolean mask values must use the actual guest data."""
        guards = (
            "(current & 2) | (current & 4)",
            "((current & 2) | (current & 4)) == 0",
            "((current & 2) | (current & 4)) || (current == 0)",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, guard in enumerate(guards):
                source = root / f"integer-or-{index}.c"
                guest = root / f"integer-or-{index}.malbolge"
                _ = source.write_text(previous.source(guard), encoding="utf-8")
                compiled = COMPILE(source, guest)
                assert compiled.returncode == 0, (guard, compiled.stderr)
                boundaries = (bytes((0, 255)), bytes((2, 4)), bytes((4, 2)))
                seeded = (
                    hashlib.shake_256(bytes((47, value))).digest(2)
                    for value in range(12)
                )
                for data in (*boundaries, *seeded):
                    actual = RUN(guest, data)
                    assert actual.returncode == 0, (guard, data, actual.stderr)
                    expected = bytes((data[0],) * 4 + (data[1],))
                    assert actual.stdout == expected, (guard, data)
                    assert actual.stderr == EIGHT_STEPS

    @staticmethod
    def test_integer_and_xor_and_unknown_effect_refuse() -> None:
        """The OR zero law does not generalize to AND or XOR."""
        invalid = (
            "(current & 2) & (current & 4)",
            "(current & 2) ^ (current & 4)",
            "((current & 2) | (current & 4)) ^ ((current & 2) != 0)",
            "((current & 2) | (current & 4)) & ((current & 2) != 0)",
            "(current & 2) | getchar()",
            "(current & 2) | putchar(65)",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, guard in enumerate(invalid):
                source = root / f"invalid-{index}.c"
                guest = root / f"invalid-{index}.malbolge"
                _ = source.write_text(previous.source(guard), encoding="utf-8")
                result = COMPILE(source, guest)
                assert result.returncode != 0, guard
                assert not guest.exists(), guard

    @staticmethod
    def test_unequal_guest_branch_effects_refuse() -> None:
        """The dynamic OR guard cannot erase a different output trace."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "unequal.c"
            guest = source.with_suffix(".malbolge")
            _ = source.write_text(
                total.source("(current & 2) | (current & 4)"),
                encoding="utf-8",
            )
            result = COMPILE(source, guest)
            assert result.returncode != 0
            assert not guest.exists()

    @staticmethod
    def test_forged_integer_or_ancestors_refuse() -> None:
        """Source-backed Clang parent, operator, span and type remain strict."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "original.c"
            _ = source.write_text(
                previous.source("(current & 2) | (current & 4)")
            )
            normalized = NORMALIZED(source)
            for field in ("parent", "operation", "type", "span"):
                forged = copy.deepcopy(normalized)
                nodes = cast("list[dict[str, object]]", forged["nodes"])
                node = next(
                    item
                    for item in nodes
                    if item["kind"] == BINARY_KIND
                    and item["operation"] == BITWISE_OR
                )
                match field:
                    case "parent":
                        node[field] = 0
                    case "operation":
                        node[field] = "^"
                    case "type":
                        node[field] = "u32"
                    case _:
                        span = cast("dict[str, dict[str, int]]", node[field])
                        span["begin"]["column"] += 1
                guest = Path(directory) / f"forged-{field}.malbolge"
                result = PROJECT(forged, guest, source)
                assert result.returncode != 0, field
                assert not guest.exists(), field
