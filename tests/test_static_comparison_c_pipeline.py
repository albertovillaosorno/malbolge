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
#   - Source-checked constant C comparisons selecting real guest byte I/O.
# - Must-Not:
#   - Compute input-dependent branches on the host or hide skipped C effects.
# - Allows:
#   - Inputs: pinned C frontend, binary stdin and normalized AST mutations.
#   - Outputs: independent normative VM oracles and closed refusal.
#   - Side effects: isolated temporary output artifacts only.
# - Split-When:
#   - Runtime guest Boolean evaluation replaces static source proof.
# - Merge-When:
#   - General guest control-flow tests establish the same boundary.
# - Summary:
#   - Checks six decimal relational operators and guest I/O branch effects.

"""Complete C comparisons must select source-proven guest I/O effects."""

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


class StaticComparisonCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C frontend, adapter, layout and VM required")

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
                "comparison-condition",
                str(path),
            ],
            capture_output=True,
            check=False,
            timeout=20,
        )
        if built.returncode:
            raise AssertionError(built.stderr)
        return json.loads(built.stdout)

    def test_relational_and_equality_branches_execute_real_guest_io(self) -> None:
        cases = (
            ("2 == 2", True),
            ("2 != 2", False),
            ("4 > 3", True),
            ("4 < 3", False),
            ("7 >= 7", True),
            ("7 <= 6", False),
            ("2147483647 > 0", True),
            ("0 <= 2147483647", True),
        )
        rng = random.Random(0xC0A1C0DE)
        boundary = b"\x00\xff\x80\x02"
        seeded = bytes(rng.getrandbits(8) for _ in range(4))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, (predicate, selected) in enumerate(cases):
                with self.subTest(predicate=predicate):
                    path = Path(directory) / f"comparison-{index}.c"
                    target = Path(directory) / f"comparison-{index}.malbolge"
                    path.write_text(source(predicate))
                    built = self.compile(path, target)
                    self.assertEqual(built.returncode, 0, built.stderr)
                    # One binary replay per operator plus a second seeded
                    # stream on both outcomes; the current VM is memory-heavy.
                    inputs = (boundary, seeded) if index < 2 else (boundary,)
                    for data in inputs:
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
                        steps = 8 if selected else 7
                        self.assertEqual(
                            guest.stderr,
                            f"malbolge-steps-v1:{steps}\n".encode(),
                        )

    def test_dynamic_and_unproved_comparisons_refuse_publication(self) -> None:
        predicates = (
            "getchar() == 0",
            "first == 0",
            "2 + 1 == 3",
            "2 == (2)",
            "2==2",
            "-1 < 0",
            "2147483648 > 0",
            "0x10 == 16",
            "01 == 1",
            "2 & 2",
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

    def test_corrupted_comparison_ast_refuses_publication(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            path = Path(directory) / "original.c"
            path.write_text(source("2 == 2"))
            original = self.normalized(path)
            comparison = next(
                n for n in original["nodes"] if n["kind"] == "binary-expression"
            )
            operands = [n for n in original["nodes"] if n["parent"] == comparison["id"]]
            changes = (
                (comparison["id"], "operation", "!="),
                (comparison["id"], "type", "u32"),
                (comparison["id"], "constant_integer", "0"),
                (comparison["id"], "parent", 2),
                (comparison["id"], "span.end.column", 1),
                (operands[0]["id"], "literal", "3"),
                (operands[0]["id"], "constant_integer", "3"),
                (operands[0]["id"], "parent", 2),
                (operands[0]["id"], "span.begin.byte", 1),
                (operands[1]["id"], "literal", "1"),
                (operands[1]["id"], "constant_integer", "1"),
                (operands[1]["id"], "span.end.column", 1),
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
