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
#   - Whole-source pure logical C conditions selecting real guest byte I/O.
# - Must-Not:
#   - Silently skip unknown short-circuit operands or guest input effects.
# - Allows:
#   - Inputs: pinned Clang normalized syntax and binary runtime streams.
#   - Outputs: normative VM comparisons and fail-closed source rejections.
#   - Side effects: isolated temporary compilation artifacts only.
# - Split-When:
#   - Guest-side dynamic condition evaluation implements this C subset.
# - Merge-When:
#   - Source-authenticated C static-condition proof becomes a common suite.
# - Summary:
#   - Checks !, parentheses, &&, || and relational subexpressions.

"""Pure folded C expressions must select source-proven runtime byte effects."""

from __future__ import annotations

import copy
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
ADAPTER = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT = ROOT / ".cache/rust/target/debug/malbolge_layout"
VM = ROOT / ".cache/rust/target/debug/malbolge"
INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"


def source(predicate: str) -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int first = getchar();\n"
        f"    if ({predicate}) {{\n"
        "        putchar(first);\n"
        "        putchar(putchar(getchar()));\n"
        "    } else {\n"
        "        getchar();\n"
        "        putchar(getchar());\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class StaticLogicalCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned frontend, adapter, layout, and VM required")

    @staticmethod
    def compile(path: Path, target: Path) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--capsule",
                "--output",
                str(target),
                str(path),
            ],
            capture_output=True,
            check=False,
            timeout=90,
        )

    @staticmethod
    def normalized(path: Path) -> dict[str, object]:
        built = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "static-logical",
                str(path),
            ],
            capture_output=True,
            check=False,
            timeout=20,
        )
        if built.returncode:
            raise AssertionError(built.stderr)
        return json.loads(built.stdout)

    def assert_guest_oracles(self, cases: tuple[tuple[str, bool], ...]) -> None:
        rng = random.Random(0x10A1CA1)
        boundary = b"\x00\xff\x80\x01"
        seeded = bytes(rng.getrandbits(8) for _ in range(4))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, (predicate, selected) in enumerate(cases):
                with self.subTest(predicate=predicate):
                    path = Path(directory) / f"logical-{index}.c"
                    target = Path(directory) / f"logical-{index}.malbolge"
                    path.write_text(source(predicate))
                    built = self.compile(path, target)
                    self.assertEqual(built.returncode, 0, built.stderr)
                    for data in (boundary, seeded) if index == 0 else (boundary,):
                        guest = subprocess.run(
                            [str(VM), str(target), "--input-stdin", "--report-steps"],
                            input=data,
                            capture_output=True,
                            check=False,
                            timeout=30,
                        )
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        expected = (
                            bytes((data[0], data[1], data[1], data[2]))
                            if selected
                            else bytes((data[2], data[3]))
                        )
                        self.assertEqual(guest.stdout, expected)
                        self.assertEqual(
                            guest.stderr,
                            f"malbolge-steps-v1:{8 if selected else 7}\n".encode(),
                        )

    def test_nested_logical_predicates_execute_guest_oracles(self) -> None:
        self.assert_guest_oracles(
            (
                ("!(1 == 2) && (3 > 1)", True),
                ("(0 || !0)", True),
                ("!(1 == 1) || (2 < 1)", False),
                ("2 == (2)", True),
                ("((0))", False),
                ("!!1", True),
            )
        )

    def test_pure_scalar_predicates_execute_guest_oracles(self) -> None:
        self.assert_guest_oracles(
            (
                ("!!0", False),
                ("0 && 23", False),
                ("2 && 3", True),
                ("0 || 19", True),
                ("(2 == 3) || (2 != 3)", True),
                ("(5 >= 3) && !(3 <= 1)", True),
                ("!!!!!!!1", False),
            )
        )

    def test_unproved_or_dynamic_operands_never_publish_guest_code(self) -> None:
        predicates = (
            "0 && getchar()",
            "1 || getchar()",
            "1 && (2 + 1)",
            "!(first)",
            "1 || (++first)",
            "1 && putchar(getchar())",
            "1 ^ 1",
            "1 & 1",
            "0 ? 1 : 2",
            "! 0",
            "( 1)",
            "1&&1",
            "1  && 1",
            "2 == (+2)",
            "!!!!!!!!0",  # Exceeds the eight-level bounded proof.
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, predicate in enumerate(predicates):
                with self.subTest(predicate=predicate):
                    path = Path(directory) / f"unsupported-{index}.c"
                    target = Path(directory) / f"unsupported-{index}.malbolge"
                    path.write_text(source(predicate))
                    built = self.compile(path, target)
                    self.assertNotEqual(built.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_recursive_condition_metadata_refuses_publication(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            path = Path(directory) / "original.c"
            path.write_text(source("!(1 == 2) && (3 > 1)"))
            original = self.normalized(path)
            nodes = original["nodes"]
            logical = next(n for n in nodes if n.get("operation") == "&&")
            negate = next(n for n in nodes if n.get("operation") == "!")
            first_paren = next(
                n for n in nodes if n["kind"] == "parenthesized-expression"
            )
            comparison = next(n for n in nodes if n.get("operation") == "==")
            literals = [n for n in nodes if n["kind"] == "integer-literal"]
            changes = (
                (logical["id"], "constant_integer", "0"),
                (logical["id"], "parent", 2),
                (logical["id"], "span.end.column", 1),
                (logical["id"], "operation", "+"),
                (negate["id"], "operation", "~"),
                (negate["id"], "constant_integer", "0"),
                (negate["id"], "type", "u32"),
                (first_paren["id"], "constant_integer", "1"),
                (first_paren["id"], "span.end.byte", 1),
                (first_paren["id"], "parent", 3),
                (comparison["id"], "constant_integer", "1"),
                (comparison["id"], "span.begin.column", 1),
                (literals[0]["id"], "literal", "3"),
                (literals[1]["id"], "parent", 3),
            )
            for index, (node_id, field, value) in enumerate(changes):
                with self.subTest(index=index, field=field):
                    forged = copy.deepcopy(original)
                    node = next(n for n in forged["nodes"] if n["id"] == node_id)
                    metadata = node
                    for component in field.split(".")[:-1]:
                        metadata = metadata[component]
                    metadata[field.split(".")[-1]] = value
                    target = Path(directory) / f"forged-{index}.malbolge"
                    built = subprocess.run(
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
                    self.assertNotEqual(built.returncode, 0)
                    self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
