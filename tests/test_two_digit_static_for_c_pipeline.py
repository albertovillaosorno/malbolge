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
#   - Two-digit finite C induction starts and full binary VM parity.
# - Must-Not:
#   - Admit forged source extents or host-compute live guest bytes.
# - Allows:
#   - Inputs: pinned C, forged normalized nodes, runtime byte streams.
#   - Outputs: compiled guest parity and explicit unsupported diagnostics.
#   - Side effects: temporary guest artifacts only.
# - Split-When:
#   - General guest-side induction makes finite source proof obsolete.
# - Merge-When:
#   - Other bounded exact Clang for-loop proofs own the same behavior.
# - Summary:
#   - Two-digit induction starts retain exact source geometry and I/O.

"""Two-digit counted loops retain actual C control and runtime byte I/O."""

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


class TwoDigitStaticForCPipelineTests(unittest.TestCase):
    """Witness complete loops in actual Malbolge, not host I/O."""

    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler and normative VM required")

    def test_two_digit_starts_match_independent_binary_oracles(self) -> None:
        """Forward, reverse, inclusive, zero-trip and assigned steps work."""
        cases = (
            (12, ">=", 10, "i--", 11, 10, range(12, 9, -1)),
            (19, ">", 16, "i = i - 1", 18, 17, range(19, 16, -1)),
            (10, "<=", 12, "i++", 11, 12, range(10, 13)),
            (98, "<=", 99, "i += 1", 98, 99, range(98, 100)),
            (99, "<", 99, "++i", 97, 98, range(0)),
        )
        streams = (
            bytes((0, 255, 128, 1, 42, 11, 127, 233, 16, 99)),
            hashlib.shake_256(b"two-digit-static-guest").digest(10),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, (start, op, bound, step, first, last, trips) in enumerate(cases):
                with self.subTest(case=index):
                    source = root / f"case-{index}.c"
                    target = source.with_suffix(".malbolge")
                    source.write_text(
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
                        source, target
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    for data in streams:
                        expected, reads = oracle(trips, first, last, data)
                        vm = descending.DescendingStaticForCPipelineTests.run_guest(
                            target, data
                        )
                        self.assertEqual(vm.returncode, 0, vm.stderr)
                        self.assertEqual(vm.stdout, expected)
                        self.assertEqual(
                            vm.stderr,
                            f"malbolge-steps-v1:{reads + len(expected) + 1}\n".encode(),
                        )

    def test_nested_two_digit_counter_keeps_distinct_runtime_reads(self) -> None:
        """An inner counter shadows the outer with no repeated guest byte."""
        source = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    for (int i = 10; i <= 11; ++i) {\n"
            "        for (int i = 2; i >= 1; --i) {\n"
            "            putchar(getchar());\n"
            "        }\n"
            "        putchar(getchar());\n"
            "    }\n"
            "    putchar(getchar());\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            path = Path(directory) / "nested.c"
            target = path.with_suffix(".malbolge")
            path.write_text(source)
            compiled = descending.DescendingStaticForCPipelineTests.compile(
                path, target
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255, 128, 1, 42, 11, 127)),
                hashlib.shake_256(b"two-digit-shadowed").digest(7),
            ):
                vm = descending.DescendingStaticForCPipelineTests.run_guest(
                    target, data
                )
                self.assertEqual(vm.returncode, 0, vm.stderr)
                self.assertEqual(vm.stdout, data)
                self.assertEqual(vm.stderr, b"malbolge-steps-v1:15\n")

    def test_invalid_two_digit_initializer_forms_fail_closed(self) -> None:
        """No three digits, signed starts, noncanonical zero or long trips."""
        sources = (
            program(initial=100, bound=102, first=100, last=101),
            program(initial=-10, bound=0, first=1, last=3),
            program(initial=10, bound=30, first=11, last=29),
            program(initial=12, operator=">=", bound=10, step="i++"),
            program(initial=10, bound=12, step="i += 2"),
            program(initial=10, bound=12).replace("i = 10", "i = 010"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, source in enumerate(sources):
                with self.subTest(case=index):
                    path = Path(directory) / f"invalid-{index}.c"
                    target = path.with_suffix(".malbolge")
                    path.write_text(source)
                    result = descending.DescendingStaticForCPipelineTests.compile(
                        path, target
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_initial_geometry_refuses_publication(self) -> None:
        """Every two-digit literal and declaration extent stays authenticated."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "source.c"
            path.write_text(program(initial=12, operator=">=", bound=10, step="i--"))
            original = descending.DescendingStaticForCPipelineTests.normalized(path)
            nodes = original["nodes"]
            loop = next(node for node in nodes if node["kind"] == "for-statement")
            declaration = next(
                node
                for node in nodes
                if node["kind"] == "declaration-statement"
                and node["parent"] == loop["id"]
            )
            variable = next(
                node
                for node in nodes
                if node["kind"] == "variable-declaration"
                and node["parent"] == declaration["id"]
            )
            initial = next(
                node
                for node in nodes
                if node["kind"] == "integer-literal"
                and node["parent"] == variable["id"]
            )
            changes = (
                (initial["id"], "literal", "13"),
                (initial["id"], "constant_integer", "13"),
                (initial["id"], "span.end.byte", 1),
                (initial["id"], "span.begin.column", 1),
                (declaration["id"], "span.end.column", 1),
                (variable["id"], "span.end.byte", 1),
                (loop["id"], "parent", 999),
            )
            for index, (node_id, field, value) in enumerate(changes):
                with self.subTest(field=field):
                    forged = copy.deepcopy(original)
                    node = next(n for n in forged["nodes"] if n["id"] == node_id)
                    keys = field.split(".")
                    field_target = node
                    for key in keys[:-1]:
                        field_target = field_target[key]
                    field_target[keys[-1]] = value
                    target = root / f"forged-{index}.malbolge"
                    result = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(target),
                            "--capsule",
                        ],
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
