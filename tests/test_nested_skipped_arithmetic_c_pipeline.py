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
#   - Recursive authentication of nested pure C skipped arithmetic.
# - Must-Not:
#   - Execute skipped undefined operations or produce host-emulated bytes.
# - Allows:
#   - Inputs: pinned C source and deliberately altered normalized Clang trees.
#   - Outputs: normative guest Fibonacci bytes or fail-closed rejection.
#   - Side effects: isolated temporary compilation and guest VM execution.
# - Split-When:
#   - General dynamic C expression lowering supersedes bounded source replay.
# - Merge-When:
#   - Skipped C arithmetic becomes part of the general guest verifier matrix.
# - Summary:
#   - Nested skipped arithmetic is pure; selected arithmetic remains strict.

"""End-to-end C-to-Malbolge proof for nested skipped unsigned expressions."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT / "tests/compiler/c-frontend/accepted/"
    "local_nested_skipped_arithmetic_fibonacci.c"
)
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
VM = ROOT / ".cache/rust/target/debug/malbolge"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
ADAPTER = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT = ROOT / ".cache/rust/target/debug/malbolge_layout"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
GUEST_INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
PREDICATE = "(next & 2U) != 0U"


def oracle(reverse: bool = False) -> bytes:
    a, b = 1, 1
    output = bytearray()
    for _ in range(12):
        term = (a + b) & 255
        selected = term & 31
        if term & 1:
            # For odd terms, division by term & 1 yields term and its
            # remainder is zero; the second ternary arm subtracts term.
            if bool(term & 2) != reverse:
                assert (term // (term & 1)) + (term % (term & 1)) == term
                selected = (term ^ 26) & 31
            else:
                assert (term % (term & 1) + term // (term & 1) - term) == 0
        output.append(selected)
        a, b = b, term
    return bytes(output)


class NestedSkippedArithmeticPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(p.is_file() for p in (FRONTEND, ADAPTER, LAYOUT, VM)):
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
            check=False,
            capture_output=True,
            timeout=120,
        )

    def test_complete_c_guest_matches_independent_recurrence(self) -> None:
        text = SOURCE.read_text()
        self.assertEqual(text.count(PREDICATE), 1)
        self.assertEqual(oracle(), bytes.fromhex("021905080d15020d19100919"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for reverse in (False, True):
                with self.subTest(reverse=reverse):
                    source = Path(directory) / f"fib-{reverse}.c"
                    guest = source.with_suffix(".malbolge")
                    source.write_text(
                        text.replace(PREDICATE, "(next & 2U) == 0U")
                        if reverse
                        else text
                    )
                    result = self.compile(
                        source, guest, f"tests/nested-skipped-{reverse}"
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertTrue(guest.is_file())
                    for stdin in (b"", bytes((0, 255, 128))):
                        run = subprocess.run(
                            [str(VM), str(guest), "--input-stdin", "--report-steps"],
                            input=stdin,
                            capture_output=True,
                            check=False,
                            timeout=30,
                        )
                        self.assertEqual(run.returncode, 0, run.stderr)
                        self.assertEqual(run.stdout, oracle(reverse))
                        self.assertEqual(
                            run.stderr,
                            f"malbolge-steps-v1:{41 if reverse else 43}\n".encode(),
                        )

    def test_selected_undefined_arithmetic_and_skipped_effects_refuse(self) -> None:
        text = SOURCE.read_text()
        variants = {
            "selected-zero-divisor": text.replace("next / (next & 1U)", "next / 0U"),
            "selected-zero-remainder": text.replace("next % (next & 1U)", "next % 0U"),
            "hidden-read": text.replace("next % (next & 1U)", "(unsigned)getchar()"),
            "hidden-write": text.replace("next / (next & 1U)", "(unsigned)putchar(65)"),
            "hidden-comma": text.replace("(next & 1U)", "(putchar(65), (next & 1U))"),
            "hidden-guard-read": text.replace(
                PREDICATE, "((unsigned)getchar() & 2U) != 0U"
            ),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for name, source_text in variants.items():
                with self.subTest(name=name):
                    self.assertNotEqual(source_text, text)
                    source = Path(directory) / f"{name}.c"
                    guest = source.with_suffix(".malbolge")
                    source.write_text(source_text)
                    result = self.compile(
                        source, guest, f"tests/nested-skipped-bad-{name}"
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(guest.exists())

    def test_forged_skipped_expression_nodes_refuse(self) -> None:
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/nested-skipped-arithmetic-ast-v1",
                str(SOURCE),
            ],
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        artifact = json.loads(frontend.stdout)
        nodes = artifact["nodes"]
        conditional = next(n for n in nodes if n["kind"] == "conditional-expression")
        operations = [
            n
            for n in nodes
            if n.get("operation") in ("/", "%", "+", "-")
            and n["id"] > conditional["id"]
        ]
        self.assertGreaterEqual(len(operations), 6)
        bad_nodes = (conditional, *operations)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for node in bad_nodes:
                for field, value in (
                    ("type", "i32"),
                    ("parent", 0),
                    ("reference", "external:getchar"),
                    ("kind", "call-expression"),
                ):
                    with self.subTest(node=node["id"], field=field):
                        forged = json.loads(frontend.stdout)
                        forged["nodes"][node["id"] - 1][field] = value
                        output = Path(directory) / f"{node['id']}-{field}.malbolge"
                        refused = subprocess.run(
                            [
                                str(ADAPTER),
                                "--layout-backend",
                                str(LAYOUT),
                                "--output",
                                str(output),
                                "--capsule",
                            ],
                            input=json.dumps(forged).encode(),
                            capture_output=True,
                            check=False,
                            timeout=30,
                        )
                        self.assertNotEqual(refused.returncode, 0, refused.stderr)
                        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
