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
#   - C ternary short-circuit division guarded by the complete Fibonacci loop.
# - Must-Not:
#   - Replace VM parity with host output or publish unproved guest artifacts.
# - Allows:
#   - Inputs: pinned frontend, checked normalized IR, full guest compiler.
#   - Outputs: independent unsigned C byte oracle and real VM replay.
#   - Side effects: isolated local temporary test files only.
# - Split-When:
#   - Dynamic C conditional evaluation is implemented inside guest programs.
# - Merge-When:
#   - The generalized source/guest differential suite covers short-circuiting.
# - Summary:
#   - Nonselected C division by zero must not be evaluated by source replay.

"""End-to-end guarded C ternary evaluation under real guest byte output."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests/compiler/c-frontend/accepted/local_lazy_conditional_fibonacci.c"
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
VM = ROOT / ".cache/rust/target/debug/malbolge"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
ADAPTER = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT = ROOT / ".cache/rust/target/debug/malbolge_layout"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
GUEST_INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"


def oracle() -> bytes:
    """Unsigned C arithmetic with selected-only ternary branch evaluation."""
    a, b = 1, 1
    output = bytearray()
    for _ in range(12):
        next_term = (a + b) & 255
        if next_term & 1:
            selected = ((next_term ^ 26) & 31) // (next_term & 1)
        else:
            selected = next_term & 31
        output.append(selected)
        a, b = b, next_term
    return bytes(output)


class LazyConditionalPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler binaries not built")

    def compile(
        self, source: Path, guest: Path, source_id: str
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                source_id,
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=120,
        )

    def test_full_guarded_fibonacci_emits_real_guest_bytes(self) -> None:
        expected = oracle()
        self.assertEqual(expected, bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            guest = Path(temporary) / "guarded-fibonacci.malbolge"
            compiled = self.compile(SOURCE, guest, "tests/lazy-fibonacci-v1")
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for data in (b"", bytes((0, 255, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=data,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertEqual(executed.stderr, b"malbolge-steps-v1:47\n")

    def test_selected_undefined_or_effectful_branch_refuses(self) -> None:
        source = SOURCE.read_text()
        original = "? (((next ^ 26U) & 31U) / (next & 1U))"
        self.assertEqual(source.count(original), 1)
        # Invalid *selected* arithmetic and effects in either syntactic arm
        # must continue refusing before any guest artifact is published.
        variants = {
            "selected-zero-denominator": source.replace(
                original, "? (((next ^ 26U) & 31U) / 0U)"
            ),
            "unselected-side-effect": source.replace(
                ": (next & 31U);", ": (putchar(65), next & 31U);"
            ),
            "unselected-input": source.replace(
                ": (next & 31U);", ": (unsigned)getchar();"
            ),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            for label, replacement in variants.items():
                with self.subTest(label=label):
                    source_path = Path(temporary) / f"{label}.c"
                    source_path.write_text(replacement)
                    guest = source_path.with_suffix(".malbolge")
                    refused = self.compile(source_path, guest, f"tests/{label}-v1")
                    self.assertNotEqual(refused.returncode, 0)
                    self.assertFalse(guest.exists())

    def test_both_ternary_arms_guard_division_and_remainder(self) -> None:
        """Both selected paths are defined; both skipped paths divide by zero."""
        source = SOURCE.read_text()
        original = (
            "        unsigned selected = ((next & 1U) != 0U)\n"
            "            ? (((next ^ 26U) & 31U) / (next & 1U))\n"
            "            : (next & 31U);"
        )
        changed = (
            "        unsigned selected = ((next & 1U) == 0U)\n"
            "            ? ((next & 31U) / (1U - (next & 1U)))\n"
            "            : (((next ^ 26U) & 31U) % ((next & 1U) * 32U));"
        )
        self.assertEqual(source.count(original), 1)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            candidate = Path(temporary) / "two-guards.c"
            candidate.write_text(source.replace(original, changed))
            guest = candidate.with_suffix(".malbolge")
            compiled = self.compile(candidate, guest, "tests/two-guards-v1")
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for data in (b"", bytes((0, 255, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=data,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, oracle())
                self.assertEqual(executed.stderr, b"malbolge-steps-v1:47\n")

    def test_skipped_division_ast_forgeries_refuse(self) -> None:
        """Skipped expressions remain checked against authentic Clang nodes."""
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/lazy-ast-forgery-v1",
                str(SOURCE),
            ],
            check=False,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        parsed = json.loads(frontend.stdout)
        divisions = [node for node in parsed["nodes"] if node.get("operation") == "/"]
        self.assertEqual(len(divisions), 1)
        division = divisions[0]
        identifier = division["id"]
        self.assertIsInstance(identifier, int)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            for label, field, replacement in (
                ("div-kind", "kind", "call-expression"),
                ("div-type", "type", "i32"),
                ("div-parent", "parent", 0),
                ("div-hidden-metadata", "reference", "external:getchar"),
            ):
                with self.subTest(label=label):
                    forged = json.loads(frontend.stdout)
                    forged["nodes"][identifier - 1][field] = replacement
                    guest = Path(temporary) / f"{label}.malbolge"
                    refused = subprocess.run(
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
                        timeout=30,
                    )
                    self.assertNotEqual(refused.returncode, 0)
                    self.assertFalse(guest.exists())
