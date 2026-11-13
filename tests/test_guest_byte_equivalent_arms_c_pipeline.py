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
#   - Source-proven pure C ternaries whose arms retain one live guest byte.
# - Must-Not:
#   - Turn runtime predicates into host decisions or discard guest I/O.
# - Allows:
#   - Inputs: original source, pinned Clang nodes, binary guest input.
#   - Outputs: authenticated byte identity or fail-closed refusal.
#   - Side effects: temporary guest artifacts only.
# - Split-When:
#   - General runtime C conditional control reaches Malbolge lowering.
# - Merge-When:
#   - Guest byte expression proof becomes a general typed SSA pass.
# - Summary:
#   - Pure dynamic guards with equivalent byte arms need no guest branch.

"""Complete C-to-guest evidence for side-effect-free equivalent ternary arms."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast, override

from tests import test_guest_byte_conditional_identity_c_pipeline as previous
from tests import test_guest_byte_identity_arithmetic_c_pipeline as arithmetic

ROOT = previous.ROOT
FRONTEND = previous.FRONTEND
ADAPTER = previous.ADAPTER
LAYOUT = previous.LAYOUT
VM = previous.VM
COMPILE = previous.COMPILE
RUN = previous.RUN
NORMALIZED = previous.NORMALIZED
PROJECT = previous.PROJECT
OUTPUT_LINE = 6


def _source(
    *,
    expression: str = "current > 127 ? (current + 0) : (current & 255)",
    bound: int = 3,
) -> str:
    """Produce a complete C loop, static branch, continue and binary I/O."""
    return arithmetic.source(expression=expression, bound=bound)


class GuestByteEquivalentArmsCPipelineTests(unittest.TestCase):
    """Require actual guest effects, strict source proof and negative gates."""

    @override
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned frontend, adapter, layout and VM required")

    def test_complete_loop_compares_live_input_without_branching_guest(
        self,
    ) -> None:
        """A strict threshold on a live C byte must not become host output."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "comparison.c"
            guest = root / "comparison.malbolge"
            _ = program.write_text(_source(), encoding="utf-8")
            compiled = COMPILE(program, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            boundaries = (
                bytes((0, 255)),
                bytes((127, 128)),
                bytes((128, 127)),
                bytes((255, 0)),
            )
            seeded = (
                hashlib.shake_256(bytes((181, index))).digest(2) for index in range(16)
            )
            for data in (*boundaries, *seeded):
                with self.subTest(data=data):
                    vm = RUN(guest, data)
                    self.assertEqual(vm.returncode, 0, vm.stderr)
                    self.assertEqual(vm.stdout, bytes((data[0],) * 4 + (data[1],)))
                    self.assertEqual(vm.stderr, b"malbolge-steps-v1:8\n")

    def test_bitmask_guard_and_zero_trip_execute_in_guest(self) -> None:
        """Parity and skipped induction cannot manufacture guest effects."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, (expression, bound, copies, steps) in enumerate(
                (
                    ("current & 1 ? current : current", 3, 4, 8),
                    ("current > 127 ? current : current", 0, 1, 5),
                )
            ):
                with self.subTest(expression=expression):
                    program = root / f"variant-{index}.c"
                    guest = root / f"variant-{index}.malbolge"
                    _ = program.write_text(
                        _source(expression=expression, bound=bound),
                        encoding="utf-8",
                    )
                    compiled = COMPILE(program, guest)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    for data in (bytes((0, 255)), bytes((255, 0))):
                        vm = RUN(guest, data)
                        self.assertEqual(vm.returncode, 0, vm.stderr)
                        self.assertEqual(
                            vm.stdout, bytes((data[0],) * copies + (data[1],))
                        )
                        self.assertEqual(
                            vm.stderr, f"malbolge-steps-v1:{steps}\n".encode()
                        )

    def test_pure_comparisons_and_compositions_authenticate(self) -> None:
        """Frontend proof runs once per guard without repeated layout search."""
        expressions = (
            "current ? current : current",
            "current > 127 ? current : current",
            "current >= 128 ? (current * 1) : (current | 0)",
            "current < 128 ? current : current",
            "current <= 255 ? current : current",
            "current == 7 ? current : current",
            "current != 7 ? current : current",
            "current & 255 ? current : current",
            "current > 127 ? (current == 0 ? 0 : current) : (current ^ 0)",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, expression in enumerate(expressions):
                with self.subTest(expression=expression):
                    program = root / f"admitted-{index}.c"
                    guest = root / f"admitted-{index}.malbolge"
                    _ = program.write_text(
                        _source(expression=expression), encoding="utf-8"
                    )
                    result = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            sys.executable,
                            "--output",
                            str(guest),
                            "--source",
                            str(program),
                            "--capsule",
                        ],
                        input=json.dumps(NORMALIZED(program)).encode(),
                        capture_output=True,
                        check=False,
                        timeout=10,
                    )
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn(
                        b"layout backend exited unsuccessfully", result.stderr
                    )
                    self.assertFalse(guest.exists())

    def test_effects_unequal_arms_and_unsupported_guards_refuse(self) -> None:
        """No partial output may escape a source or semantic rejection."""
        invalid = (
            "current > 127 ? current : 0",
            "current & 1 ? current : (current + 1)",
            "current > 127 ? (current & 254) : current",
            "current > 127 ? getchar() : current",
            "current > 127 ? current : putchar(current)",
            "getchar() > 127 ? current : current",
            "putchar(current) > 127 ? current : current",
            "current & 256 ? current : current",
            "current / 0 ? current : current",
            "current + 1 ? current : current",
            "current > 127 ? current : current + getchar()",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, expression in enumerate(invalid):
                with self.subTest(expression=expression):
                    program = root / f"invalid-{index}.c"
                    guest = root / f"invalid-{index}.malbolge"
                    _ = program.write_text(
                        _source(expression=expression), encoding="utf-8"
                    )
                    result = COMPILE(program, guest)
                    self.assertNotEqual(result.returncode, 0, expression)
                    self.assertFalse(guest.exists())

    def test_clang_guard_and_arm_forgery_refuse(self) -> None:
        """Parentage, span and literal mutations must never authorize output."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "original.c"
            _ = program.write_text(_source(), encoding="utf-8")
            normalized = NORMALIZED(program)
            original_nodes = cast("list[dict[str, object]]", normalized["nodes"])
            affected = [
                index
                for index, node in enumerate(original_nodes)
                if cast("dict[str, dict[str, int]]", node["span"])["begin"]["line"]
                == OUTPUT_LINE
            ]
            for index in affected:
                for field in ("parent", "span"):
                    with self.subTest(node=index, field=field):
                        forged = copy.deepcopy(normalized)
                        nodes = cast("list[dict[str, object]]", forged["nodes"])
                        if field == "parent":
                            nodes[index]["parent"] = 1
                        else:
                            span = cast(
                                "dict[str, dict[str, int]]", nodes[index]["span"]
                            )
                            span["begin"]["column"] += 1
                        guest = root / f"forged-{index}-{field}.malbolge"
                        result = PROJECT(forged, guest, program)
                        self.assertNotEqual(result.returncode, 0, (index, field))
                        self.assertFalse(guest.exists())
            for field in ("literal", "constant_integer"):
                forged = copy.deepcopy(normalized)
                nodes = cast("list[dict[str, object]]", forged["nodes"])
                candidate = next(node for node in nodes if node.get("literal") == "127")
                candidate[field] = "128"
                guest = root / f"literal-{field}.malbolge"
                result = PROJECT(forged, guest, program)
                self.assertNotEqual(result.returncode, 0, field)
                self.assertFalse(guest.exists())

    def test_rehashed_original_source_and_absent_source_refuse(self) -> None:
        """A changed C guard or arm cannot borrow a trusted Clang document."""
        original = _source()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "original.c"
            _ = program.write_text(original, encoding="utf-8")
            normalized = NORMALIZED(program)
            changes = (
                ("current > 127", "current < 127"),
                ("(current & 255)", "(current & 254)"),
                ("current + 0", "current - 0"),
                ("current > 127", "currenx > 127"),
            )
            for index, (old, new) in enumerate(changes):
                with self.subTest(change=index):
                    changed = root / f"changed-{index}.c"
                    _ = changed.write_text(original.replace(old, new), encoding="utf-8")
                    forged = copy.deepcopy(normalized)
                    metadata = cast("dict[str, object]", forged["source"])
                    metadata["sha256"] = hashlib.sha256(
                        changed.read_bytes()
                    ).hexdigest()
                    guest = root / f"changed-{index}.malbolge"
                    result = PROJECT(forged, guest, changed)
                    self.assertNotEqual(result.returncode, 0, index)
                    self.assertFalse(guest.exists())
            guest = root / "no-source.malbolge"
            result = PROJECT(normalized, guest, None)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(guest.exists())


if __name__ == "__main__":
    _ = unittest.main()
