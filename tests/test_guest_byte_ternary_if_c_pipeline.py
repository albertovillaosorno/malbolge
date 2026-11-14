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
#   - Pure source-proven ternary guards over real successful guest bytes.
# - Must-Not:
#   - Predict guest input, erase side effects, or trust forged Clang nodes.
# - Allows:
#   - Inputs: pinned C/Clang and binary guest input.
#   - Outputs: normative VM parity or refusal without publication.
#   - Side effects: temporary guest artifacts only.
# - Split-When:
#   - Runtime guest branching replaces finite source-C proof.
# - Merge-When:
#   - General typed control-flow equivalence supersedes this proof.
# - Summary:
#   - Prove ternary Boolean truth over all successful guest bytes.
# - Description:
#   - Run whole counted C streams with conditional guards in the VM.
# - Usage:
#   - Run with python3.14 -B -m unittest.
# - Defaults:
#   - Unproven effects and AST/source alterations fail closed.

"""Real C/VM proof for nested pure ternary predicates over binary input."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from typing import cast, override

from tests import test_guest_byte_equivalent_if_c_pipeline as previous

ROOT = previous.ROOT
FRONTEND = previous.FRONTEND
ADAPTER = previous.ADAPTER
LAYOUT = previous.LAYOUT
VM = previous.VM
COMPILE = previous.COMPILE
RUN = previous.RUN
NORMALIZED = previous.NORMALIZED
PROJECT = previous.PROJECT
EIGHT_STEPS = b"malbolge-steps-v1:8\n"
SIX_STEPS = b"malbolge-steps-v1:6\n"


class GuestByteTernaryIfCPipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler and normative VM required")

    def test_total_ternary_condition_selects_entire_output_arm(self) -> None:
        """The runtime-dependent selector is pure and both arms are total."""
        guards = (
            ("(current & 1) ? (current >= 0) : (current <= 255)", False),
            ("(current & 1) ? (current < 0) : (current > 255)", True),
            (
                (
                    "(current == 0) ? (current >= 0) : "
                    "((current & 1) ? (current > 0) : (current <= 255))"
                ),
                False,
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, (guard, reverse) in enumerate(guards):
                program = root / f"total-{index}.c"
                guest = root / f"total-{index}.malbolge"
                _ = program.write_text(
                    previous.previous.source(guard, reverse=reverse),
                    encoding="utf-8",
                )
                compiled = COMPILE(program, guest)
                assert compiled.returncode == 0, (guard, compiled.stderr)
                boundary = (bytes((0, 255)), bytes((1, 254)), bytes((255, 0)))
                seeded = (
                    hashlib.shake_256(bytes((97, number))).digest(2)
                    for number in range(9)
                )
                for data in (*boundary, *seeded):
                    with self.subTest(guard=guard, data=data):
                        actual = RUN(guest, data)
                        assert actual.returncode == 0, actual.stderr
                        assert actual.stdout == bytes((data[0],) * 4 + (data[1],))
                        assert actual.stderr == EIGHT_STEPS

    @staticmethod
    def test_dependent_ternary_guard_preserves_identical_guest_effects() -> None:
        """Different selected truth values still yield one live-byte trace."""
        guard = "(current & 1) ? (current == 1) : (current == 0)"
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "dependent.c"
            guest = root / "dependent.malbolge"
            _ = program.write_text(previous.source(guard, bound=1))
            compiled = COMPILE(program, guest)
            assert compiled.returncode == 0, compiled.stderr
            for data in (bytes((0, 255)), bytes((1, 254)), bytes((2, 253))):
                actual = RUN(guest, data)
                assert actual.returncode == 0, actual.stderr
                assert actual.stdout == bytes((data[0], data[0], data[1]))
                assert actual.stderr == SIX_STEPS

    @staticmethod
    def test_source_proven_integer_arms_compose_with_live_byte_guards() -> None:
        """Static C integer truth in a ternary preserves live guest effects."""
        cases = (
            ("current ? 1 : (current == 0)", False),
            ("(current & 1) ? 0 : 0", True),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, (guard, reverse) in enumerate(cases):
                program = root / f"integer-arm-{index}.c"
                guest = root / f"integer-arm-{index}.malbolge"
                _ = program.write_text(
                    previous.previous.source(guard, reverse=reverse, bound=1)
                )
                compiled = COMPILE(program, guest)
                assert compiled.returncode == 0, (guard, compiled.stderr)
                for data in (bytes((0, 255)), bytes((1, 254)), bytes((255, 0))):
                    vm = RUN(guest, data)
                    assert vm.returncode == 0, vm.stderr
                    assert vm.stdout == bytes((data[0], data[0], data[1]))
                    assert vm.stderr == SIX_STEPS
            dependent = root / "dependent-integer.c"
            dependent_guest = root / "dependent-integer.malbolge"
            _ = dependent.write_text(previous.source("(current & 1) ? 1 : 0", bound=1))
            compiled = COMPILE(dependent, dependent_guest)
            assert compiled.returncode == 0, compiled.stderr
            for data in (bytes((0, 255)), bytes((1, 254)), bytes((2, 253))):
                vm = RUN(dependent_guest, data)
                assert vm.returncode == 0, vm.stderr
                assert vm.stdout == bytes((data[0], data[0], data[1]))
                assert vm.stderr == SIX_STEPS

    @staticmethod
    def test_impure_or_non_equivalent_ternaries_refuse() -> None:
        """No conditional operand may hide an input or unequal side effect."""
        invalid = (
            previous.previous.source("(current & 1) ? (current == 1) : (current == 0)"),
            previous.source("(getchar() & 1) ? (current >= 0) : (current <= 255)"),
            previous.source("(current & 1) ? (getchar() >= 0) : (current <= 255)"),
            previous.source("(current & 1) ? (current >= 0) : (putchar(65) >= 0)"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, source in enumerate(invalid):
                program = root / f"invalid-{index}.c"
                guest = root / f"invalid-{index}.malbolge"
                _ = program.write_text(source, encoding="utf-8")
                result = COMPILE(program, guest)
                assert result.returncode != 0, source
                assert not guest.exists()

    @staticmethod
    def test_forged_ternary_literal_nodes_refuse() -> None:
        """The literal truth values must match original C and Clang evidence."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "literal-original.c"
            _ = program.write_text(previous.previous.source("current ? 1 : 0", bound=1))
            normalized = NORMALIZED(program)
            for field in ("literal", "constant_integer", "parent", "span", "type"):
                forged = copy.deepcopy(normalized)
                nodes = cast("list[dict[str, object]]", forged["nodes"])
                ternary = next(
                    node for node in nodes if node["kind"] == "conditional-expression"
                )
                integer = next(
                    node
                    for node in nodes
                    if node["parent"] == ternary["id"]
                    and node["kind"] == "integer-literal"
                    and node["literal"] == "0"
                )
                if field in ("literal", "constant_integer"):
                    integer[field] = "1"
                elif field == "parent":
                    integer[field] = 0
                elif field == "type":
                    integer[field] = "u32"
                else:
                    span = cast("dict[str, dict[str, int]]", integer[field])
                    span["begin"]["column"] += 1
                guest = root / f"literal-forged-{field}.malbolge"
                projected = PROJECT(forged, guest, program)
                assert projected.returncode != 0, field
                assert not guest.exists(), field

    @staticmethod
    def test_forged_ternary_clang_nodes_refuse() -> None:
        """No mutation may alter normalized parentage or condition identity."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "original.c"
            _ = program.write_text(
                previous.previous.source(
                    "(current & 1) ? (current >= 0) : (current <= 255)"
                )
            )
            normalized = NORMALIZED(program)
            for field in ("operation", "parent", "span", "type", "kind"):
                forged = copy.deepcopy(normalized)
                nodes = cast("list[dict[str, object]]", forged["nodes"])
                ternary = next(
                    node for node in nodes if node["kind"] == "conditional-expression"
                )
                if field == "operation":
                    ternary[field] = "||"
                elif field == "parent":
                    ternary[field] = 0
                elif field == "type":
                    ternary[field] = "u32"
                elif field == "kind":
                    ternary[field] = "binary-expression"
                else:
                    span = cast("dict[str, dict[str, int]]", ternary[field])
                    span["end"]["column"] += 1
                guest = root / f"forged-{field}.malbolge"
                result = PROJECT(forged, guest, program)
                assert result.returncode != 0, field
                assert not guest.exists(), field
