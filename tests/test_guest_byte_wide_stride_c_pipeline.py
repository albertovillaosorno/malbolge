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
#   - Source-authenticated two-digit induction strides in complete C streams.
# - Must-Not:
#   - Guess loop termination or trust forged Clang/source stride evidence.
# - Allows:
#   - Inputs: pinned Clang AST, original C, genuine binary guest input.
#   - Outputs: guest output parity or refusal before artifact publication.
#   - Side effects: temporary compilation artifacts only.
# - Split-When:
#   - Guest runtime induction supersedes statically proven C replay.
# - Merge-When:
#   - General loop lowering owns the same source geometry and provenance.
# - Summary:
#   - Prove finite two-digit C strides without inventing guest-side control.
# - Description:
#   - Cover real input, branching, exact endpoints and forged stride sources.
# - Usage:
#   - Run with python3.14 -B -m unittest.
# - Defaults:
#   - Any unknown or divergent loop fails closed.

"""Complete C-to-Malbolge streams with two-digit finite induction strides."""

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

from tests import test_guest_byte_named_induction_c_pipeline as previous
from tests import test_guest_byte_total_if_c_pipeline as total

ROOT = previous.ROOT
COMPILE = previous.COMPILE
RUN = previous.RUN
NORMALIZED = previous.NORMALIZED
PROJECT = previous.PROJECT


def program(
    name: str = "position",
    *,
    initial: int = 0,
    bound: int = 36,
    step: str = "+= 12",
) -> str:
    """Retain a nested live-byte branch and an induction-selected continue."""
    return previous.program(name, initial=initial, bound=bound, step=step)


class GuestByteWideStrideCPipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if not all(
            path.is_file()
            for path in (
                total.FRONTEND,
                total.ADAPTER,
                total.LAYOUT,
                total.VM,
            )
        ):
            self.skipTest("pinned Clang and normative guest VM required")

    def test_original_complete_c_program_emits_real_guest_bytes(self) -> None:
        """Twelve-step source induction keeps both guest reads at runtime."""
        inputs = (
            *(bytes((value, value ^ 255)) for value in (0, 1, 127, 128, 255)),
            *(hashlib.shake_256(bytes((71, index))).digest(2) for index in range(8)),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "wide.c"
            guest = source.with_suffix(".malbolge")
            _ = source.write_text(program())
            result = COMPILE(source, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            for data in inputs:
                with self.subTest(data=data):
                    vm = RUN(guest, data)
                    self.assertEqual(vm.returncode, 0, vm.stderr)
                    self.assertEqual(vm.stdout, bytes((data[0],) * 4 + (data[1],)))
                    self.assertEqual(vm.stderr, b"malbolge-steps-v1:8\n")

    def test_reverse_two_digit_stride_runs_original_guest(self) -> None:
        """Descending exact endpoints cannot be guessed from the comparator."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "reverse.c"
            guest = source.with_suffix(".malbolge")
            _ = source.write_text(program(initial=36, bound=0, step="-= 12"))
            result = COMPILE(source, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            for data in (b"\0\xff", b"\xff\0", b"\x80\x7f"):
                vm = RUN(guest, data)
                self.assertEqual(vm.returncode, 0, vm.stderr)
                self.assertEqual(vm.stdout, bytes((data[0],) * 4 + (data[1],)))

    def test_two_digit_step_variants_reach_layout(self) -> None:
        """Compound, assigned, ordered and zero-trip geometry prove source C."""
        cases = (
            (0, 36, "+= 12"),
            (0, 36, "= position + 12"),
            (36, 0, "= position - 12"),
            (0, 30, "+= 10"),
            (36, 36, "+= 12"),
            (99, 0, "-= 99"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, (initial, bound, step) in enumerate(cases):
                with self.subTest(initial=initial, bound=bound, step=step):
                    source = Path(directory) / f"variant-{index}.c"
                    guest = source.with_suffix(".malbolge")
                    _ = source.write_text(
                        program(initial=initial, bound=bound, step=step)
                    )
                    result = subprocess.run(
                        [
                            str(total.ADAPTER),
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

    def test_overshoot_and_forged_stride_refuse_without_artifact(self) -> None:
        """Exact 12-step inequality and Clang/source evidence are mandatory."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "original.c"
            guest = source.with_suffix(".malbolge")
            for initial, bound, step in (
                (0, 35, "+= 12"),
                (36, 1, "-= 12"),
                (0, 36, "-= 12"),
                (36, 0, "+= 12"),
                (0, 36, "+= 00"),
            ):
                with self.subTest(initial=initial, bound=bound, step=step):
                    _ = source.write_text(
                        program(initial=initial, bound=bound, step=step)
                    )
                    result = COMPILE(source, guest)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(guest.exists())
            original = program()
            _ = source.write_text(original)
            normalized = NORMALIZED(source)
            for field in ("literal", "source", "operator", "parent"):
                with self.subTest(field=field):
                    forged = copy.deepcopy(normalized)
                    nodes = cast("list[dict[str, object]]", forged["nodes"])
                    compound = next(
                        node
                        for node in nodes
                        if node.get("kind") == "compound-assignment-expression"
                    )
                    if field == "literal":
                        rhs = nodes[nodes.index(compound) + 2]
                        rhs["literal"] = "11"
                        rhs["constant_integer"] = "11"
                    elif field == "operator":
                        compound["operation"] = "-="
                    elif field == "parent":
                        compound["parent"] = 0
                    else:
                        _ = source.write_text(original.replace("+= 12", "+= 13"))
                    candidate = Path(directory) / f"forged-{field}.malbolge"
                    result = PROJECT(forged, candidate, source)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(candidate.exists())
                    _ = source.write_text(original)


if __name__ == "__main__":
    _ = unittest.main()
