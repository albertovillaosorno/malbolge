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
#   - Total byte-range comparisons with wider source-C integer literals.
# - Must-Not:
#   - Predict guest input or assume unsupported byte-dependent branches.
# - Allows:
#   - Inputs: pinned C/Clang evidence and successful binary guest input.
#   - Outputs: real VM parity or explicit fail-closed refusal.
#   - Side effects: isolated temporary guest artifacts only.
# - Split-When:
#   - General C guest-dependent control-flow lowering is implemented.
# - Merge-When:
#   - Typed interval inference subsumes the source-proven proof.
# - Summary:
#   - Authenticate total guards outside the successful input byte range.
# - Description:
#   - Checks live C streams and source/Clang integrity under wide guards.
# - Usage:
#   - Run with python3.14 -B -m unittest.
# - Defaults:
#   - Inconclusive guards and forged evidence refuse publication.

"""Real C-to-Malbolge parity for byte-total wide integer comparisons."""

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

from tests import test_guest_byte_identity_arithmetic_c_pipeline as arithmetic
from tests import test_guest_byte_range_conditional_c_pipeline as previous

ROOT = previous.ROOT
FRONTEND = previous.FRONTEND
ADAPTER = previous.ADAPTER
LAYOUT = previous.LAYOUT
VM = previous.VM
COMPILE = previous.COMPILE
RUN = previous.RUN
NORMALIZED = previous.NORMALIZED
PROJECT = previous.PROJECT


def _source(
    expression: str = "current < 256 ? ((current ^ 0) & 255) : 0",
    bound: int = 4,
) -> str:
    return arithmetic.source(expression=expression, bound=bound)


class GuestByteWideRangeConditionalCPipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C frontend, adapter, layout and VM required")

    def test_complete_source_branch_and_loop_preserve_live_binary_byte(
        self,
    ) -> None:
        """A C comparison with 256 remains true for every successful byte."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "wide-bound.c"
            guest = root / "wide-bound.malbolge"
            _ = source.write_text(_source(), encoding="utf-8")
            result = COMPILE(source, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            boundaries = (
                bytes((0, 255)),
                bytes((1, 254)),
                bytes((127, 128)),
                bytes((255, 0)),
            )
            # jig-ignore-next-line: pinned Ruff uses 88-column formatting
            seeded = (hashlib.shake_256(bytes((211, i))).digest(2) for i in range(16))
            for data in (*boundaries, *seeded):
                with self.subTest(data=data):
                    outcome = RUN(guest, data)
                    self.assertEqual(outcome.returncode, 0, outcome.stderr)
                    expected = bytes((data[0],) * 5 + (data[1],))
                    self.assertEqual(outcome.stdout, expected)
                    self.assertEqual(outcome.stderr, b"malbolge-steps-v1:9\n")

    def test_zero_exception_predicate_retains_live_guest_byte(self) -> None:
        """Zero selects zero; all positive bytes select their identity."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "zero-exception.c"
            guest = root / "zero-exception.malbolge"
            expression = "current >= 1 ? ((current ^ 0) & 255) : 0"
            _ = source.write_text(_source(expression, 3), encoding="utf-8")
            result = COMPILE(source, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            boundary = (
                bytes((0, 255)),
                bytes((1, 254)),
                bytes((255, 0)),
            )
            for data in (
                *boundary,
                # jig-ignore-next-line: pinned Ruff uses 88 columns
                *(hashlib.shake_256(bytes((233, i))).digest(2) for i in range(12)),
            ):
                with self.subTest(data=data):
                    vm = RUN(guest, data)
                    self.assertEqual(vm.returncode, 0, vm.stderr)
                    expected = bytes((data[0],) * 4 + (data[1],))
                    self.assertEqual(vm.stdout, expected)
                    self.assertEqual(vm.stderr, b"malbolge-steps-v1:8\n")

    def test_false_guard_and_zero_trip_execute_in_real_guest(self) -> None:
        """Both interval polarities preserve the exact VM effect sequence."""
        variants = (
            ("current >= 256 ? 0 : (current | 0)", 3, 4, 8),
            ("current == 4096 ? 0 : current", 0, 1, 5),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, (expr, bound, repeats, steps) in enumerate(variants):
                with self.subTest(expression=expr):
                    source = root / f"variant-{index}.c"
                    guest = root / f"variant-{index}.malbolge"
                    text = _source(expr, bound)
                    _ = source.write_text(text, encoding="utf-8")
                    result = COMPILE(source, guest)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    for data in (bytes((0, 255)), bytes((255, 0))):
                        outcome = RUN(guest, data)
                        self.assertEqual(outcome.returncode, 0, outcome.stderr)
                        self.assertEqual(
                            outcome.stdout,
                            bytes((data[0],) * repeats + (data[1],)),
                        )
                        self.assertEqual(
                            outcome.stderr,
                            f"malbolge-steps-v1:{steps}\n".encode(),
                        )

    def test_total_comparisons_and_zero_mask_reach_layout(self) -> None:
        """Front-end admission differs from the intentionally failed layout."""
        expressions = (
            "current < 256 ? current : 0",
            "current <= 256 ? current : 0",
            "current > 256 ? 0 : current",
            "current >= 256 ? 0 : current",
            "current == 256 ? 0 : current",
            "current != 256 ? current : 0",
            "current < 2147483647 ? current : 0",
            "current & 256 ? 0 : current",
            "current & 65280 ? 0 : current",
            "current > 0 ? current : 0",
            "current >= 1 ? current : 0",
            "current <= 0 ? 0 : current",
            "current < 1 ? 0 : current",
            "current & 255 ? current : 0",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, expression in enumerate(expressions):
                with self.subTest(expression=expression):
                    source = root / f"admit-{index}.c"
                    guest = root / f"admit-{index}.malbolge"
                    _ = source.write_text(_source(expression), encoding="utf-8")
                    result = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            sys.executable,
                            "--output",
                            str(guest),
                            "--source",
                            str(source),
                            "--capsule",
                        ],
                        input=json.dumps(NORMALIZED(source)).encode(),
                        capture_output=True,
                        check=False,
                        timeout=15,
                    )
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn(
                        b"layout backend exited unsuccessfully", result.stderr
                    )
                    self.assertFalse(guest.exists())

    def test_inconclusive_guards_and_bad_effects_refuse(self) -> None:
        """Neither intermediate thresholds nor hidden effects are erased."""
        invalid = (
            "current < 255 ? current : 0",
            "current > 1 ? current : 0",
            "current == 255 ? current : 0",
            "current != 255 ? current : 0",
            "current & 257 ? 0 : current",
            "current >= 2 ? current : 0",
            "current < 2 ? 0 : current",
            "current > 0 ? 0 : current",
            "current & 254 ? current : 0",
            "current < 256 ? (current + 1) : 0",
            "current < 256 ? getchar() : 0",
            "current >= 256 ? 0 : putchar(current)",
            "current < 256 ? current : getchar()",
            "getchar() < 256 ? current : 0",
            "current < 2147483648 ? current : 0",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, expression in enumerate(invalid):
                with self.subTest(expression=expression):
                    source = root / f"invalid-{index}.c"
                    guest = root / f"invalid-{index}.malbolge"
                    _ = source.write_text(_source(expression), encoding="utf-8")
                    result = COMPILE(source, guest)
                    self.assertNotEqual(result.returncode, 0, expression)
                    self.assertFalse(guest.exists())

    def test_forged_integer_and_changed_source_refuse(self) -> None:
        """A forged normalized literal or source digest cannot pass proof."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "original.c"
            original = _source()
            _ = source.write_text(original, encoding="utf-8")
            normalized = NORMALIZED(source)
            for field in ("literal", "constant_integer"):
                forged = copy.deepcopy(normalized)
                nodes = cast("list[dict[str, object]]", forged["nodes"])
                # jig-ignore-next-line: pinned Ruff uses 88 columns
                match = next(node for node in nodes if node.get("literal") == "256")
                match[field] = "255"
                guest = root / f"forged-{field}.malbolge"
                result = PROJECT(forged, guest, source)
                self.assertNotEqual(result.returncode, 0, field)
                self.assertFalse(guest.exists())
            for changed in (
                original.replace("< 256", "< 255"),
                original.replace("< 256", "< 257"),
                original.replace(" : 0", " : 1"),
            ):
                changed_source = root / "changed.c"
                _ = changed_source.write_text(changed, encoding="utf-8")
                forged = copy.deepcopy(normalized)
                record = cast("dict[str, object]", forged["source"])
                record["sha256"] = hashlib.sha256(
                    changed_source.read_bytes()
                ).hexdigest()
                guest = root / "changed.malbolge"
                outcome = PROJECT(forged, guest, changed_source)
                self.assertNotEqual(outcome.returncode, 0)
                self.assertFalse(guest.exists())
            guest = root / "missing.malbolge"
            result = PROJECT(normalized, guest, None)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(guest.exists())


if __name__ == "__main__":
    _ = unittest.main()
