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
#   - C byte-range predicates with a source-proven selected identity arm.
# - Must-Not:
#   - Predict guest input, erase guest effects, or admit dependent branches.
# - Allows:
#   - Inputs: source-backed Clang comparisons and successful binary guest I/O.
#   - Outputs: exact guest byte replay or fail-closed refusal.
#   - Side effects: isolated temporary guest artifacts only.
# - Split-When:
#   - Real guest-side conditional lowering supports these C guards.
# - Merge-When:
#   - Byte range analysis becomes a general typed lowering pass.
# - Summary:
#   - Provable byte bounds select a pure C identity without guest branching.

"""End-to-end source/Clang/VM proof for always-true byte-range guards."""

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

from tests import test_guest_byte_equivalent_arms_c_pipeline as previous

ROOT = previous.ROOT
FRONTEND = previous.FRONTEND
ADAPTER = previous.ADAPTER
LAYOUT = previous.LAYOUT
VM = previous.VM
COMPILE = previous.COMPILE
RUN = previous.RUN
NORMALIZED = previous.NORMALIZED
PROJECT = previous.PROJECT
OUTPUT_LINE = previous.OUTPUT_LINE


def _source(
    expression: str = "current <= 255 ? ((current ^ 0) & 255) : 0",
    bound: int = 4,
) -> str:
    return previous._source(expression=expression, bound=bound)


class GuestByteRangeConditionalCPipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C frontend, adapter, layout and VM required")

    def test_complete_loop_replays_live_byte_with_range_guard(self) -> None:
        """The real VM observes the input, never a host-predicted byte."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "range.c"
            guest = root / "range.malbolge"
            _ = source.write_text(_source(), encoding="utf-8")
            result = COMPILE(source, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            boundary = (
                bytes((0, 255)),
                bytes((1, 254)),
                bytes((127, 128)),
                bytes((255, 0)),
            )
            seeded = (
                hashlib.shake_256(bytes((197, index))).digest(2) for index in range(16)
            )
            # Stratify the successful first-input range while keeping the
            # per-test guest process and synthesis costs finite.
            byte_strata = (
                bytes((first, (first * 37 + 1) & 255)) for first in range(0, 256, 8)
            )
            for data in (*boundary, *seeded, *byte_strata):
                with self.subTest(data=data):
                    outcome = RUN(guest, data)
                    self.assertEqual(outcome.returncode, 0, outcome.stderr)
                    self.assertEqual(outcome.stdout, bytes((data[0],) * 5 + (data[1],)))
                    self.assertEqual(outcome.stderr, b"malbolge-steps-v1:9\n")

    def test_true_false_bounds_and_zero_trip_execute_in_guest(self) -> None:
        """Range proof is valid on both endpoints and both branch polarities."""
        # Other valid spellings pass the separate fast frontend-only gate;
        # avoid five costly syntheses of identical guest byte effects here.
        variants = (
            ("current > 255 ? 0 : (current | 0)", 3, 4, 8),
            ("current & 0 ? 0 : current", 0, 1, 5),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, (expression, bound, repeats, steps) in enumerate(variants):
                with self.subTest(expression=expression):
                    program = root / f"variant-{index}.c"
                    guest = root / f"variant-{index}.malbolge"
                    _ = program.write_text(_source(expression, bound), encoding="utf-8")
                    result = COMPILE(program, guest)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    for data in (bytes((0, 255)), bytes((255, 0))):
                        vm = RUN(guest, data)
                        self.assertEqual(vm.returncode, 0, vm.stderr)
                        self.assertEqual(
                            vm.stdout, bytes((data[0],) * repeats + (data[1],))
                        )
                        self.assertEqual(
                            vm.stderr, f"malbolge-steps-v1:{steps}\n".encode()
                        )

    def test_inconclusive_guards_and_effectful_arms_refuse(self) -> None:
        """Only range-total tests and pure selected identities are accepted."""
        invalid = (
            "current > 127 ? current : 0",
            "current <= 254 ? current : 0",
            "current >= 1 ? current : 0",
            "current < 255 ? 0 : current",
            "current == 0 ? current : 0",
            "current <= 255 ? (current + 1) : 0",
            "current <= 255 ? getchar() : 0",
            "current > 255 ? 0 : putchar(current)",
            "current <= 255 ? current : getchar()",
            "getchar() <= 255 ? current : 0",
            "current / 0 ? current : 0",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, expression in enumerate(invalid):
                with self.subTest(expression=expression):
                    program = root / f"invalid-{index}.c"
                    guest = root / f"invalid-{index}.malbolge"
                    _ = program.write_text(_source(expression), encoding="utf-8")
                    result = COMPILE(program, guest)
                    self.assertNotEqual(result.returncode, 0, expression)
                    self.assertFalse(guest.exists())

    def test_forged_clang_guard_and_source_refuse(self) -> None:
        """Neither stale Clang coordinates nor SHA-only source edits suffice."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "range.c"
            original = _source()
            _ = program.write_text(original, encoding="utf-8")
            normalized = NORMALIZED(program)
            original_nodes = cast("list[dict[str, object]]", normalized["nodes"])
            indices = [
                index
                for index, node in enumerate(original_nodes)
                if cast("dict[str, dict[str, int]]", node["span"])["begin"]["line"]
                == OUTPUT_LINE
            ]
            for index in indices:
                for field in ("parent", "span"):
                    with self.subTest(node=index, field=field):
                        forged = copy.deepcopy(normalized)
                        nodes = cast("list[dict[str, object]]", forged["nodes"])
                        if field == "parent":
                            nodes[index]["parent"] = 1
                        else:
                            cast("dict[str, dict[str, int]]", nodes[index]["span"])[
                                "begin"
                            ]["column"] += 1
                        guest = root / f"forged-{index}-{field}.malbolge"
                        result = PROJECT(forged, guest, program)
                        self.assertNotEqual(result.returncode, 0, (index, field))
                        self.assertFalse(guest.exists())
            for field in ("literal", "constant_integer"):
                forged = copy.deepcopy(normalized)
                nodes = cast("list[dict[str, object]]", forged["nodes"])
                next(node for node in nodes if node.get("literal") == "255")[field] = (
                    "254"
                )
                guest = root / f"forged-literal-{field}.malbolge"
                result = PROJECT(forged, guest, program)
                self.assertNotEqual(result.returncode, 0, field)
                self.assertFalse(guest.exists())
            for index, changed in enumerate(
                (
                    original.replace("<= 255", "<= 254"),
                    original.replace("& 255", "& 254"),
                    original.replace(" : 0", " : 1"),
                )
            ):
                source = root / f"changed-{index}.c"
                _ = source.write_text(changed, encoding="utf-8")
                forged = copy.deepcopy(normalized)
                cast("dict[str, object]", forged["source"])["sha256"] = hashlib.sha256(
                    source.read_bytes()
                ).hexdigest()
                guest = root / f"changed-{index}.malbolge"
                outcome = PROJECT(forged, guest, source)
                self.assertNotEqual(outcome.returncode, 0)
                self.assertFalse(guest.exists())
            guest = root / "no-source.malbolge"
            outcome = PROJECT(normalized, guest, None)
            self.assertNotEqual(outcome.returncode, 0)
            self.assertFalse(guest.exists())

    def test_range_guards_reach_admission_without_layout(self) -> None:
        """Multiple pure forms are authenticated without costly guest search."""
        expressions = (
            "current <= 255 ? current : 0",
            "current > 255 ? 0 : current",
            "current >= 0 ? (current + 0) : 0",
            "current < 0 ? 0 : current",
            "current & 0 ? 0 : current",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, expression in enumerate(expressions):
                with self.subTest(expression=expression):
                    program = root / f"proof-{index}.c"
                    guest = root / f"proof-{index}.malbolge"
                    _ = program.write_text(_source(expression), encoding="utf-8")
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


if __name__ == "__main__":
    _ = unittest.main()
