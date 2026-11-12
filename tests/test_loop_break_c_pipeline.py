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
#   - Source-proven nested do/while Fibonacci guest parity and refusals.
# - Must-Not:
#   - Substitute host-computed stdout for real guest VM output.
# - Allows:
#   - Inputs: pinned source C and forged normalized Clang metadata.
#   - Outputs: normative VM bytes or explicit unsupported diagnostics.
#   - Side effects: isolated compiler and guest execution.
# - Split-When:
#   - General source-authenticated loop composition replaces finite replay.
# - Merge-When:
#   - Independent guest control-flow conformance covers nested C loops.
# - Summary:
#   - An unbraced inner while breaks into its outer post-test do.

"""Guest nested post-test loop parity and source integrity."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT / "tests/compiler/c-frontend/accepted/"
    "local_unbraced_do_while_inner_fibonacci.c"
)
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
ADAPTER = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT = ROOT / ".cache/rust/target/debug/malbolge_layout"
VM = ROOT / ".cache/rust/target/debug/malbolge"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"


def independent_oracle(batch_size: int, batches: int) -> bytes:
    a, b = 1, 1
    output = bytearray()
    for _ in range(batches):
        for _ in range(batch_size):
            next_value = (a + b) & 255
            if next_value & 1:
                output.append((next_value ^ 26) & 31)
            else:
                output.append(next_value & 31)
            a, b = b, next_value
    return bytes(output)


class DoWhileInnerPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(p.is_file() for p in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler binaries not built")

    def compile(
        self, source: Path, guest: Path, timeout: int = 120
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/unbraced-do-inner-while-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=timeout,
            env={**os.environ, "TMPDIR": str(ROOT / ".temp")},
        )

    def assert_real_guest(self, source: Path, batch_size: int, batches: int) -> None:
        expected = independent_oracle(batch_size, batches)
        self.assertEqual(expected, bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "nested-do-while.malbolge"
            result = self.compile(source, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                run = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, expected)
                self.assertEqual(run.stderr, b"malbolge-steps-v1:47\n")

    def test_complete_nested_do_while_guest(self) -> None:
        self.assert_real_guest(SOURCE, 2, 6)

    def test_four_per_do_trip_guest(self) -> None:
        original = SOURCE.read_text()
        self.assertEqual(original.count("target += 2U;"), 1)
        modified = (
            original.replace("unsigned target = 2U;", "unsigned target = 4U;")
            .replace("phase & 1U", "phase & 3U")
            .replace("target += 2U;", "target += 4U;")
            .replace("completed < 6U", "completed < 3U")
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "four-per-batch.c"
            source.write_text(modified)
            self.assert_real_guest(source, 4, 3)

    def test_invalid_source_refuses_publication(self) -> None:
        original = SOURCE.read_text()
        variants = {
            "hidden-input": original.replace(
                "            a = b;",
                "            getchar();\n            a = b;",
            ),
            "unreachable-output": original.replace(
                "                break;",
                "                break;\n                putchar(90);",
            ),
            "unreachable-write": original.replace(
                "                break;",
                "                break;\n                a = 0U;",
            ),
            "nonterminating-inner": original.replace(
                "                break;", "                continue;"
            ),
            "selected-zero-divisor": original.replace("next & 31U", "next / 0U"),
            "effectful-do-predicate": original.replace(
                "while (completed < 6U)", "while (++completed < 6U)"
            ),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, source_text in variants.items():
                with self.subTest(source=label):
                    source = Path(scratch) / f"{label}.c"
                    source.write_text(source_text)
                    guest = source.with_suffix(".malbolge")
                    result = self.compile(source, guest, timeout=8)
                    self.assertNotEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(guest.exists())

    def test_forged_nested_loop_nodes_refuse_publication(self) -> None:
        normalized = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/unbraced-do-inner-ast-v1",
                str(SOURCE),
            ],
            capture_output=True,
            check=False,
            timeout=30,
            env={**os.environ, "TMPDIR": str(ROOT / ".temp")},
        )
        self.assertEqual(normalized.returncode, 0, normalized.stderr)
        artifact = json.loads(normalized.stdout)
        nodes = artifact["nodes"]
        outer = next(n for n in nodes if n["kind"] == "do-statement")
        inner = next(n for n in nodes if n["kind"] == "while-statement")
        self.assertEqual(inner["parent"], outer["id"])
        inner_body = next(
            n
            for n in nodes
            if n["parent"] == inner["id"] and n["kind"] == "compound-statement"
        )
        outer_condition = next(
            n
            for n in nodes
            if n["parent"] == outer["id"] and n["kind"] == "binary-expression"
        )
        inner_break = next(n for n in nodes if n["kind"] == "break-statement")
        variants = {
            "inner-parent": (inner, "parent", None),
            "inner-kind": (inner, "kind", None),
            "inner-begin-byte": (inner, "begin", "byte"),
            "inner-begin-column": (inner, "begin", "column"),
            "inner-end-byte": (inner, "end", "byte"),
            "inner-end-column": (inner, "end", "column"),
            "outer-end-byte": (outer, "end", "byte"),
            "outer-end-column": (outer, "end", "column"),
            "body-parent": (inner_body, "parent", None),
            "body-end-column": (inner_body, "end", "column"),
            "condition-parent": (outer_condition, "parent", None),
            "condition-operation": (outer_condition, "operation", None),
            "break-parent": (inner_break, "parent", None),
            "break-begin-column": (inner_break, "begin", "column"),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, (node, field, coordinate) in variants.items():
                with self.subTest(ast=label):
                    forged = json.loads(normalized.stdout)
                    selected = forged["nodes"][node["id"] - 1]
                    if coordinate is not None:
                        selected["span"][field][coordinate] += 1
                    elif field == "parent":
                        selected[field] = 0
                    elif field == "kind":
                        selected[field] = "null-statement"
                    elif field == "operation":
                        selected[field] = "!="
                    guest = Path(scratch) / f"{label}.malbolge"
                    result = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(guest),
                            "--capsule",
                        ],
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=8,
                        env={**os.environ, "TMPDIR": str(ROOT / ".temp")},
                    )
                    self.assertNotEqual(result.returncode, 0, label)
                    self.assertIn(b"Unsupported", result.stderr, label)
                    self.assertFalse(guest.exists(), label)


if __name__ == "__main__":
    unittest.main()
