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
#   - Pure induction ternaries selecting real guest binary byte effects.
# - Must-Not:
#   - Read runtime byte values on the host or trust forged ternary ancestry.
# - Allows:
#   - Inputs: pinned Clang C, binary stdin and adversarial normalized JSON.
#   - Outputs: normative VM parity and explicit unsupported diagnostics.
#   - Side effects: isolated temporary guest artifacts only.
# - Split-When:
#   - Dynamic guest ternary evaluation is independently implemented.
# - Merge-When:
#   - A general authenticated induction predicate evaluator subsumes this.
# - Summary:
#   - Proven ?: branches choose real VM input and output traces.

"""Authenticate C induction ternaries without folding guest byte effects."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path

from tests import test_descending_static_for_c_pipeline as descending
from tests.test_induction_static_for_c_pipeline import (
    ADAPTER,
    FRONTEND,
    LAYOUT,
    ROOT,
    VM,
)

Pred = Callable[[int], bool]


def program(first: str = "i % 2 == 0 ? i == 12 : i == 11") -> str:
    """Preserve live input through branch, continue, break, and final read."""
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    for (int i = 12; i >= 8; i--) {\n"
        "        int current = getchar();\n"
        f"        if ({first}) {{\n"
        "            putchar(putchar(current));\n"
        "            continue;\n"
        "        }\n"
        "        if (i == 9) {\n"
        "            break;\n"
        "        }\n"
        "        putchar(current);\n"
        "        putchar(getchar());\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


def oracle(first: Pred, data: bytes) -> tuple[bytes, int]:
    """Evaluate the independent finite source-C control model."""
    output = bytearray()
    reads = 0
    for i in range(12, 7, -1):
        current = data[reads]
        reads += 1
        if first(i):
            output.extend((current, current))
            continue
        if i == 9:
            break
        output.append(current)
        output.append(data[reads])
        reads += 1
    output.append(data[reads])
    return bytes(output), reads + 1


CASES: tuple[tuple[str, Pred], ...] = (
    (
        "i % 2 == 0 ? i == 12 : i == 11",
        lambda i: (i == 12) if (i % 2 == 0) else (i == 11),
    ),
    (
        "i % 3 ? i == 10 : i == 12",
        lambda i: (i == 10) if (i % 3) else (i == 12),
    ),
    (
        "i >= 11 ? i % 2 : i == 9",
        lambda i: bool(i % 2) if (i >= 11) else (i == 9),
    ),
    (
        "i == 12 ? (i == 12 ? i % 2 == 0 : i == 8) : i == 10",
        lambda i: ((i % 2 == 0) if i == 12 else (i == 8)) if i == 12 else i == 10,
    ),
    (
        "(i == 12 ? i % 2 == 0 : i % 3 == 1) && i >= 9",
        lambda i: ((i % 2 == 0) if i == 12 else (i % 3 == 1)) and i >= 9,
    ),
)


class TernaryInductionForCPipelineTests(unittest.TestCase):
    """Run complete C ternary streams in the actual normative guest VM."""

    def setUp(self) -> None:
        if not all(tool.is_file() for tool in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned frontend, adapter, layout and VM required")

    def test_ternary_predicates_execute_real_guest_binary_streams(self) -> None:
        """Separate source-proof and byte parity across two C ternaries."""
        self.assert_ternary_cases(CASES[:2])

    def test_ternary_grouped_and_nested_predicates(self) -> None:
        """Exercise nested ternary and logical grouping with real byte I/O."""
        self.assert_ternary_cases(CASES[2:4])

    def test_ternary_logical_composition(self) -> None:
        """Prove both ternary arms beneath a larger logical C predicate."""
        self.assert_ternary_cases(CASES[4:])

    def assert_ternary_cases(self, cases: tuple[tuple[str, Pred], ...]) -> None:
        """Use independent source-C control and step oracle for every case."""
        streams = (
            bytes((0, 255, 128, 1, 42, 9, 27, 45, 200, 7, 3, 99)),
            hashlib.shake_256(b"source-ternary-induction-2300").digest(12),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, (predicate, first_oracle) in enumerate(cases):
                with self.subTest(case=index):
                    source = root / f"ternary-{index}.c"
                    target = source.with_suffix(".malbolge")
                    source.write_text(program(predicate), encoding="utf-8")
                    compiled = descending.DescendingStaticForCPipelineTests.compile(
                        source, target
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    for data in streams:
                        expected, reads = oracle(first_oracle, data)
                        guest = descending.DescendingStaticForCPipelineTests.run_guest(
                            target, data
                        )
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        self.assertEqual(guest.stdout, expected)
                        self.assertEqual(
                            guest.stderr,
                            f"malbolge-steps-v1:{reads + len(expected) + 1}\n".encode(),
                        )

    def test_zero_trip_ternary_body_proves_children_without_guest_effects(
        self,
    ) -> None:
        """Unreachable input and ternary arms remain AST-checked, never run."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "empty.c"
            target = source.with_suffix(".malbolge")
            source.write_text(program().replace("i >= 8", "i > 12"), encoding="utf-8")
            compiled = descending.DescendingStaticForCPipelineTests.compile(
                source, target
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (bytes((0, 255)), bytes((128, 1))):
                guest = descending.DescendingStaticForCPipelineTests.run_guest(
                    target, data
                )
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(guest.stdout, data[:1])
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:3\n")
            invalid_source = root / "invalid-empty.c"
            invalid_target = invalid_source.with_suffix(".malbolge")
            invalid_source.write_text(
                program("i % 2 ? i == 12 : getchar()").replace("i >= 8", "i > 12"),
                encoding="utf-8",
            )
            rejected = descending.DescendingStaticForCPipelineTests.compile(
                invalid_source, invalid_target
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertFalse(invalid_target.exists())

    def test_nested_shadowed_ternaries_keep_live_guest_reads(self) -> None:
        """Two lexical counters independently select nested byte effects."""
        source_text = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    for (int i = 12; i >= 11; --i) {\n"
            "        for (int i = 2; i >= 1; --i) {\n"
            "            int current = getchar();\n"
            "            if (i % 2 == 0 ? i == 2 : i == 0) {\n"
            "                putchar(putchar(current));\n"
            "                continue;\n"
            "            }\n"
            "            putchar(current);\n"
            "        }\n"
            "        putchar(getchar());\n"
            "    }\n"
            "    putchar(getchar());\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "nested.c"
            target = source.with_suffix(".malbolge")
            source.write_text(source_text, encoding="utf-8")
            compiled = descending.DescendingStaticForCPipelineTests.compile(
                source, target
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255, 128, 1, 42, 9, 27, 45, 200)),
                hashlib.shake_256(b"source-ternary-shadow-2300").digest(9),
            ):
                guest = descending.DescendingStaticForCPipelineTests.run_guest(
                    target, data
                )
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(
                    guest.stdout,
                    bytes(
                        (
                            data[0],
                            data[0],
                            data[1],
                            data[2],
                            data[3],
                            data[3],
                            data[4],
                            data[5],
                            data[6],
                        )
                    ),
                )
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:17\n")

    def test_unsupported_ternary_operands_refuse_publication(self) -> None:
        """Neither a selected nor unselected arm may hide runtime effects."""
        sources = (
            program("current ? i == 12 : i == 11"),
            program("i % 2 ? current : i == 11"),
            program("i % 2 ? i == 12 : getchar()"),
            program("i % 2 ? i == 12 : (i = 3)"),
            program("i % 2 ? putchar(current) : i == 11"),
            program("i / 2 ? i == 12 : i == 11"),
            program("i % 2 ? i / 2 == 6 : i == 11"),
            program("i % 2 ? i == 12 : current % 2"),
            program("i % 2 ? i == 12 : i % 0"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, contents in enumerate(sources):
                with self.subTest(index=index):
                    source = root / f"invalid-{index}.c"
                    target = source.with_suffix(".malbolge")
                    source.write_text(contents, encoding="utf-8")
                    rejected = descending.DescendingStaticForCPipelineTests.compile(
                        source, target
                    )
                    self.assertNotEqual(rejected.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_ternary_ancestry_refuses_publication(self) -> None:
        """Every child binding, source position and kind is authenticated."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "original.c"
            source.write_text(program(), encoding="utf-8")
            original = descending.DescendingStaticForCPipelineTests.normalized(source)
            nodes = original["nodes"]
            ternary = next(n for n in nodes if n["kind"] == "conditional-expression")
            children = [n for n in nodes if n["parent"] == ternary["id"]]
            self.assertEqual(len(children), 3)
            first, middle, last = children
            changes = (
                (ternary["id"], "kind", "binary-expression"),
                (ternary["id"], "operation", "?"),
                (ternary["id"], "parent", 999),
                (ternary["id"], "span.begin.column", 1),
                (ternary["id"], "span.end.byte", 1),
                (first["id"], "parent", 999),
                (first["id"], "span.end.column", 1),
                (middle["id"], "parent", 999),
                (middle["id"], "span.begin.byte", 1),
                (last["id"], "parent", 999),
                (last["id"], "span.begin.column", 1),
                (last["id"], "span.end.line", 1),
            )
            for index, (node_id, field, value) in enumerate(changes):
                with self.subTest(index=index):
                    forged = copy.deepcopy(original)
                    node = next(n for n in forged["nodes"] if n["id"] == node_id)
                    nested = node
                    parts = field.split(".")
                    for part in parts[:-1]:
                        nested = nested[part]
                    nested[parts[-1]] = value
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
