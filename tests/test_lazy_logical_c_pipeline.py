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
#   - Nested and ordinary C short-circuit evaluation in full recurrences.
# - Must-Not:
#   - Evaluate skipped C arithmetic or replace guest VM with host output.
# - Allows:
#   - Inputs: pinned Clang C source and independently forged normalized trees.
#   - Outputs: verified twelve-byte guest Fibonacci trace or closed rejection.
#   - Side effects: temporary files under the ignored test workspace.
# - Split-When:
#   - A general C short-circuit IR replaces source-proven finite evaluation.
# - Merge-When:
#   - The full compiler differential suite includes logical expression guards.
# - Summary:
#   - Nested && and || skip undefined RHS arithmetic but not selected UB.

"""Full C-to-Malbolge short-circuit logical expression regressions."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests/compiler/c-frontend/accepted/local_lazy_logical_fibonacci.c"
NESTED_SOURCE = (
    ROOT / "tests/compiler/c-frontend/accepted/local_nested_lazy_logical_fibonacci.c"
)
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
VM = ROOT / ".cache/rust/target/debug/malbolge"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
ADAPTER = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT = ROOT / ".cache/rust/target/debug/malbolge_layout"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
GUEST_INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"

AND_ARM = """        if (((next & 1U) != 0U) && ((next / (next & 1U)) != 0U)) {
            selected = (next ^ 26U) & 31U;
        }"""
OR_ARM = """        if (((next & 1U) == 0U) || ((next / (next & 1U)) == 0U)) {
            selected = next & 31U;
        } else {
            selected = (next ^ 26U) & 31U;
        }"""


def oracle() -> bytes:
    """Compute recurrence and branch results independently with unsigned C rules."""
    a, b = 1, 1
    output = bytearray()
    for _ in range(12):
        next_term = (a + b) & 255
        selected = next_term & 31
        if next_term & 1:
            # A nonzero odd term selects the second operand of && and ||.
            assert next_term // (next_term & 1) != 0
            selected = (next_term ^ 26) & 31
        output.append(selected)
        a, b = b, next_term
    return bytes(output)


def or_source(source: str) -> str:
    assert source.count(AND_ARM) == 1
    return source.replace(AND_ARM, OR_ARM)


class LazyLogicalPipelineTests(unittest.TestCase):
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

    def frontend_ast(self, source: Path) -> bytes:
        result = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/lazy-logical-ast-v1",
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def reject_ast(self, data: dict[str, object], guest: Path) -> None:
        refused = subprocess.run(
            [
                str(ADAPTER),
                "--layout-backend",
                str(LAYOUT),
                "--output",
                str(guest),
                "--capsule",
            ],
            input=json.dumps(data).encode(),
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertNotEqual(refused.returncode, 0)
        self.assertFalse(guest.exists())

    def test_full_logical_and_or_emit_normative_guest_bytes(self) -> None:
        expected = oracle()
        self.assertEqual(expected, bytes.fromhex("02191f08170f020d03101303"))
        source_text = SOURCE.read_text()
        self.assertEqual(source_text.count(AND_ARM), 1)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            for label, text in (
                ("and", source_text),
                ("or", or_source(source_text)),
            ):
                with self.subTest(label=label):
                    source = Path(temporary) / f"{label}.c"
                    guest = source.with_suffix(".malbolge")
                    source.write_text(text)
                    compiled = self.compile(
                        source, guest, f"tests/lazy-logical-{label}-v1"
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(guest.is_file())
                    for stdin in (b"", bytes((0, 255, 128))):
                        executed = subprocess.run(
                            [str(VM), str(guest), "--input-stdin", "--report-steps"],
                            input=stdin,
                            capture_output=True,
                            check=False,
                            timeout=30,
                        )
                        self.assertEqual(executed.returncode, 0, executed.stderr)
                        self.assertEqual(executed.stdout, expected)
                        self.assertEqual(executed.stderr, b"malbolge-steps-v1:47\n")

    def test_nested_skipped_logical_tree_emits_real_guest_bytes(self) -> None:
        source_text = NESTED_SOURCE.read_text()
        self.assertIn("&& (((next & 2U) != 0U) ||", source_text)
        expected = oracle()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            # The second variant changes which odd term selects the inner
            # division, while even terms still skip its zero divisor.
            for label, candidate in (
                ("inner-even", source_text),
                (
                    "inner-odd",
                    source_text.replace(
                        "((next & 2U) != 0U) ||",
                        "((next & 2U) == 0U) ||",
                    ),
                ),
            ):
                with self.subTest(label=label):
                    source = Path(temporary) / f"{label}.c"
                    source.write_text(candidate)
                    guest = source.with_suffix(".malbolge")
                    compiled = self.compile(
                        source, guest, f"tests/nested-lazy-{label}-v1"
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(guest.is_file())
                    for stdin in (b"", bytes((255, 0, 129))):
                        executed = subprocess.run(
                            [str(VM), str(guest), "--input-stdin", "--report-steps"],
                            input=stdin,
                            capture_output=True,
                            check=False,
                            timeout=30,
                        )
                        self.assertEqual(executed.returncode, 0, executed.stderr)
                        self.assertEqual(executed.stdout, expected)
                        self.assertEqual(executed.stderr, b"malbolge-steps-v1:47\n")

    def test_nested_skipped_arithmetic_rejects_undefined_and_effects(self) -> None:
        original = NESTED_SOURCE.read_text()
        variants = {
            "nested-selected-zero": original.replace(
                "((next & 1U) != 0U) &&",
                "((next & 1U) == 0U) &&",
            ),
            "nested-zero-divisor": original.replace("next / (next & 1U)", "next / 0U"),
            "nested-skipped-input": original.replace(
                "next / (next & 1U)", "next / (unsigned)getchar()"
            ),
            "nested-skipped-output": original.replace(
                "next / (next & 1U)", "next / (unsigned)putchar(65)"
            ),
            "nested-hidden-comma": original.replace(
                "next & 1U", "putchar(65), next & 1U", 1
            ),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            for label, candidate in variants.items():
                with self.subTest(label=label):
                    self.assertNotEqual(candidate, original)
                    source = Path(temporary) / f"{label}.c"
                    source.write_text(candidate)
                    guest = source.with_suffix(".malbolge")
                    refused = self.compile(source, guest, f"tests/{label}-v1")
                    self.assertNotEqual(refused.returncode, 0)
                    self.assertFalse(guest.exists())

    def test_nested_skipped_boolean_ast_is_authenticated(self) -> None:
        original = self.frontend_ast(NESTED_SOURCE)
        nodes = json.loads(original)["nodes"]
        logical = next(node for node in nodes if node.get("operation") == "||")
        comparison = next(
            node
            for node in nodes
            if node.get("operation") == "!="
            and node["parent"] != 0
            and node["span"]["begin"]["byte"] > logical["span"]["begin"]["byte"]
        )
        division = next(node for node in nodes if node.get("operation") == "/")
        inner = next(
            node
            for node in nodes
            if node["parent"] == logical["id"]
            and node["kind"] == "parenthesized-expression"
            and node["id"] > logical["id"] + 1
        )
        mutations = (
            ("logical-type", logical, "type", "u32"),
            ("logical-parent", logical, "parent", 0),
            ("logical-effect", logical, "reference", "external:getchar"),
            ("comparison-parent", comparison, "parent", 0),
            ("division-kind", division, "kind", "call-expression"),
            ("division-parent", division, "parent", 0),
            ("division-effect", division, "reference", "external:putchar"),
            ("inner-parent", inner, "parent", 0),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            for label, node, field, replacement in mutations:
                with self.subTest(label=label):
                    forged = json.loads(original)
                    forged["nodes"][node["id"] - 1][field] = replacement
                    self.reject_ast(forged, Path(temporary) / f"{label}.malbolge")

    def test_selected_undefined_and_hidden_effects_refuse(self) -> None:
        source_text = SOURCE.read_text()
        variants = {
            "selected-zero": source_text.replace("(next / (next & 1U))", "(next / 0U)"),
            "wrong-guard": source_text.replace(
                "((next & 1U) != 0U) &&",
                "((next & 1U) == 0U) &&",
            ),
            "skipped-output": source_text.replace(
                "(next / (next & 1U))",
                "(next / (unsigned)putchar(65))",
            ),
            "skipped-input": source_text.replace(
                "(next / (next & 1U))",
                "(next / (unsigned)getchar())",
            ),
            "unproved-comma": source_text.replace(
                "(next / (next & 1U))",
                "(next / (putchar(65), next & 1U))",
            ),
            "unproved-or-evaluation": or_source(source_text).replace(
                "((next & 1U) == 0U) ||",
                "((next & 1U) != 0U) ||",
            ),
        }
        for text in variants.values():
            self.assertNotEqual(text, source_text)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            for label, candidate in variants.items():
                with self.subTest(label=label):
                    source = Path(temporary) / f"{label}.c"
                    source.write_text(candidate)
                    guest = source.with_suffix(".malbolge")
                    refused = self.compile(source, guest, f"tests/{label}-logical-v1")
                    self.assertNotEqual(refused.returncode, 0)
                    self.assertFalse(guest.exists())

    def test_skipped_logical_rhs_remains_source_authenticated(self) -> None:
        original = self.frontend_ast(SOURCE)
        parsed = json.loads(original)
        nodes = parsed["nodes"]
        logic = next(node for node in nodes if node.get("operation") == "&&")
        division = next(node for node in nodes if node.get("operation") == "/")
        rhs = next(
            node
            for node in nodes
            if node.get("kind") == "parenthesized-expression"
            and node.get("parent") == logic["id"]
            and node["id"] > logic["id"]
        )
        for label, node, field, replacement in (
            ("logic-type", logic, "type", "u32"),
            ("logic-parent", logic, "parent", 0),
            ("division-kind", division, "kind", "call-expression"),
            ("division-type", division, "type", "i32"),
            ("division-parent", division, "parent", 0),
            ("division-hidden-effect", division, "reference", "external:getchar"),
            ("rhs-parent", rhs, "parent", 0),
        ):
            with self.subTest(label=label):
                forged = json.loads(original)
                forged["nodes"][node["id"] - 1][field] = replacement
                with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
                    self.reject_ast(forged, Path(temporary) / f"{label}.malbolge")


if __name__ == "__main__":
    unittest.main()
