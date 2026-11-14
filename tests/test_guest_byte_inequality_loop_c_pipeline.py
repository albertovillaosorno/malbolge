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
#   - Source-proven finite C inequality induction with actual guest I/O.
# - Must-Not:
#   - Pretend divergent inequality loops terminate or predict guest input.
# - Allows:
#   - Inputs: pinned Clang AST, original C source and binary guest streams.
#   - Outputs: normative VM parity or refusal without guest publication.
#   - Side effects: temporary guest artifacts only.
# - Split-When:
#   - General guest control-flow lowering replaces static induction proof.
# - Merge-When:
#   - Finite C loop bounds share a generic verified induction contract.
# - Summary:
#   - Authenticate source C != loop bounds and unit-step termination.
# - Description:
#   - Complete loops with branch/continue and binary guest VM parity.
# - Usage:
#   - Run with python3.14 -B -m unittest.
# - Defaults:
#   - Divergent, unproven and forged loop conditions refuse publication.

"""Complete C inequality loops and real Malbolge guest I/O parity."""

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

from tests import test_guest_byte_total_if_c_pipeline as total

ROOT = total.ROOT
ADAPTER = total.ADAPTER
COMPILE = total.COMPILE
RUN = total.RUN
NORMALIZED = total.NORMALIZED
PROJECT = total.PROJECT


def program(
    initial: int = 0,
    bound: int = 3,
    step: str = "++i",
    guard: str = "((~current) ^ current) == -1",
) -> str:
    """A source program combining state, induction, continue and guest I/O."""
    source = total.source(guard, bound=3)
    original = "for (int i = 0; i < 3; ++i)"
    assert original in source
    return source.replace(original, f"for (int i = {initial}; i != {bound}; {step})")


class GuestByteInequalityLoopCPipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if not all(
            path.is_file()
            for path in (total.FRONTEND, total.ADAPTER, total.LAYOUT, total.VM)
        ):
            self.skipTest("pinned Clang and normative guest VM required")

    def test_original_finite_inequality_loop_matches_real_guest(self) -> None:
        """Three trips, a selected continue, byte guard and two guest reads."""
        inputs = (
            *(bytes((v, 255 ^ v)) for v in (0, 1, 127, 128, 254, 255)),
            *(hashlib.shake_256(bytes((37, i))).digest(2) for i in range(12)),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "finite-inequality.c"
            guest = source.with_suffix(".malbolge")
            _ = source.write_text(program(), encoding="utf-8")
            compiled = COMPILE(source, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in inputs:
                with self.subTest(data=data):
                    vm = RUN(guest, data)
                    self.assertEqual(vm.returncode, 0, vm.stderr)
                    self.assertEqual(vm.stdout, bytes((data[0],) * 4 + (data[1],)))
                    self.assertEqual(vm.stderr, b"malbolge-steps-v1:8\n")

    def test_both_directions_and_step_spellings_reach_layout(self) -> None:
        """All unit-step forms reach layout without a VM-search matrix."""
        variants = (
            (0, 3, "i++"),
            (0, 3, "i += 1"),
            (0, 3, "i = i + 1"),
            (4, 1, "--i"),
            (4, 1, "i--"),
            (4, 1, "i -= 1"),
            (4, 1, "i = i - 1"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, (initial, bound, step) in enumerate(variants):
                with self.subTest(initial=initial, bound=bound, step=step):
                    source = Path(directory) / f"step-{index}.c"
                    guest = source.with_suffix(".malbolge")
                    _ = source.write_text(program(initial, bound, step))
                    admitted = subprocess.run(
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
                        timeout=10,
                    )
                    self.assertEqual(admitted.returncode, 1, admitted.stderr)
                    self.assertIn(
                        b"layout backend exited unsuccessfully",
                        admitted.stderr,
                    )
                    self.assertFalse(guest.exists())

    def test_descending_inequality_outputs_actual_guest_stream(self) -> None:
        """Descending C loop selects genuine reads in VM execution order."""
        source_text = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    for (int i = 4; i != 1; --i) {\n"
            "        if (i % 2 == 0) {\n"
            "            putchar(getchar());\n"
            "            continue;\n"
            "        }\n"
            "        putchar(getchar());\n"
            "    }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "descending.c"
            guest = source.with_suffix(".malbolge")
            _ = source.write_text(source_text)
            compiled = COMPILE(source, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (b"\x00\xff\x80", b"\xff\x00\x01"):
                vm = RUN(guest, data)
                self.assertEqual(vm.returncode, 0, vm.stderr)
                self.assertEqual(vm.stdout, data)
                self.assertEqual(vm.stderr, b"malbolge-steps-v1:7\n")

    def test_equal_bound_is_zero_trip_but_tail_reads_guest(self) -> None:
        """The first inequality check is false without touching the loop."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "zero-trip.c"
            guest = source.with_suffix(".malbolge")
            _ = source.write_text(program(initial=3, bound=3))
            compiled = COMPILE(source, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (b"\x00\xff", b"\xff\x00"):
                vm = RUN(guest, data)
                self.assertEqual(vm.returncode, 0, vm.stderr)
                self.assertEqual(vm.stdout, data)
                self.assertEqual(vm.stderr, b"malbolge-steps-v1:5\n")

    def test_divergent_or_oversized_loops_refuse_without_guest(self) -> None:
        """Opposite step direction or more than sixteen trips must refuse."""
        invalid = (
            program(4, 1, "++i"),
            program(0, 3, "--i"),
            program(0, 17, "++i"),
            program(4, 0, "i += 1"),
            program(1, 3, "i -= 1"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, source_text in enumerate(invalid):
                with self.subTest(index=index):
                    source = Path(directory) / f"invalid-{index}.c"
                    guest = source.with_suffix(".malbolge")
                    _ = source.write_text(source_text)
                    compiled = COMPILE(source, guest)
                    self.assertNotEqual(compiled.returncode, 0, source_text)
                    self.assertFalse(guest.exists(), source_text)

    def test_forged_step_direction_cannot_make_infinite_loop_finite(self) -> None:
        """Changing an assigned `+` AST to `-` cannot rewrite C semantics."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "divergent.c"
            _ = source.write_text(program(4, 1, "i = i + 1"))
            forged = NORMALIZED(source)
            nodes = cast("list[dict[str, object]]", forged["nodes"])
            step = next(
                node
                for node in nodes
                if node.get("kind") == "binary-expression"
                and node.get("operation") == "+"
                and cast("dict[str, dict[str, int]]", node["span"])["begin"]["line"]
                == 4
            )
            step["operation"] = "-"
            guest = Path(directory) / "forged-step.malbolge"
            result = PROJECT(forged, guest, source)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(guest.exists())

    def test_clang_comparator_or_coordinate_forgery_refuses(self) -> None:
        """Same-width <= AST spoofing cannot authorize source-spelled !=."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "unmodified.c"
            _ = source.write_text(program())
            normalized = NORMALIZED(source)
            cases = ("operation", "parent", "span", "bound", "initial")
            for field in cases:
                with self.subTest(field=field):
                    forged = copy.deepcopy(normalized)
                    nodes = cast("list[dict[str, object]]", forged["nodes"])
                    condition = next(
                        node
                        for node in nodes
                        if node.get("kind") == "binary-expression"
                        and node.get("operation") == "!="
                    )
                    if field == "operation":
                        condition["operation"] = "<="
                    elif field == "parent":
                        condition["parent"] = 0
                    elif field == "span":
                        span = cast("dict[str, dict[str, int]]", condition["span"])
                        span["begin"]["column"] += 1
                    else:
                        start = nodes.index(condition)
                        literal = nodes[start + (3 if field == "bound" else -1)]
                        literal["literal"] = "2"
                        literal["constant_integer"] = "2"
                    guest = Path(directory) / f"forged-{field}.malbolge"
                    result = PROJECT(forged, guest, source)
                    self.assertNotEqual(result.returncode, 0, field)
                    self.assertFalse(guest.exists(), field)


if __name__ == "__main__":
    _ = unittest.main()
