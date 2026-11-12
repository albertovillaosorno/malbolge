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
#   - Real guest parity and fail-closed C do-break skipped-condition proof.
# - Must-Not:
#   - Substitute a host stdout fixture for normative guest execution.
# - Allows:
#   - Inputs: pinned C source and forged normalized Clang AST nodes.
#   - Outputs: VM byte parity or explicit unsupported admission.
#   - Side effects: isolated source compilation and guest execution.
# - Split-When:
#   - General guest C control-flow conformance supersedes bounded replay.
# - Merge-When:
#   - Independent do-break tests cover these semantic source boundaries.
# - Summary:
#   - Undefined C arithmetic is never evaluated after selected break.

"""Full-source do-break skipped predicate and guest parity evidence."""

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
    "local_do_break_skipped_condition_fibonacci.c"
)
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
ADAPTER = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT = ROOT / ".cache/rust/target/debug/malbolge_layout"
VM = ROOT / ".cache/rust/target/debug/malbolge"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"


def independent_oracle() -> bytes:
    a, b = 1, 1
    output = bytearray()
    for _ in range(12):
        next_value = (a + b) & 255
        # C's selected break must not evaluate the ternary predicate at all.
        if next_value & 1:
            output.append((next_value ^ 26) & 31)
        else:
            output.append(next_value & 31)
        a, b = b, next_value
    return bytes(output)


class DoBreakSkippedConditionPipelineTests(unittest.TestCase):
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
                "tests/do-break-skipped-predicate-v1",
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

    def assert_real_guest(self, source: Path) -> None:
        expected = independent_oracle()
        self.assertEqual(expected, bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "do-break.malbolge"
            compile_result = self.compile(source, guest)
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            self.assertTrue(guest.is_file())
            for stdin in (b"", bytes((255, 0, 128))):
                result = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=stdin,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, expected)
                self.assertEqual(result.stderr, b"malbolge-steps-v1:47\n")

    def test_selected_break_and_evaluated_false_predicate_guest(self) -> None:
        self.assert_real_guest(SOURCE)

    def test_unconditional_break_skips_arithmetic_guest(self) -> None:
        original = SOURCE.read_text()
        modified = original.replace(
            "            if (next & 1U) {\n                break;\n            }",
            "            break;",
        ).replace(
            "((next & 1U) ? (1U / 0U) : 0U)",
            "((a / (b - b)) != 0U)",
        )
        self.assertNotEqual(modified, original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "unconditional-break.c"
            source.write_text(modified)
            self.assert_real_guest(source)

    def test_invalid_complete_c_refuses_artifact(self) -> None:
        original = SOURCE.read_text()
        variants = {
            "selected-undefined": original.replace("(1U / 0U) : 0U", "0U : (1U / 0U)"),
            "unselected-input": original.replace("(1U / 0U)", "(unsigned)getchar()"),
            "selected-break-disabled": original.replace("if (next & 1U)", "if (0U)"),
            "unreachable-output": original.replace(
                "                break;",
                "                break;\n                putchar(90);",
            ),
            "unreachable-write": original.replace(
                "                break;",
                "                break;\n                next = 0U;",
            ),
            "unbounded-even-loop": original.replace("(1U / 0U) : 0U", "(1U / 0U) : 1U"),
            "effectful-condition": original.replace(
                "(1U / 0U) : 0U", "(1U / 0U) : ++next"
            ),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, source_text in variants.items():
                with self.subTest(source=label):
                    self.assertNotEqual(source_text, original)
                    source = Path(scratch) / f"{label}.c"
                    source.write_text(source_text)
                    guest = source.with_suffix(".malbolge")
                    result = self.compile(source, guest, timeout=8)
                    self.assertNotEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(guest.is_file(), label)

    def test_forged_skipped_condition_ast_refuses_artifact(self) -> None:
        normalized = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/do-break-skipped-predicate-ast-v1",
                str(SOURCE),
            ],
            capture_output=True,
            check=False,
            timeout=30,
            env={**os.environ, "TMPDIR": str(ROOT / ".temp")},
        )
        self.assertEqual(normalized.returncode, 0, normalized.stderr)
        nodes = json.loads(normalized.stdout)["nodes"]
        do = next(n for n in nodes if n["kind"] == "do-statement")
        branch = next(
            n
            for n in nodes
            if n["kind"] == "if-statement"
            and n["parent"]
            == next(
                x["id"]
                for x in nodes
                if x["kind"] == "compound-statement" and x["parent"] == do["id"]
            )
        )
        selected_break = next(n for n in nodes if n["kind"] == "break-statement")
        ternary = next(n for n in nodes if n["kind"] == "conditional-expression")
        divisor = next(
            n
            for n in nodes
            if n["kind"] == "binary-expression" and n.get("operation") == "/"
        )
        variants = {
            "do-end-byte": (do, "end", "byte"),
            "do-end-column": (do, "end", "column"),
            "break-parent": (selected_break, "parent", None),
            "break-begin-byte": (selected_break, "begin", "byte"),
            "break-begin-column": (selected_break, "begin", "column"),
            "branch-parent": (branch, "parent", None),
            "predicate-parent": (ternary, "parent", None),
            "predicate-begin-byte": (ternary, "begin", "byte"),
            "predicate-end-column": (ternary, "end", "column"),
            "division-parent": (divisor, "parent", None),
            "division-begin-column": (divisor, "begin", "column"),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, (node, field, coordinate) in variants.items():
                with self.subTest(ast=label):
                    forged = json.loads(normalized.stdout)
                    selected = forged["nodes"][node["id"] - 1]
                    if coordinate is not None:
                        selected["span"][field][coordinate] += 1
                    else:
                        selected[field] = 0
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
                    self.assertFalse(guest.is_file(), label)


if __name__ == "__main__":
    unittest.main()
