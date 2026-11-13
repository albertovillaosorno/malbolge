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
#   - Nonzero ascending finite C induction and live binary guest I/O.
# - Must-Not:
#   - Trust mutated Clang induction evidence or host-replay guest input.
# - Allows:
#   - Inputs: pinned C, normalized evidence, binary stdin.
#   - Outputs: real VM parity and explicit unsupported C refusal.
#   - Side effects: temporary guest artifacts only.
# - Split-When:
#   - Runtime guest induction supersedes source-time finite proof.
# - Merge-When:
#   - Bounded induction-start proofs share one compiler contract.

"""Nonzero C loop starts retain exact guest effects and induction identity."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests import test_descending_static_for_c_pipeline as descending
from tests.test_assigned_step_static_for_c_pipeline import oracle, program
from tests.test_induction_static_for_c_pipeline import (
    ADAPTER,
    FRONTEND,
    LAYOUT,
    ROOT,
    VM,
)


class NonzeroStartStaticForCPipelineTests(unittest.TestCase):
    """Test complete admitted C streams on the normative Malbolge VM."""

    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler and normative guest VM required")

    def test_nonzero_starts_execute_complete_branching_streams(self) -> None:
        """Start values control nested output, continue and eventual break."""
        variants = (
            (2, "<", 4, "i = i + 1", 2, 3, range(2, 4)),
            (5, "<=", 6, "i++", 5, 6, range(5, 7)),
            (9, "<", 9, "++i", 8, 99, range(9, 9)),
            (5, "<", 2, "++i", 8, 99, range(5, 2)),
        )
        streams = (
            bytes((0, 255, 128, 1, 42, 11, 127, 233, 16, 99)),
            hashlib.shake_256(b"nonzero-ascending-guest").digest(10),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, (start, op, bound, step, first, last, trips) in enumerate(
                variants
            ):
                with self.subTest(variant=index):
                    path = root / f"start-{index}.c"
                    target = path.with_suffix(".malbolge")
                    path.write_text(
                        program(
                            initial=start,
                            operator=op,
                            bound=bound,
                            step=step,
                            first=first,
                            last=last,
                        )
                    )
                    compiled = descending.DescendingStaticForCPipelineTests.compile(
                        path, target
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    for data in streams:
                        expected, reads = oracle(trips, first, last, data)
                        guest = descending.DescendingStaticForCPipelineTests.run_guest(
                            target, data
                        )
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        self.assertEqual(guest.stdout, expected)
                        self.assertEqual(
                            guest.stderr,
                            f"malbolge-steps-v1:{reads + len(expected) + 1}\n".encode(),
                        )

    def test_nonzero_outer_with_shadowed_countdown(self) -> None:
        """Source-proven outer control cannot steal the inner induction."""
        source = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    for (int i = 2; i <= 2; i++) {\n"
            "        for (int i = 2; i >= 2; i--) {\n"
            "            putchar(getchar());\n"
            "        }\n"
            "        if (i == 2) {\n"
            "            putchar(getchar());\n"
            "            continue;\n"
            "        }\n"
            "        putchar(getchar());\n"
            "    }\n"
            "    putchar(getchar());\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            path = Path(directory) / "shadowed.c"
            target = path.with_suffix(".malbolge")
            path.write_text(source)
            compiled = descending.DescendingStaticForCPipelineTests.compile(
                path, target
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255, 128)),
                hashlib.shake_256(b"nonzero-shadowed").digest(3),
            ):
                guest = descending.DescendingStaticForCPipelineTests.run_guest(
                    target, data
                )
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(guest.stdout, data)
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:7\n")

    def test_unsupported_start_shapes_and_stride_fail_closed(self) -> None:
        """Wider literals, reverse steps and excessive trips are not proofs."""
        sources = (
            program(initial=10, operator="<", bound=12),
            program(initial=2, operator="<", bound=19),
            program(initial=2, operator="<", bound=6, step="i += 2"),
            program(initial=2, operator="<", bound=6, step="i = i + 2"),
            program(initial=2, operator=">", bound=0, step="++i"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, source in enumerate(sources):
                with self.subTest(index=index):
                    path = root / f"unsupported-{index}.c"
                    target = path.with_suffix(".malbolge")
                    path.write_text(source)
                    result = descending.DescendingStaticForCPipelineTests.compile(
                        path, target
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_initial_source_evidence_fails_closed(self) -> None:
        """The source-start value remains bound to the pinned Clang node."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "original.c"
            path.write_text(program(initial=2, bound=6, first=3, last=5))
            original = descending.DescendingStaticForCPipelineTests.normalized(path)
            for index, (field, value) in enumerate(
                (
                    ("literal", "3"),
                    ("constant_integer", "3"),
                    ("span.begin.byte", 0),
                    ("span.end.column", 0),
                    ("parent", 999),
                )
            ):
                with self.subTest(field=field):
                    forged = copy.deepcopy(original)
                    nodes = forged["nodes"]
                    loop = next(n for n in nodes if n["kind"] == "for-statement")
                    declaration = next(
                        n
                        for n in nodes
                        if n["kind"] == "declaration-statement"
                        and n["parent"] == loop["id"]
                    )
                    variable = next(
                        n
                        for n in nodes
                        if n["kind"] == "variable-declaration"
                        and n["parent"] == declaration["id"]
                    )
                    initial = next(
                        n
                        for n in nodes
                        if n["kind"] == "integer-literal"
                        and n["parent"] == variable["id"]
                    )
                    target = initial
                    keys = field.split(".")
                    for key in keys[:-1]:
                        target = target[key]
                    target[keys[-1]] = value
                    output = root / f"forged-{index}.malbolge"
                    result = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(output),
                            "--capsule",
                        ],
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
