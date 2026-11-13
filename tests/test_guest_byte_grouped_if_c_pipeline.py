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
#   - Real C and guest parity for source-proven grouped/negated byte guards.
# - Must-Not:
#   - Speculate guest input or admit effectful/forged predicate trees.
# - Allows:
#   - Inputs: pinned C/Clang and successful binary guest input.
#   - Outputs: normative VM parity or fail-closed refusal.
#   - Side effects: isolated temporary guest artifacts only.
# - Split-When:
#   - Runtime C predicates execute as guest branches.
# - Merge-When:
#   - A general C expression lowering proof supersedes these predicates.
# - Summary:
#   - Authentic parentheses and logical negation preserve byte truth sets.
# - Description:
#   - Test whole C induction, selected continue and byte input/output.
# - Usage:
#   - Run with python3.14 -B -m unittest.
# - Defaults:
#   - Unproven/impure operands reject without a guest artifact.

"""Source-backed grouped and negated byte guards with guest VM parity."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import tempfile
from typing import cast
from typing import override
import unittest

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

UNARY_OPERATION = "!"
OPERATION_FIELD = "operation"
PARENT_FIELD = "parent"
SIX_STEPS = b"malbolge-steps-v1:6\n"
EIGHT_STEPS = b"malbolge-steps-v1:8\n"


def _forge_unary(
    normalized: dict[str, object], field: str
) -> dict[str, object]:
    forged = copy.deepcopy(normalized)
    nodes = cast("list[dict[str, object]]", forged["nodes"])
    unary = next(
        node for node in nodes if node.get(OPERATION_FIELD) == UNARY_OPERATION
    )
    if field == OPERATION_FIELD:
        unary[field] = "~"
    elif field == PARENT_FIELD:
        unary[field] = 0
    else:
        span = cast("dict[str, dict[str, int]]", unary[field])
        span["begin"]["column"] += 1
    return forged


class GuestByteGroupedIfCPipelineTests(unittest.TestCase):
    """Exercise authenticated byte truth sets through actual guest output."""

    @override
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler and normative VM tools required")

    def test_negated_parity_guard_preserves_equivalent_live_byte_effects(
        self,
    ) -> None:
        """A genuine input-dependent unary test need not guess its outcome."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "negated-dynamic.c"
            guest = root / "negated-dynamic.malbolge"
            _ = program.write_text(
                previous.source("!(current & 1)"), encoding="utf-8"
            )
            result = COMPILE(program, guest)
            assert result.returncode == 0, result.stderr
            data_set = (
                bytes((0, 255)),
                bytes((1, 254)),
                bytes((127, 128)),
                bytes((128, 127)),
                bytes((255, 0)),
                *(
                    hashlib.shake_256(bytes((239, i))).digest(2)
                    for i in range(12)
                ),
            )
            for data in data_set:
                with self.subTest(data=data):
                    vm = RUN(guest, data)
                    assert vm.returncode == 0, vm.stderr
                    expected = bytes((data[0],) * 4 + (data[1],))
                    assert vm.stdout == expected
                    assert vm.stderr == EIGHT_STEPS

    @staticmethod
    def test_parenthesized_tautology_and_negation_select_entire_arm() -> None:
        """A complete bitset stays complete through parentheses, then flips."""
        cases = (
            "(current == 0 || current != 0)",
            "!((current == 0) || (current != 0))",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, guard in enumerate(cases):
                program = root / f"grouped-{index}.c"
                guest = root / f"grouped-{index}.malbolge"
                _ = program.write_text(
                    previous.previous.source(
                        guard, reverse=index == 1, bound=1
                    ),
                    encoding="utf-8",
                )
                result = COMPILE(program, guest)
                assert result.returncode == 0, (guard, result.stderr)
                for data in (bytes((0, 255)), bytes((255, 0))):
                    vm = RUN(guest, data)
                    assert vm.returncode == 0, (guard, vm.stderr)
                    expected = bytes((data[0],) * 2 + (data[1],))
                    assert vm.stdout == expected, guard
                    assert vm.stderr == SIX_STEPS

    @staticmethod
    def test_direct_byte_zero_partitions_select_only_reachable_effects() -> (
        None
    ):
        """A live-byte zero test and its complement cover all inputs."""
        cases = (
            ("current || !current", False),
            ("!(current && !current)", False),
            ("!(current || !current)", True),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, (guard, reverse) in enumerate(cases):
                program = root / f"direct-{index}.c"
                guest = root / f"direct-{index}.malbolge"
                _ = program.write_text(
                    previous.previous.source(guard, reverse=reverse, bound=1),
                    encoding="utf-8",
                )
                compiled = COMPILE(program, guest)
                assert compiled.returncode == 0, (guard, compiled.stderr)
                for data in (bytes((0, 255)), bytes((1, 254)), bytes((255, 0))):
                    vm = RUN(guest, data)
                    assert vm.returncode == 0, (guard, vm.stderr)
                    expected = bytes((data[0],) * 2 + (data[1],))
                    assert vm.stdout == expected, guard
                    assert vm.stderr == SIX_STEPS

    @staticmethod
    def test_impure_and_unequal_grouped_guards_refuse() -> None:
        """Grouping cannot erase hidden C input or unequal branch effects."""
        invalid = (
            previous.previous.source("!(current & 1)"),
            previous.source("!(getchar() & 1)"),
            previous.source("!((current < 128) || (getchar() >= 0))"),
            previous.previous.source("current"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, text in enumerate(invalid):
                program = root / f"invalid-{index}.c"
                guest = root / f"invalid-{index}.malbolge"
                _ = program.write_text(text, encoding="utf-8")
                result = COMPILE(program, guest)
                assert result.returncode != 0, text
                assert not guest.exists()

    @staticmethod
    def test_forged_negated_clang_nodes_refuse() -> None:
        """An AST mutation cannot silently alter a proven truth set."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "original.c"
            _ = program.write_text(previous.source("!(current & 1)"))
            normalized = NORMALIZED(program)
            for field in (OPERATION_FIELD, PARENT_FIELD, "span"):
                forged = _forge_unary(normalized, field)
                guest = root / f"forged-{field}.malbolge"
                result = PROJECT(forged, guest, program)
                assert result.returncode != 0, field
                assert not guest.exists(), field
