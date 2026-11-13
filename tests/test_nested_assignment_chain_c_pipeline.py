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
#   - Source-authenticated nested assignment-valued byte output.
# - Must-Not:
#   - Reuse stale guest byte state or silently simulate guest I/O on the host.
# - Allows:
#   - Inputs: pinned Clang C and adversarial normalized JSON.
#   - Outputs: real VM binary parity or fail-closed compilation.
#   - Side effects: temporary isolated test artifacts.
# - Split-When:
#   - General guest C call and assignment lowering subsumes this proof.
# - Merge-When:
#   - Source byte output proofs share one canonical call grammar.
# - Summary:
#   - Nested putchar returns forward one fresh assigned guest byte.

"""Check original C nested byte-assignment calls in actual Malbolge."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from tests import test_source_local_alias_c_pipeline as aliases
from tests import test_static_for_break_c_pipeline as helpers
from tests.test_static_for_break_c_pipeline import ADAPTER, FRONTEND, LAYOUT, ROOT, VM


def compound_source(
    nested: str = "putchar(putchar(current = getchar()));",
    trailing: str = "putchar(putchar(current));",
) -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int current = getchar();\n"
        "    putchar(current);\n"
        "    for (int i = 0; i < 3; ++i) {\n"
        "        if (i % 2 == 0) {\n"
        f"            {nested}\n"
        "            continue;\n"
        "        }\n"
        "        putchar(current);\n"
        "    }\n"
        f"    {trailing}\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class NestedAssignmentChainCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(tool.is_file() for tool in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C frontend and normative guest tools required")

    def test_compound_branch_continue_loop_matches_binary_guest_oracle(self) -> None:
        """The original full C source must execute real input and output."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, target = root / "compound.c", root / "compound.malbolge"
            path.write_text(compound_source(), encoding="utf-8")
            compiled = helpers.StaticForBreakCPipelineTests.compile(path, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255, 128, 1)),
                hashlib.shake_256(b"nested-assign-compound-2026").digest(4),
                bytes((255, 0, 1, 128)),
                *(
                    hashlib.shake_256(
                        b"nested-assignment-seed-" + bytes((seed,))
                    ).digest(4)
                    for seed in range(16)
                ),
            ):
                with self.subTest(data=data):
                    vm = helpers.StaticForBreakCPipelineTests.vm(target, data)
                    self.assertEqual(vm.returncode, 0, vm.stderr)
                    expected = bytes(
                        (
                            data[0],
                            data[1],
                            data[1],
                            data[1],
                            data[2],
                            data[2],
                            data[2],
                            data[2],
                            data[3],
                        )
                    )
                    self.assertEqual(vm.stdout, expected)
                    self.assertEqual(vm.stderr, b"malbolge-steps-v1:14\n")

    def test_top_level_nested_rebind_retains_C_destination(self) -> None:
        """One nested read rebinds current for later source-C consumers."""
        program = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    int current = getchar();\n"
            "    putchar(putchar(current = getchar()));\n"
            "    putchar(current);\n"
            "    for (int i = 0; i < 2; ++i) {\n"
            "        putchar(current);\n"
            "    }\n"
            "    putchar(getchar());\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, target = root / "top.c", root / "top.malbolge"
            path.write_text(program, encoding="utf-8")
            compiled = helpers.StaticForBreakCPipelineTests.compile(path, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255, 128)),
                hashlib.shake_256(b"nested-assign-top").digest(3),
            ):
                vm = helpers.StaticForBreakCPipelineTests.vm(target, data)
                self.assertEqual(vm.returncode, 0, vm.stderr)
                self.assertEqual(vm.stdout, bytes((data[1],) * 5 + (data[2],)))
                self.assertEqual(vm.stderr, b"malbolge-steps-v1:10\n")

    def test_three_deep_selected_arm_and_zero_trip_body(self) -> None:
        """Nested return chaining and skipped reads use different effects."""
        program = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    int current = getchar();\n"
            "    if (1) {\n"
            "        putchar(putchar(putchar(current = getchar())));\n"
            "        putchar(current);\n"
            "    }\n"
            "    for (int i = 0; i < 0; ++i) {\n"
            "        putchar(putchar(current = getchar()));\n"
            "    }\n"
            "    putchar(current);\n"
            "    putchar(getchar());\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, target = root / "branch.c", root / "branch.malbolge"
            path.write_text(program, encoding="utf-8")
            compiled = helpers.StaticForBreakCPipelineTests.compile(path, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((255, 0, 128)),
                hashlib.shake_256(b"nested-assign-depth-three").digest(3),
            ):
                vm = helpers.StaticForBreakCPipelineTests.vm(target, data)
                self.assertEqual(vm.returncode, 0, vm.stderr)
                self.assertEqual(vm.stdout, bytes((data[1],) * 5 + (data[2],)))
                self.assertEqual(vm.stderr, b"malbolge-steps-v1:10\n")

    def test_unsupported_source_variants_never_publish_guest(self) -> None:
        cases = (
            "putchar(putchar(current + getchar()));",
            "putchar(putchar(current == getchar()));",
            "putchar(putchar(current = getchar() + 1));",
            "putchar(putchar(current = putchar(getchar())));",
            "putchar(putchar(current = getchar(), current));",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, nested in enumerate(cases):
                with self.subTest(index=index):
                    path = root / f"invalid-{index}.c"
                    target = root / f"invalid-{index}.malbolge"
                    path.write_text(compound_source(nested), encoding="utf-8")
                    compiled = helpers.StaticForBreakCPipelineTests.compile(
                        path, target
                    )
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_nested_call_and_assignment_nodes_refuse(self) -> None:
        """An output cannot be minted by editing normalized Clang ancestry."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "source.c"
            path.write_text(compound_source(), encoding="utf-8")
            normalized = helpers.StaticForBreakCPipelineTests.normalized(path)
            nodes = normalized["nodes"]
            outer = next(
                n
                for n in nodes
                if n["kind"] == "call-expression"
                and n["reference"] == "external:putchar"
                and n["span"]["begin"]["line"] == 7
            )
            at = nodes.index(outer)
            edits = (
                (0, "reference", "external:getchar"),
                (0, "parent", 2),
                (0, "type", "u32"),
                (1, "operation", "integral-cast"),
                (2, "reference", "external:getchar"),
                (3, "parent", 2),
                (4, "type", "ptr(fn()->i32)"),
                (5, "reference", "external:getchar"),
                (6, "operation", "+"),
                (6, "parent", 2),
                (7, "reference", "other@47"),
                (8, "kind", "cast-expression"),
                (9, "operation", "integral-cast"),
                (10, "parent", 2),
            )
            for index, (offset, field, value) in enumerate(edits):
                with self.subTest(index=index):
                    forged = copy.deepcopy(normalized)
                    forged["nodes"][at + offset][field] = value
                    target = root / f"forged-{index}.malbolge"
                    result = aliases.SourceLocalAliasCPipelineTests.adapter(
                        forged, target, path
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())
            forged = copy.deepcopy(normalized)
            forged["nodes"][at]["span"]["end"]["column"] -= 1
            target = root / "forged-span.malbolge"
            result = aliases.SourceLocalAliasCPipelineTests.adapter(
                forged, target, path
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(target.exists())

    def test_missing_source_and_coherent_operator_spoof_refuse(self) -> None:
        """The AST cannot invent an assignment token absent from original C."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "source.c"
            program = compound_source()
            path.write_text(program, encoding="utf-8")
            normalized = helpers.StaticForBreakCPipelineTests.normalized(path)
            target = root / "missing.malbolge"
            result = aliases.SourceLocalAliasCPipelineTests.adapter(
                normalized, target, None
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(target.exists())
            edited = root / "edited.c"
            edited.write_text(
                program.replace("current = getchar()", "current + getchar()"),
                encoding="utf-8",
            )
            forged = copy.deepcopy(normalized)
            forged["source"]["sha256"] = hashlib.sha256(edited.read_bytes()).hexdigest()
            result = aliases.SourceLocalAliasCPipelineTests.adapter(
                forged, target, edited
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(target.exists())

    def test_stale_alias_after_nested_rebind_refuses(self) -> None:
        program = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    int current = getchar();\n"
            "    int prior = current;\n"
            "    putchar(putchar(current = getchar()));\n"
            "    putchar(prior);\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, target = root / "stale.c", root / "stale.malbolge"
            path.write_text(program, encoding="utf-8")
            result = helpers.StaticForBreakCPipelineTests.compile(path, target)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
