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
#   - Source-authenticated C ternary inside a short-circuited Boolean guard.
# - Must-Not:
#   - Execute skipped undefined arithmetic or use host-produced guest bytes.
# - Allows:
#   - Inputs: pinned Clang source and independently forged normalized ASTs.
#   - Outputs: real guest Fibonacci stream or closed compiler rejection.
#   - Side effects: isolated temporary C and Malbolge artifacts.
# - Split-When:
#   - General guest-side C conditionals replace bounded source evaluation.
# - Merge-When:
#   - Full C and real guest output regression is consolidated.
# - Summary:
#   - An unexecuted ternary authenticates both undefined arithmetic arms.

"""Normative guest parity for a short-circuited C ternary."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "tests/compiler/c-frontend/accepted/local_skipped_ternary_logical_fibonacci.c"
)
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
VM = ROOT / ".cache/rust/target/debug/malbolge"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
ADAPTER = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT = ROOT / ".cache/rust/target/debug/malbolge_layout"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
GUEST_INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
PREDICATE = "(next & 2U) != 0U"


def oracle(reverse=False):
    a, b = 1, 1
    result = bytearray()
    for _ in range(12):
        term = (a + b) & 255
        value = term & 31
        if term & 1:
            if bool(term & 2) != reverse:
                assert term // (term & 1) != 0
                value = (term ^ 26) & 31
            else:
                assert term % (term & 1) == 0
        result.append(value)
        a, b = b, term
    return bytes(result)


class SkippedTernaryLogicalPipelineTests(unittest.TestCase):
    def setUp(self):
        if not all(p.is_file() for p in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned binaries not built")

    def compile(self, source, guest, identity):
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                identity,
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=180,
        )

    def test_complete_guest_fibonacci_both_arms(self):
        original = SOURCE.read_text()
        self.assertEqual(original.count(PREDICATE), 1)
        for reverse in (False, True):
            with self.subTest(reverse=reverse):
                text = (
                    original.replace(PREDICATE, "(next & 2U) == 0U")
                    if reverse
                    else original
                )
                with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp:
                    source = Path(temp) / "ternary.c"
                    guest = Path(temp) / "ternary.malbolge"
                    source.write_text(text)
                    compiled = self.compile(
                        source, guest, f"tests/skipped-ternary-{reverse}"
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
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
                        self.assertTrue(run.stderr.startswith(b"malbolge-steps-v1:"))

    def test_undefined_selected_arithmetic_and_hidden_effects_refuse(self):
        source_text = SOURCE.read_text()
        variants = {
            "selected-zero-division": source_text.replace(
                "next / (next & 1U)", "next / 0U"
            ),
            "selected-zero-remainder": source_text.replace(
                "next % (next & 1U)", "next % 0U"
            ),
            "hidden-input": source_text.replace(
                "next / (next & 1U)", "(unsigned)getchar() / (next & 1U)"
            ),
            "hidden-output": source_text.replace(
                "next % (next & 1U)", "(unsigned)putchar(65) % (next & 1U)"
            ),
            "hidden-guard-input": source_text.replace(
                PREDICATE, "((unsigned)getchar() & 2U) != 0U"
            ),
            "hidden-comma": source_text.replace(
                "next / (next & 1U)", "next / (putchar(65), (next & 1U))"
            ),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp:
            for label, candidate in variants.items():
                with self.subTest(label=label):
                    self.assertNotEqual(candidate, source_text)
                    source = Path(temp) / f"{label}.c"
                    guest = source.with_suffix(".malbolge")
                    source.write_text(candidate)
                    refused = self.compile(source, guest, f"tests/{label}-ternary")
                    self.assertNotEqual(refused.returncode, 0)
                    self.assertFalse(guest.exists())

    def test_skipped_ternary_forged_ast_refuses(self):
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/skipped-ternary-logical-ast-v1",
                str(SOURCE),
            ],
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        original = frontend.stdout
        nodes = json.loads(original)["nodes"]
        ternary = next(n for n in nodes if n["kind"] == "conditional-expression")
        division = next(n for n in nodes if n.get("operation") == "/")
        remainder = next(n for n in nodes if n.get("operation") == "%")
        condition = next(
            n
            for n in nodes
            if n["parent"] == ternary["id"] and n.get("operation") == "!="
        )
        mutations = (
            ("ternary-type", ternary, "type", "i32"),
            ("ternary-parent", ternary, "parent", 0),
            ("ternary-effect", ternary, "reference", "external:getchar"),
            ("ternary-kind", ternary, "kind", "call-expression"),
            ("then-parent", division, "parent", 0),
            ("else-parent", remainder, "parent", 0),
            ("condition-parent", condition, "parent", 0),
            ("then-effect", division, "reference", "external:putchar"),
            ("else-effect", remainder, "reference", "external:getchar"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp:
            for label, node, field, value in mutations:
                with self.subTest(label=label):
                    forged = json.loads(original)
                    forged["nodes"][node["id"] - 1][field] = value
                    self.assert_refused(forged, Path(temp) / f"{label}.malbolge")
            for point in ("begin", "end"):
                for coordinate in ("byte", "column"):
                    with self.subTest(point=point, coordinate=coordinate):
                        forged = json.loads(original)
                        forged["nodes"][ternary["id"] - 1]["span"][point][
                            coordinate
                        ] += 1
                        self.assert_refused(
                            forged, Path(temp) / f"{point}-{coordinate}.malbolge"
                        )

    def assert_refused(self, tree, output):
        refused = subprocess.run(
            [
                str(ADAPTER),
                "--layout-backend",
                str(LAYOUT),
                "--output",
                str(output),
                "--capsule",
            ],
            input=json.dumps(tree).encode(),
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertNotEqual(refused.returncode, 0, refused.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
