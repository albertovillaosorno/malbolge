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
#   - Pure C unary operands containing undefined arithmetic when skipped.
# - Must-Not:
#   - Evaluate skipped undefined C or replace real VM guest output.
# - Allows:
#   - Inputs: pinned C23 sources and forged normalized frontend nodes.
#   - Outputs: normative Malbolge recurrence parity or explicit rejection.
#   - Side effects: isolated temporary C compilation and guest execution.
# - Split-When:
#   - Runtime C expression lowering replaces bounded source-state replay.
# - Merge-When:
#   - General verifier coverage subsumes skipped pure unary arithmetic.
# - Summary:
#   - Verify all three unsigned unary operators around skipped division.

"""End-to-end source and VM proof for skipped unsigned C unary operations."""

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
    "local_unary_skipped_arithmetic_fibonacci.c"
)
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
VM = ROOT / ".cache/rust/target/debug/malbolge"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
ADAPTER = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT = ROOT / ".cache/rust/target/debug/malbolge_layout"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
GUEST_INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
UNARY = "~(next / (next & 1U))"


def oracle(operation: str) -> bytes:
    a, b = 1, 1
    result = bytearray()
    for _ in range(12):
        term = (a + b) & 255
        selected = term & 31
        if term & 1:
            quotient = term // (term & 1)
            if operation == "~":
                unary = (~quotient) & 0xFFFFFFFF
            elif operation == "-":
                unary = (-quotient) & 0xFFFFFFFF
            else:
                assert operation == "+"
                unary = quotient
            if unary != 0:
                selected = (term ^ 26) & 31
        result.append(selected)
        a, b = b, term
    return bytes(result)


class UnarySkippedArithmeticPipelineTests(unittest.TestCase):
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

    def check_complete_c_guest(self, operation: str) -> None:
        source_text = SOURCE.read_text()
        self.assertEqual(source_text.count(UNARY), 1)
        expected = bytes.fromhex("02191f08170f020d03101303")
        self.assertEqual(oracle(operation), expected)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / f"unary-{ord(operation)}.c"
            guest = source.with_suffix(".malbolge")
            source.write_text(
                source_text.replace(UNARY, f"{operation}(next / (next & 1U))")
            )
            result = self.compile(
                source, guest, f"tests/unary-skipped-{ord(operation)}"
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
                self.assertEqual(run.stdout, expected)
                self.assertEqual(run.stderr, b"malbolge-steps-v1:47\n")

    def test_complete_c_bitwise_not_guest(self) -> None:
        self.check_complete_c_guest("~")

    def test_complete_c_unary_plus_guest(self) -> None:
        self.check_complete_c_guest("+")

    def test_complete_c_unary_minus_guest(self) -> None:
        self.check_complete_c_guest("-")

    def test_undefined_selected_or_hidden_effects_refuse(self) -> None:
        source_text = SOURCE.read_text()
        variants = {
            "selected-zero-division": source_text.replace(
                "next / (next & 1U)", "next / 0U"
            ),
            "hidden-read": source_text.replace(
                "next / (next & 1U)", "(unsigned)getchar()"
            ),
            "hidden-write": source_text.replace(
                "next / (next & 1U)", "(unsigned)putchar(65)"
            ),
            "hidden-comma": source_text.replace(
                "next / (next & 1U)", "(putchar(65), next / (next & 1U))"
            ),
            "hidden-update": source_text.replace("next / (next & 1U)", "++next"),
            "signed-cast": source_text.replace(UNARY, "-(int)(next / (next & 1U))"),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for name, source_text in variants.items():
                with self.subTest(name=name):
                    source = Path(directory) / f"{name}.c"
                    guest = source.with_suffix(".malbolge")
                    source.write_text(source_text)
                    result = self.compile(
                        source, guest, f"tests/unary-skipped-bad-{name}"
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(guest.exists())

    def test_forged_unary_and_division_nodes_refuse(self) -> None:
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/unary-skipped-arithmetic-ast-v1",
                str(SOURCE),
            ],
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        artifact = json.loads(frontend.stdout)
        nodes = artifact["nodes"]
        unary = next(
            n
            for n in nodes
            if n["kind"] == "unary-expression" and n["operation"] == "~"
        )
        division = next(
            n
            for n in nodes
            if n["kind"] == "binary-expression" and n["operation"] == "/"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for node in (unary, division):
                for field, value in (
                    ("type", "i32"),
                    ("parent", 0),
                    ("reference", "external:getchar"),
                    ("kind", "call-expression"),
                    ("operation", "!"),
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
