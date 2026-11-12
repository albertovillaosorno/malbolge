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
#   - Complete C conditional while guest parity and source/AST rejection.
# - Must-Not:
#   - Substitute source-level simulation for real Malbolge guest execution.
# - Allows:
#   - Inputs: pinned Clang C program and forged normalized JSON nodes.
#   - Outputs: normative VM parity or explicit unsupported admission.
#   - Side effects: isolated compilation and VM execution.
# - Split-When:
#   - Dynamic guest conditional loop lowering replaces static source replay.
# - Merge-When:
#   - Independent complete-C control-flow tests cover both while arms.
# - Summary:
#   - Source-checked branch alternatives preserve ordered unsigned writes.

"""Complete conditional while programs on the normative guest VM."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests/compiler/c-frontend/accepted/local_conditional_while_fibonacci.c"
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
        steps = 0
        if next_value & 1:
            while steps < 2:
                mask += 13
                steps += 1
        else:
            while steps < 1:
                mask += 0
                steps += 1
        output.append((next_value ^ mask) & 31)
        a, b = b, next_value
    return bytes(output)


class ConditionalWhilePipelineTests(unittest.TestCase):
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
                "tests/conditional-while-complete-c-v1",
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
            guest = Path(scratch) / "conditional-while.malbolge"
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

    def test_complete_two_selected_while_arms_guest(self) -> None:
        self.assert_real_guest(SOURCE)

    def test_inverted_dispatch_same_guest_oracle(self) -> None:
        original = SOURCE.read_text()
        # The opposite comparison must select the corresponding other
        # while, preserving C's output but changing which arm is selected.
        modified = (
            original.replace("if ((next & 1U) != 0U)", "if ((next & 1U) == 0U)")
            .replace("while (steps < 2U)", "while (steps < TEMP_LIMIT)")
            .replace("while (steps < 1U)", "while (steps < 2U)")
            .replace("while (steps < TEMP_LIMIT)", "while (steps < 1U)")
            .replace("mask += 13U;", "mask += TEMP_MASK;")
            .replace("mask += 0U;", "mask += 13U;")
            .replace("mask += TEMP_MASK;", "mask += 0U;")
        )
        self.assertNotEqual(modified, original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "inverted-while-dispatch.c"
            source.write_text(modified)
            self.assert_real_guest(source)

    def test_nonterminating_or_effectful_sources_refuse_publication(self) -> None:
        original = SOURCE.read_text()
        variants = {
            "stalled-then-loop": original.replace(
                "mask += 13U;\n                steps += 1U;",
                "mask += 13U;\n                steps += 0U;",
            ),
            "stalled-else-loop": original.replace(
                "mask += 0U;\n                steps += 1U;",
                "mask += 0U;\n                steps += 0U;",
            ),
            "hidden-then-input": original.replace(
                "mask += 13U;", "mask += (unsigned)getchar();"
            ),
            "hidden-else-input": original.replace(
                "mask += 0U;", "mask += (unsigned)getchar();"
            ),
            "effectful-condition": original.replace(
                "if ((next & 1U) != 0U)", "if (getchar() != 0)"
            ),
            "outer-counter-write": original.replace("mask += 13U;", "i += 13U;"),
            "unbounded-condition": original.replace(
                "while (steps < 2U)", "while (steps < 400U)"
            ),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, source_text in variants.items():
                with self.subTest(source=label):
                    self.assertNotEqual(source_text, original)
                    source = Path(scratch) / f"{label}.c"
                    source.write_text(source_text)
                    guest = source.with_suffix(".malbolge")
                    result = self.compile(source, guest, timeout=10)
                    self.assertNotEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(guest.is_file(), label)

    def test_forged_conditional_while_ast_refuses_publication(self) -> None:
        normalized = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/conditional-while-ast-v1",
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
        whiles = [
            n
            for n in nodes
            if n["kind"] == "while-statement" and n["parent"] == branch["id"]
        ]
        self.assertEqual(len(whiles), 2)
        then_loop, else_loop = whiles
        predicate = next(
            n
            for n in nodes
            if n["kind"] == "binary-expression" and n["parent"] == branch["id"]
        )
        then_scope = next(
            n
            for n in nodes
            if n["kind"] == "compound-statement" and n["parent"] == then_loop["id"]
        )
        else_scope = next(
            n
            for n in nodes
            if n["kind"] == "compound-statement" and n["parent"] == else_loop["id"]
        )
        variants = {
            "then-parent": (then_loop, "parent", None),
            "else-parent": (else_loop, "parent", None),
            "then-begin-byte": (then_loop, "begin", "byte"),
            "else-begin-byte": (else_loop, "begin", "byte"),
            "then-begin-line": (then_loop, "begin", "line"),
            "else-begin-line": (else_loop, "begin", "line"),
            "then-begin-column": (then_loop, "begin", "column"),
            "else-begin-column": (else_loop, "begin", "column"),
            "then-end-byte": (then_loop, "end", "byte"),
            "else-end-column": (else_loop, "end", "column"),
            "then-scope-end": (then_scope, "end", "byte"),
            "else-scope-end": (else_scope, "end", "column"),
            "predicate-parent": (predicate, "parent", None),
            "branch-end-column": (branch, "end", "column"),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, (node, field, coordinate) in variants.items():
                with self.subTest(ast=label):
                    forged = json.loads(normalized.stdout)
                    target = forged["nodes"][node["id"] - 1]
                    if coordinate is None:
                        target[field] = 0
                    else:
                        target["span"][field][coordinate] += 1
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
                        timeout=10,
                        env={**os.environ, "TMPDIR": str(ROOT / ".temp")},
                    )
                    self.assertNotEqual(result.returncode, 0, label)
                    self.assertIn(b"Unsupported", result.stderr, label)
                    self.assertFalse(guest.is_file(), label)


if __name__ == "__main__":
    unittest.main()
