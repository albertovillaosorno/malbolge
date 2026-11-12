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
#   - Real guest parity and fail-closed unbraced conditional do-while proof.
# - Must-Not:
#   - Replace normative VM execution with a host stdout fixture.
# - Allows:
#   - Inputs: pinned full C and deliberately forged normalized Clang nodes.
#   - Outputs: guest bytes/steps or explicit unsupported admission.
#   - Side effects: isolated source compilation and real VM execution.
# - Split-When:
#   - Runtime C loop lowering supersedes bounded source-state replay.
# - Merge-When:
#   - General unbraced conditional proof subsumes do-while alternatives.
# - Summary:
#   - Both selected arms execute their body before checking a false post-test.

"""Real guest checks for complete C conditional do-while branches."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests/compiler/c-frontend/accepted/local_conditional_do_fibonacci.c"
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
        mask = 0
        # Both do loops run once even when their source post-test is false.
        if next_value & 1:
            mask ^= 26
        else:
            mask |= 0
        output.append((next_value ^ mask) & 31)
        a, b = b, next_value
    return bytes(output)


class ConditionalDoPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(p.is_file() for p in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler binaries not built")

    @staticmethod
    def compile(
        source: Path, guest: Path, timeout: int = 120
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/conditional-do-complete-c-v1",
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
            guest = Path(scratch) / "conditional-do.malbolge"
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

    def test_both_selected_post_test_arms_guest(self) -> None:
        self.assert_real_guest(SOURCE)

    def test_reversed_dispatch_and_false_on_entry_post_test_guest(self) -> None:
        original = SOURCE.read_text()
        modified = (
            original.replace("if ((next & 1U) != 0U)", "if ((next & 1U) == 0U)")
            .replace("mask ^= 26U;", "mask ^= TEMP_MASK;")
            .replace("mask |= 0U;", "mask ^= 26U;")
            .replace("mask ^= TEMP_MASK;", "mask |= 0U;")
            .replace("while (steps < 1U)", "while (steps < 0U)")
        )
        self.assertNotEqual(modified, original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "reversed-conditional-do.c"
            source.write_text(modified)
            self.assert_real_guest(source)

    def test_unsupported_c_sources_fail_without_publication(self) -> None:
        original = SOURCE.read_text()
        variants = {
            "nonterminating-then": original.replace(
                "mask ^= 26U;\n                steps += 1U;",
                "mask ^= 26U;\n                steps += 0U;",
            ),
            "nonterminating-else": original.replace(
                "mask |= 0U;\n                steps += 1U;",
                "mask |= 0U;\n                steps += 0U;",
            ),
            "hidden-then-input": original.replace(
                "mask ^= 26U;", "mask ^= (unsigned)getchar();"
            ),
            "hidden-else-input": original.replace(
                "mask |= 0U;", "mask |= (unsigned)getchar();"
            ),
            "effectful-branch-condition": original.replace(
                "if ((next & 1U) != 0U)", "if (getchar() != 0)"
            ),
            "outer-counter-write": original.replace(
                "mask ^= 26U;", "i += 26U;"
            ),
            "selected-undefined-predicate": original.replace(
                "while (steps < 1U)", "while ((1U / 0U) != 0U)", 1
            ),
            "unbounded-post-test": original.replace(
                "while (steps < 1U)", "while (steps < 100U)", 1
            ),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, source_text in variants.items():
                with self.subTest(source=label):
                    self.assertNotEqual(source_text, original)
                    source = Path(scratch) / f"{label}.c"
                    source.write_text(source_text)
                    guest = source.with_suffix(".malbolge")
                    result = self.compile(source, guest, timeout=12)
                    self.assertNotEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(guest.is_file(), label)

    def test_forged_conditional_do_ast_refuses_publication(self) -> None:
        normalized = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/conditional-do-ast-v1",
                str(SOURCE),
            ],
            capture_output=True,
            check=False,
            timeout=30,
            env={**os.environ, "TMPDIR": str(ROOT / ".temp")},
        )
        self.assertEqual(normalized.returncode, 0, normalized.stderr)
        nodes = json.loads(normalized.stdout)["nodes"]
        branch = next(n for n in nodes if n["kind"] == "if-statement")
        loops = [
            n
            for n in nodes
            if n["kind"] == "do-statement" and n["parent"] == branch["id"]
        ]
        self.assertEqual(len(loops), 2)
        then_loop, else_loop = loops
        scopes = [
            next(
                n
                for n in nodes
                if n["kind"] == "compound-statement" and n["parent"] == loop["id"]
            )
            for loop in loops
        ]
        predicate = next(
            n
            for n in nodes
            if n["kind"] == "binary-expression" and n["parent"] == branch["id"]
        )
        trailing_condition = next(
            n
            for n in nodes
            if n["kind"] == "binary-expression" and n["parent"] == then_loop["id"]
        )
        variants = {
            "then-parent": (then_loop, "parent", None),
            "else-parent": (else_loop, "parent", None),
            "then-begin-byte": (then_loop, "begin", "byte"),
            "then-begin-line": (then_loop, "begin", "line"),
            "then-begin-column": (then_loop, "begin", "column"),
            "else-begin-byte": (else_loop, "begin", "byte"),
            "else-begin-line": (else_loop, "begin", "line"),
            "else-begin-column": (else_loop, "begin", "column"),
            "then-end-column": (then_loop, "end", "column"),
            "else-end-byte": (else_loop, "end", "byte"),
            "else-end-column": (else_loop, "end", "column"),
            "then-scope-end-byte": (scopes[0], "end", "byte"),
            "else-scope-end-column": (scopes[1], "end", "column"),
            "predicate-parent": (predicate, "parent", None),
            "branch-end-column": (branch, "end", "column"),
            "post-test-end-byte": (trailing_condition, "end", "byte"),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, (node, field, coordinate) in variants.items():
                with self.subTest(ast=label):
                    forged = json.loads(normalized.stdout)
                    selected = forged["nodes"][node["id"] - 1]
                    if coordinate is None:
                        selected[field] = 0
                    else:
                        selected["span"][field][coordinate] += 1
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
                        timeout=12,
                        env={**os.environ, "TMPDIR": str(ROOT / ".temp")},
                    )
                    self.assertNotEqual(result.returncode, 0, label)
                    self.assertIn(b"Unsupported", result.stderr, label)
                    self.assertFalse(guest.is_file(), label)


if __name__ == "__main__":
    unittest.main()
