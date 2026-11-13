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
#   - Source-authenticated equivalent local byte aliases in complete C streams.
# - Must-Not:
#   - Treat overwritten or stale C variables as the current guest byte.
# - Allows:
#   - Inputs: pinned Clang C, binary guest stdin, and forged normalized JSON.
#   - Outputs: actual Malbolge VM parity or closed compiler refusals.
#   - Side effects: isolated temporary test artifacts.
# - Split-When:
#   - General guest mutable storage replaces this accumulator identity proof.
# - Merge-When:
#   - General C local SSA bookkeeping subsumes equivalent source aliases.
# - Summary:
#   - Original and copied C local names share one resident guest byte.

"""A copied C input stays readable through both verified local names."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from tests import test_source_local_alias_c_pipeline as aliases
from tests import test_static_for_break_c_pipeline as helpers
from tests.test_static_for_break_c_pipeline import ADAPTER, FRONTEND, LAYOUT, ROOT, VM


def source(*, loop_copy: bool = True, top_output: str = "current") -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int current = getchar();\n"
        "    int saved = current;\n"
        f"    putchar({top_output});\n"
        "    putchar(saved);\n"
        "    for (int i = 0; i < 3; ++i) {\n"
        "        int byte = getchar();\n"
        + ("        int copy = byte;\n" if loop_copy else "")
        + "        if (i == 1) {\n"
        + (
            "            putchar(copy);\n"
            if loop_copy
            else "            putchar(byte);\n"
        )
        + "            continue;\n"
        "        }\n"
        "        putchar(byte);\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


def rebinding_source(assignment: str = "current = saved;") -> str:
    return source().replace(
        "    int saved = current;\n",
        f"    int saved = current;\n    saved = getchar();\n    {assignment}\n",
    )


class LiveAliasReassignmentCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(tool.is_file() for tool in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned Clang, adapter, layout and VM required")

    def test_original_and_copy_in_compound_loop_stream(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "whole.c"
            guest = root / "whole.malbolge"
            path.write_text(source(), encoding="utf-8")
            built = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            self.assertEqual(built.returncode, 0, built.stderr)
            for data in (
                bytes((0, 255, 128, 1, 42)),
                hashlib.shake_256(b"verified-dual-alias-c-stream").digest(5),
            ):
                with self.subTest(data=data):
                    run = helpers.StaticForBreakCPipelineTests.vm(guest, data)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(run.stdout, data[:1] + data)
                    self.assertEqual(run.stderr, b"malbolge-steps-v1:12\n")

    def test_original_name_after_copy_with_loop_emits_same_guest_value(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "original.c"
            guest = root / "original.malbolge"
            path.write_text(source(loop_copy=False), encoding="utf-8")
            built = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            self.assertEqual(built.returncode, 0, built.stderr)
            for data in (bytes((255, 0, 128, 1, 42)), bytes((19, 3, 2, 1, 0))):
                run = helpers.StaticForBreakCPipelineTests.vm(guest, data)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, data[:1] + data)
                self.assertEqual(run.stderr, b"malbolge-steps-v1:12\n")

    def test_copy_rebinds_stale_c_local_to_new_guest_input(self) -> None:
        program = rebinding_source()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "rebind.c"
            guest = root / "rebind.malbolge"
            path.write_text(program, encoding="utf-8")
            built = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            self.assertEqual(built.returncode, 0, built.stderr)
            for data in (
                bytes((0, 255, 128, 1, 42, 13)),
                hashlib.shake_256(b"source-local-rebinding-2026").digest(6),
            ):
                with self.subTest(data=data):
                    run = helpers.StaticForBreakCPipelineTests.vm(guest, data)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(run.stdout, data[1:2] + data[1:])
                    self.assertEqual(run.stderr, b"malbolge-steps-v1:13\n")

    def test_rebound_byte_can_be_copied_from_either_live_name(self) -> None:
        program = (
            rebinding_source()
            .replace(
                "    current = saved;\n",
                "    current = saved;\n    int snapshot = saved;\n",
            )
            .replace("    putchar(saved);", "    putchar(snapshot);")
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "copy-rebound.c"
            guest = root / "copy-rebound.malbolge"
            path.write_text(program, encoding="utf-8")
            built = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            self.assertEqual(built.returncode, 0, built.stderr)
            for data in (
                bytes((0, 255, 128, 1, 42, 13)),
                hashlib.shake_256(b"C-live-stale-identity-proof").digest(6),
            ):
                run = helpers.StaticForBreakCPipelineTests.vm(guest, data)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, data[1:2] + data[1:])
                self.assertEqual(run.stderr, b"malbolge-steps-v1:13\n")

    def test_unsupported_copy_assignments_refuse(self) -> None:
        assignments = (
            "current = saved + 0;",
            "current = saved + 1;",
            "current = (unsigned char)saved;",
            "current += saved;",
            "current = getchar();",
            "current = current;",
            "saved = current;",
            "current = (saved, saved);",
            "current=saved;",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, assignment in enumerate(assignments):
                with self.subTest(assignment=assignment):
                    path = root / f"unsupported-{index}.c"
                    guest = root / f"unsupported-{index}.malbolge"
                    path.write_text(rebinding_source(assignment), encoding="utf-8")
                    built = helpers.StaticForBreakCPipelineTests.compile(path, guest)
                    self.assertNotEqual(built.returncode, 0)
                    self.assertFalse(guest.exists())

    def test_forged_copy_assignment_nodes_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "copy-assignment.c"
            path.write_text(rebinding_source(), encoding="utf-8")
            normalized = helpers.StaticForBreakCPipelineTests.normalized(path)
            assignment = next(
                n
                for n in normalized["nodes"]
                if n["kind"] == "binary-expression"
                and n.get("operation") == "="
                and n["span"]["begin"]["line"] == 6
            )
            first_id = assignment["id"]
            variants = (
                (0, "operation", "+"),
                (0, "type", "u32"),
                (0, "parent", 1),
                (1, "reference", "other@0"),
                (1, "type", "u32"),
                (2, "operation", "integral-cast"),
                (2, "parent", 1),
                (3, "reference", "current@47"),
                (3, "type", "u8"),
                (3, "span", {"begin": {"byte": 1}}),
            )
            for index, (offset, field, value) in enumerate(variants):
                with self.subTest(index=index):
                    forged = copy.deepcopy(normalized)
                    node = next(
                        n for n in forged["nodes"] if n["id"] == first_id + offset
                    )
                    node[field] = value
                    guest = root / f"forged-assignment-{index}.malbolge"
                    built = aliases.SourceLocalAliasCPipelineTests.adapter(
                        forged, guest, path
                    )
                    self.assertNotEqual(built.returncode, 0)
                    self.assertFalse(guest.exists())
            standalone = (
                "#include <stdio.h>\n"
                "void stream(void) {\n"
                "    int current = getchar();\n"
                "    current = current;\n"
                "    putchar(current);\n"
                "}\n"
            )
            bare = root / "standalone.c"
            bare.write_text(standalone, encoding="utf-8")
            normalized = helpers.StaticForBreakCPipelineTests.normalized(bare)
            guest = root / "standalone-no-source.malbolge"
            built = aliases.SourceLocalAliasCPipelineTests.adapter(
                normalized, guest, None
            )
            self.assertNotEqual(built.returncode, 0)
            self.assertFalse(guest.exists())

    def test_unsupported_stale_and_modified_local_sources_refuse(self) -> None:
        invalid = (
            source().replace("int copy = byte;", "int copy = byte + 1;"),
            source().replace("putchar(byte);", "putchar(byte + 1);"),
            source().replace("int saved = current;", "int saved = getchar();"),
            source().replace("int saved = current;", "int saved = current + 0;"),
            source().replace(
                "    putchar(saved);", "    getchar();\n    putchar(saved);"
            ),
            source().replace(
                "int copy = byte;", "int copy = byte;\n        getchar();"
            ),
            source().replace(
                "int copy = byte;", "int copy = byte;\n        byte = getchar();"
            ),
            source()
            .replace(
                "int copy = byte;",
                "int copy = byte;\n        byte = getchar();",
            )
            .replace("putchar(byte);", "putchar(copy);"),
            source().replace(
                "int copy = byte;", "int copy = byte;\n        copy = getchar();"
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, candidate in enumerate(invalid):
                with self.subTest(index=index):
                    path = root / f"invalid-{index}.c"
                    guest = root / f"invalid-{index}.malbolge"
                    path.write_text(candidate, encoding="utf-8")
                    built = helpers.StaticForBreakCPipelineTests.compile(path, guest)
                    self.assertNotEqual(built.returncode, 0)
                    self.assertFalse(guest.exists())

    def test_forged_copy_binding_and_missing_source_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "source.c"
            path.write_text(source(), encoding="utf-8")
            normalized = helpers.StaticForBreakCPipelineTests.normalized(path)
            declaration = next(
                n
                for n in normalized["nodes"]
                if n["kind"] == "declaration-statement"
                and n["span"]["begin"]["line"] == 4
            )
            id_ = declaration["id"]
            for index, (offset, field, value) in enumerate(
                (
                    (0, "parent", 0),
                    (1, "name", "other"),
                    (2, "operation", "integral-cast"),
                    (3, "reference", "stale@0"),
                    (3, "type", "u8"),
                )
            ):
                with self.subTest(index=index):
                    forged = copy.deepcopy(normalized)
                    node = next(n for n in forged["nodes"] if n["id"] == id_ + offset)
                    node[field] = value
                    guest = root / f"forged-{index}.malbolge"
                    result = aliases.SourceLocalAliasCPipelineTests.adapter(
                        forged, guest, path
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(guest.exists())
            guest = root / "missing-source.malbolge"
            result = aliases.SourceLocalAliasCPipelineTests.adapter(
                normalized, guest, None
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(guest.exists())


if __name__ == "__main__":
    unittest.main()
