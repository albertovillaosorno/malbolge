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
#   - Source-proven remainder predicates for finite C induction with guest I/O.
# - Must-Not:
#   - Fold live guest input or trust forged Clang remainder subtrees.
# - Allows:
#   - Inputs: pinned C, binary stdin, and adversarial normalized JSON.
#   - Outputs: real Malbolge guest parity or explicit refusal.
#   - Side effects: temporary target files only.
# - Split-When:
#   - General guest-side induction arithmetic replaces static proof.
# - Merge-When:
#   - A general authenticated induction expression evaluator exists.
# - Summary:
#   - Pure counter remainder branches select real guest byte effects.

"""Source-authenticated modulo branches preserve actual VM byte effects."""

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


def program(first: str = "i % 2 == 0", second: str = "i % 3 == 0") -> str:
    """Interleave modulo branches, nested byte output and early loop exits."""
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    for (int i = 12; i >= 8; i -= 1) {\n"
        "        int current = getchar();\n"
        f"        if ({first}) {{\n"
        "            putchar(putchar(current));\n"
        "            continue;\n"
        "        }\n"
        f"        if ({second}) {{\n"
        "            break;\n"
        "        }\n"
        "        putchar(current);\n"
        "        putchar(getchar());\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


def oracle(first: Pred, second: Pred, data: bytes) -> tuple[bytes, int]:
    """Execute the independent finite C control model, not adapter IR."""
    output = bytearray()
    reads = 0
    for i in range(12, 7, -1):
        current = data[reads]
        reads += 1
        if first(i):
            output.extend((current, current))
            continue
        if second(i):
            break
        output.append(current)
        output.append(data[reads])
        reads += 1
    output.append(data[reads])
    return bytes(output), reads + 1


class ModularInductionForCPipelineTests(unittest.TestCase):
    """Run whole source C programs in the normative guest interpreter."""

    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C/JSON/target/VM tooling required")

    def test_modulo_predicates_execute_real_guest_binary_streams(self) -> None:
        """Descending, unary, grouped and logical predicates preserve I/O."""
        cases: tuple[tuple[str, str, Pred, Pred], ...] = (
            ("i % 2 == 0", "i % 3 == 0", lambda i: i % 2 == 0, lambda i: i % 3 == 0),
            ("i % 2", "i % 3 == 0", lambda i: bool(i % 2), lambda i: i % 3 == 0),
            ("!(i % 2)", "i % 3 != 2", lambda i: not i % 2, lambda i: i % 3 != 2),
            ("i % 11 == 1", "i % 3 == 0", lambda i: i % 11 == 1, lambda i: i % 3 == 0),
            ("i % 2 <= 0", "i % 3 == 0", lambda i: i % 2 <= 0, lambda i: i % 3 == 0),
            (
                "(i % 2 == 0) || (i % 3 == 1)",
                "i % 3 == 0",
                lambda i: i % 2 == 0 or i % 3 == 1,
                lambda i: i % 3 == 0,
            ),
        )
        streams = (
            bytes((0, 255, 128, 1, 42, 9, 27, 45, 200, 7, 3, 99)),
            hashlib.shake_256(b"modular-induction-2230").digest(12),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, (first, second, first_oracle, second_oracle) in enumerate(cases):
                with self.subTest(case=index):
                    source = root / f"mod-{index}.c"
                    target = source.with_suffix(".malbolge")
                    source.write_text(program(first, second), encoding="utf-8")
                    compiled = descending.DescendingStaticForCPipelineTests.compile(
                        source, target
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    for data in streams:
                        expected, reads = oracle(first_oracle, second_oracle, data)
                        guest = descending.DescendingStaticForCPipelineTests.run_guest(
                            target, data
                        )
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        self.assertEqual(guest.stdout, expected)
                        self.assertEqual(
                            guest.stderr,
                            f"malbolge-steps-v1:{reads + len(expected) + 1}\n".encode(),
                        )

    def test_zero_trip_remainder_body_is_authenticated_without_guest_effects(
        self,
    ) -> None:
        """Dead loop bodies must prove modulo nodes, never read guest bytes."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "zero-trip.c"
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
            invalid = root / "dead-unsupported.c"
            invalid_target = invalid.with_suffix(".malbolge")
            invalid.write_text(
                program(first="current % 2 == 0").replace("i >= 8", "i > 12"),
                encoding="utf-8",
            )
            rejected = descending.DescendingStaticForCPipelineTests.compile(
                invalid, invalid_target
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertFalse(invalid_target.exists())

    def test_nested_shadowed_remainders_preserve_fresh_guest_reads(self) -> None:
        """The same `i` name in a nested loop binds the correct induction."""
        source_text = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    for (int i = 12; i >= 11; --i) {\n"
            "        for (int i = 2; i >= 1; --i) {\n"
            "            if (i % 2 == 0) {\n"
            "                putchar(getchar());\n"
            "                continue;\n"
            "            }\n"
            "            putchar(getchar());\n"
            "            putchar(getchar());\n"
            "        }\n"
            "        putchar(getchar());\n"
            "    }\n"
            "    putchar(getchar());\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "nested.c"
            target = source.with_suffix(".malbolge")
            source.write_text(source_text, encoding="utf-8")
            compiled = descending.DescendingStaticForCPipelineTests.compile(
                source, target
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255, 128, 1, 42, 9, 27, 45, 200)),
                hashlib.shake_256(b"modulo-shadowed").digest(9),
            ):
                guest = descending.DescendingStaticForCPipelineTests.run_guest(
                    target, data
                )
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(guest.stdout, data)
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:19\n")

    def test_unsupported_guest_dependent_remainders_refuse_publication(self) -> None:
        """Only pure protected counters with nonzero literal divisors fold."""
        sources = (
            program(first="current % 2 == 0"),
            program(first="i % 0 == 0"),
            program(first="i % getchar() == 0"),
            program(first="2 % i == 0"),
            program(first="i / 2 == 0"),
            program(first="i % 2 + 1 == 0"),
            program(first="i % 2 == getchar()"),
            program(first="i % 2 == 0").replace("i % 3 == 0", "current % 3 == 0"),
            program(first="i % 00 == 0"),
            program(first="i % -2 == 0"),
            program(first="i % 2U == 0"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, text in enumerate(sources):
                with self.subTest(index=index):
                    source = Path(directory) / f"invalid-{index}.c"
                    target = source.with_suffix(".malbolge")
                    source.write_text(text, encoding="utf-8")
                    result = descending.DescendingStaticForCPipelineTests.compile(
                        source, target
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_remainder_nodes_refuse_publication(self) -> None:
        """Divisor, operator, ancestry and positional evidence all matter."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "original.c"
            source.write_text(program(), encoding="utf-8")
            original = descending.DescendingStaticForCPipelineTests.normalized(source)
            nodes = original["nodes"]
            remainder = next(n for n in nodes if n.get("operation") == "%")
            comparison = next(n for n in nodes if n["id"] == remainder["parent"])
            cast = next(n for n in nodes if n["parent"] == remainder["id"])
            variable = next(n for n in nodes if n["parent"] == cast["id"])
            divisor = next(
                n
                for n in nodes
                if n["parent"] == remainder["id"] and n["kind"] == "integer-literal"
            )
            expected = next(
                n
                for n in nodes
                if n["parent"] == comparison["id"] and n["kind"] == "integer-literal"
            )
            changes = (
                (remainder["id"], "operation", "/"),
                (remainder["id"], "type", "u32"),
                (remainder["id"], "parent", 999),
                (remainder["id"], "span.end.byte", 1),
                (cast["id"], "operation", "integral-cast"),
                (variable["id"], "reference", "i@999"),
                (divisor["id"], "literal", "0"),
                (divisor["id"], "constant_integer", "0"),
                (divisor["id"], "span.begin.column", 1),
                (expected["id"], "parent", 999),
                (comparison["id"], "span.end.column", 1),
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
