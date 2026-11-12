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
#   - Source-proven nonzero decimal C condition guest I/O acceptance.
# - Must-Not:
#   - Evaluate dynamic conditions on the host or forge guest byte outputs.
# - Allows:
#   - Inputs: pinned C frontend, canonical adapter, binary guest input.
#   - Outputs: VM parity and refusal under malformed source or AST metadata.
#   - Side effects: isolated temporary artifacts only.
# - Split-When:
#   - General guest runtime control flow owns source condition evaluation.
# - Merge-When:
#   - Adjacent literal-condition suite owns decimal source proofs.
# - Summary:
#   - Proves decimal C truthiness and multiline source coordinates.

"""End-to-end proof for source-checked decimal integer C conditions."""

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
        "        putchar(getchar());\n"
        "    }\n"
        "    if (0) {\n"
        "        getchar();\n"
        "        putchar(getchar());\n"
        "    } else {\n"
        "        putchar(getchar());\n"
        "    }\n"
        "}\n"
    )


class DecimalStaticCPipelineTests(unittest.TestCase):
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
        result = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "decimal-condition",
                str(path),
            ],
            capture_output=True,
            check=False,
            timeout=20,
        )
        if result.returncode:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)

    def test_nonzero_decimal_condition_executes_multiline_guest_oracles(self) -> None:
        rng = random.Random(0xDEC1A1)
        samples = [b"\x00\xff\x80", b"\xff\x00\x01", b"ABC"]
        samples += [bytes(rng.getrandbits(8) for _ in range(3)) for _ in range(5)]
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for literal in ("2", "23", "2147483647"):
                with self.subTest(literal=literal):
                    path = Path(directory) / f"nonzero-{literal}.c"
                    target = Path(directory) / f"nonzero-{literal}.malbolge"
                    path.write_text(source(literal))
                    built = self.compile(path, target)
                    self.assertEqual(built.returncode, 0, built.stderr)
                    for data in samples:
                        guest = subprocess.run(
                            [str(VM), str(target), "--input-stdin", "--report-steps"],
                            input=data,
                            capture_output=True,
                            check=False,
                            timeout=30,
                        )
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        self.assertEqual(
                            guest.stdout,
                            bytes((data[0], data[1], data[1], data[2])),
                        )
                        self.assertEqual(guest.stderr, b"malbolge-steps-v1:8\n")

    def test_unproved_numeric_expressions_refuse_publication(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, predicate in enumerate(
                ("-1", "1 + 2", "0x10", "0007", "2147483648", "getchar()")
            ):
                with self.subTest(predicate=predicate):
                    path = Path(directory) / f"bad-{index}.c"
                    target = Path(directory) / f"bad-{index}.malbolge"
                    path.write_text(source(predicate))
                    built = self.compile(path, target)
                    self.assertNotEqual(built.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_decimal_condition_metadata_refuses_publication(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            path = Path(directory) / "decimal.c"
            path.write_text(source("23"))
            original = self.normalized(path)
            branch = next(
                node for node in original["nodes"] if node["kind"] == "if-statement"
            )
            literal = next(
                node
                for node in original["nodes"]
                if node["parent"] == branch["id"] and node["kind"] == "integer-literal"
            )
            arm = next(
                node
                for node in original["nodes"]
                if node["parent"] == branch["id"]
                and node["kind"] == "compound-statement"
            )
            changes = (
                (branch["id"], "span.begin.byte", 1),
                (branch["id"], "span.begin.column", 1),
                (literal["id"], "literal", "24"),
                (literal["id"], "literal", "0023"),
                (literal["id"], "constant_integer", "24"),
                (literal["id"], "span.begin.byte", 1),
                (literal["id"], "span.end.byte", 1),
                (literal["id"], "span.end.column", 1),
                (literal["id"], "type_name", "u32"),
                (arm["id"], "span.begin.column", 1),
                (arm["id"], "span.end.column", 1),
                (arm["id"], "parent", 2),
            )
            for index, (node_id, field, value) in enumerate(changes):
                with self.subTest(index=index, field=field):
                    forged = copy.deepcopy(original)
                    node = next(n for n in forged["nodes"] if n["id"] == node_id)
                    parent = node
                    for part in field.split(".")[:-1]:
                        parent = parent[part]
                    parent[field.split(".")[-1]] = value
                    target = Path(directory) / f"forged-{index}.malbolge"
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
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
