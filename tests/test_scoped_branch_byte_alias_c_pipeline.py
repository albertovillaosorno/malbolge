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
#   - Source-proven block-local byte copies in selected and skipped C arms.
# - Must-Not:
#   - Export a block-local C name or recover an overwritten guest byte.
# - Allows:
#   - Inputs: pinned C frontend, source-checked JSON and binary guest stdin.
#   - Outputs: actual guest VM parity or explicit compiler refusal.
#   - Side effects: temporary generated artifacts under .temp.
# - Split-When:
#   - General guest C lexical storage replaces this bounded source proof.
# - Merge-When:
#   - General C SSA lexical-scope proof subsumes branch-local aliases.
# - Summary:
#   - A selected C arm can copy its existing live byte into a scoped alias.

"""Authenticate block-local input aliases across complete C guest streams."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from tests import test_source_local_alias_c_pipeline as aliases
from tests import test_static_for_break_c_pipeline as helpers
from tests.test_static_for_break_c_pipeline import ADAPTER, FRONTEND, LAYOUT, ROOT, VM


def source(
    *,
    condition: str = "1",
    declaration: str = "int scoped = current;",
    scoped_output: str = "scoped",
    alternative: str = "putchar(getchar());",
) -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int current = getchar();\n"
        f"    if ({condition}) {{\n"
        f"        {declaration}\n"
        f"        putchar({scoped_output});\n"
        "        putchar(current);\n"
        "    } else {\n"
        f"        {alternative}\n"
        "    }\n"
        "    putchar(current);\n"
        "    for (int i = 0; i < 3; ++i) {\n"
        "        int byte = getchar();\n"
        "        if (i % 2 == 0) {\n"
        "            int alias = byte;\n"
        "            putchar(alias);\n"
        "            continue;\n"
        "        }\n"
        "        putchar(byte);\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


def shadow_source(*, condition: str = "1", after: str = "putchar(getchar());") -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int current = getchar();\n"
        f"    if ({condition}) {{\n"
        "        int current = getchar();\n"
        "        putchar(current);\n"
        "        putchar(current);\n"
        "    } else {\n"
        "        putchar(current);\n"
        "    }\n"
        f"    {after}\n"
        "    for (int i = 0; i < 3; ++i) {\n"
        "        int byte = getchar();\n"
        "        if (i % 2 == 0) {\n"
        "            putchar(byte);\n"
        "            continue;\n"
        "        }\n"
        "        putchar(getchar());\n"
        "    }\n"
        "}\n"
    )


class ScopedBranchByteAliasCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(tool.is_file() for tool in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned Clang, adapter, layout and VM required")

    def test_selected_scoped_alias_and_whole_c_loop_match_binary_vm(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "scoped.c"
            guest = root / "scoped.malbolge"
            path.write_text(source(), encoding="utf-8")
            compiled = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255, 128, 1, 42)),
                hashlib.shake_256(b"scoped-source-C-guest-alias").digest(5),
            ):
                with self.subTest(data=data):
                    run = helpers.StaticForBreakCPipelineTests.vm(guest, data)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(run.stdout, data[:1] * 3 + data[1:])
                    self.assertEqual(run.stderr, b"malbolge-steps-v1:13\n")

    def test_unselected_scoped_alias_is_verified_without_guest_effect(self) -> None:
        text = source(condition="0", alternative="putchar(current);")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "unselected.c"
            guest = root / "unselected.malbolge"
            path.write_text(text, encoding="utf-8")
            compiled = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((255, 0, 128, 13, 1)),
                hashlib.shake_256(b"unselected-source-C-scoped-alias").digest(5),
            ):
                run = helpers.StaticForBreakCPipelineTests.vm(guest, data)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, data[:1] * 2 + data[1:])
                self.assertEqual(run.stderr, b"malbolge-steps-v1:12\n")

    def test_selected_c_shadow_reads_new_guest_byte(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "shadow.c"
            guest = root / "shadow.malbolge"
            path.write_text(shadow_source(), encoding="utf-8")
            compiled = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255, 128, 1, 42, 13, 7)),
                hashlib.shake_256(b"C-fresh-scoped-input-shadow").digest(7),
            ):
                with self.subTest(data=data):
                    run = helpers.StaticForBreakCPipelineTests.vm(guest, data)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(
                        run.stdout,
                        data[1:2] * 2 + data[2:4] + data[5:],
                    )
                    self.assertEqual(run.stderr, b"malbolge-steps-v1:14\n")

    def test_skipped_shadow_preserves_outer_live_byte(self) -> None:
        text = shadow_source(condition="0", after="putchar(current);")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "skipped.c"
            guest = root / "skipped.malbolge"
            path.write_text(text, encoding="utf-8")
            compiled = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255, 128, 1, 42)),
                hashlib.shake_256(b"C-dead-local-shadow-proof").digest(5),
            ):
                run = helpers.StaticForBreakCPipelineTests.vm(guest, data)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, data[:1] * 2 + data[1:2] + data[3:])
                self.assertEqual(run.stderr, b"malbolge-steps-v1:11\n")

    def test_selected_shadow_rejects_stale_outer_local(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "stale.c"
            guest = root / "stale.malbolge"
            path.write_text(shadow_source(after="putchar(current);"), encoding="utf-8")
            compiled = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            self.assertNotEqual(compiled.returncode, 0)
            self.assertFalse(guest.exists())

    def test_shadowed_input_requires_source_evidence(self) -> None:
        # An adversarial JSON transcript must not turn a C constant into a
        # fresh guest read merely by retaining Clang's old normalized nodes.
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            original = root / "original.c"
            original.write_text(shadow_source(), encoding="utf-8")
            normalized = helpers.StaticForBreakCPipelineTests.normalized(original)
            guest = root / "missing.malbolge"
            missing = aliases.SourceLocalAliasCPipelineTests.adapter(
                normalized, guest, None
            )
            self.assertNotEqual(missing.returncode, 0)
            self.assertFalse(guest.exists())

            replacement = shadow_source().replace(
                "        int current = getchar();",
                "        int current = 123456789;",
                1,
            )
            mutated = root / "mutated.c"
            mutated.write_text(replacement, encoding="utf-8")
            forged = copy.deepcopy(normalized)
            forged["source"]["sha256"] = hashlib.sha256(
                mutated.read_bytes()
            ).hexdigest()
            guest = root / "forged.malbolge"
            result = aliases.SourceLocalAliasCPipelineTests.adapter(
                forged, guest, mutated
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(guest.exists())

    def test_unsupported_scoped_alias_expressions_refuse(self) -> None:
        cases = (
            ("int scoped = current + 0;", "scoped"),
            ("int scoped = current + 1;", "scoped"),
            ("int scoped = getchar();", "scoped"),
            ("int scoped = (unsigned char)current;", "scoped"),
            ("int scoped=current;", "scoped"),
            ("int scoped = current;", "current + 0"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, (declaration, output) in enumerate(cases):
                with self.subTest(case=index):
                    path = root / f"invalid-{index}.c"
                    guest = root / f"invalid-{index}.malbolge"
                    path.write_text(
                        source(declaration=declaration, scoped_output=output),
                        encoding="utf-8",
                    )
                    compiled = helpers.StaticForBreakCPipelineTests.compile(path, guest)
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(guest.exists())

    def test_forged_scoped_alias_nodes_and_missing_source_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "scoped.c"
            path.write_text(source(), encoding="utf-8")
            normalized = helpers.StaticForBreakCPipelineTests.normalized(path)
            declaration = next(
                node
                for node in normalized["nodes"]
                if node["kind"] == "declaration-statement"
                and node["span"]["begin"]["line"] == 5
            )
            changes = (
                (0, "parent", 0),
                (1, "type", "u8"),
                (1, "reference", "other@0"),
                (2, "operation", "integral-cast"),
                (3, "reference", "other@0"),
                (3, "parent", 0),
            )
            for index, (offset, field, value) in enumerate(changes):
                with self.subTest(case=index):
                    forged = copy.deepcopy(normalized)
                    item = next(
                        node
                        for node in forged["nodes"]
                        if node["id"] == declaration["id"] + offset
                    )
                    item[field] = value
                    guest = root / f"forged-{index}.malbolge"
                    compiled = aliases.SourceLocalAliasCPipelineTests.adapter(
                        forged, guest, path
                    )
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(guest.exists())
            guest = root / "no-source.malbolge"
            compiled = aliases.SourceLocalAliasCPipelineTests.adapter(
                normalized, guest, None
            )
            self.assertNotEqual(compiled.returncode, 0)
            self.assertFalse(guest.exists())


if __name__ == "__main__":
    unittest.main()
