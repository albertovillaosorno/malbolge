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
#   - Preserve source-authenticated live C bytes across bounded loops.
# - Must-Not:
#   - Resurrect a stale byte after guest input or forge C loop bindings.
# - Allows:
#   - Inputs: pinned C frontend, source proof and binary guest stdin.
#   - Outputs: actual Malbolge VM parity or closed compiler refusal.
#   - Side effects: isolated temporary artifacts under .temp.
# - Split-When:
#   - General guest C control flow supersedes finite source-time replay.
# - Merge-When:
#   - C lexical byte state is uniformly tracked through loop scopes.
# - Summary:
#   - A counted C loop may read an already resident outer byte.

"""Verify a real C program retaining a guest byte across a counted loop."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from tests import test_source_local_alias_c_pipeline as aliases
from tests import test_static_for_break_c_pipeline as helpers
from tests.test_static_for_break_c_pipeline import ADAPTER, FRONTEND, LAYOUT, ROOT, VM


def source(*, bound: int = 4, loop_read: str = "putchar(current);") -> str:
    """Build one complete source-C stream with a counted output loop."""
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int current = getchar();\n"
        "    putchar(current);\n"
        "    if (1) {\n"
        "        int alias = current;\n"
        "        putchar(alias);\n"
        "    }\n"
        f"    for (int i = 0; i < {bound}; ++i) {{\n"
        "        if (i % 2 == 0) {\n"
        f"            {loop_read}\n"
        "            continue;\n"
        "        }\n"
        f"        {loop_read}\n"
        "    }\n"
        "    putchar(current);\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class OuterLiveLoopCPipelineTests(unittest.TestCase):
    """The loop must reuse one resident guest byte, not host-side output."""

    def setUp(self) -> None:
        if not all(tool.is_file() for tool in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C frontend, adapter, layout and VM required")

    def test_full_loop_and_branch_preserve_outer_byte(self) -> None:
        """A loop-selected continue must not destroy the live C binding."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest = root / "loop.c", root / "loop.malbolge"
            path.write_text(source(), encoding="utf-8")
            built = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            self.assertEqual(built.returncode, 0, built.stderr)
            for data in (
                bytes((0, 255)),
                bytes((128, 1)),
                hashlib.shake_256(b"outer-C-byte-counted-loop").digest(2),
            ):
                with self.subTest(data=data):
                    run = helpers.StaticForBreakCPipelineTests.vm(guest, data)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(run.stdout, data[:1] * 7 + data[1:])
                    self.assertEqual(run.stderr, b"malbolge-steps-v1:11\n")

    def test_zero_trip_loop_does_not_invalidate_outer_byte(self) -> None:
        """The source-checked dead body must have zero guest effects."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest = root / "zero.c", root / "zero.malbolge"
            path.write_text(source(bound=0), encoding="utf-8")
            built = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            self.assertEqual(built.returncode, 0, built.stderr)
            for data in (bytes((255, 0)), bytes((1, 128))):
                run = helpers.StaticForBreakCPipelineTests.vm(guest, data)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, data[:1] * 3 + data[1:])
                self.assertEqual(run.stderr, b"malbolge-steps-v1:7\n")

    def test_proven_equivalent_outer_alias_survives_loop(self) -> None:
        """A source-proven C alias may be read even when it is not latest."""
        program = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    int current = getchar();\n"
            "    int saved = current;\n"
            "    for (int i = 0; i < 3; ++i) {\n"
            "        if (i % 2 == 0) {\n"
            "            putchar(current);\n"
            "            continue;\n"
            "        }\n"
            "        putchar(current);\n"
            "    }\n"
            "    putchar(saved);\n"
            "    putchar(getchar());\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest = root / "alias.c", root / "alias.malbolge"
            path.write_text(program, encoding="utf-8")
            built = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            self.assertEqual(built.returncode, 0, built.stderr)
            for data in (
                bytes((255, 0)),
                hashlib.shake_256(b"C-outer-equivalent-byte").digest(2),
            ):
                run = helpers.StaticForBreakCPipelineTests.vm(guest, data)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, data[:1] * 4 + data[1:])
                self.assertEqual(run.stderr, b"malbolge-steps-v1:8\n")

    def test_source_names_and_missing_witness_fail_closed(self) -> None:
        """A forged hash may not change the local read inside a counted loop."""
        program = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    int current = getchar();\n"
            "    int another = getchar();\n"
            "    for (int i = 0; i < 2; ++i) {\n"
            "        putchar(another);\n"
            "    }\n"
            "    putchar(getchar());\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest = root / "source.c", root / "source.malbolge"
            path.write_text(program, encoding="utf-8")
            built = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            self.assertEqual(built.returncode, 0, built.stderr)
            run = helpers.StaticForBreakCPipelineTests.vm(guest, bytes((0, 255, 128)))
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(run.stdout, bytes((255, 255, 128)))
            normalized = helpers.StaticForBreakCPipelineTests.normalized(path)
            missing = root / "missing.malbolge"
            refused = aliases.SourceLocalAliasCPipelineTests.adapter(
                normalized, missing, None
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertFalse(missing.exists())
            changed = root / "changed.c"
            changed.write_text(
                program.replace("putchar(another);", "putchar(current);"),
                encoding="utf-8",
            )
            forged = copy.deepcopy(normalized)
            forged["source"]["sha256"] = hashlib.sha256(
                changed.read_bytes()
            ).hexdigest()
            false_guest = root / "forged.malbolge"
            refused = aliases.SourceLocalAliasCPipelineTests.adapter(
                forged, false_guest, changed
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertFalse(false_guest.exists())

    def test_nested_counted_loops_retain_outer_value(self) -> None:
        """Nested finite loops do not require a spurious guest read."""
        program = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    int current = getchar();\n"
            "    for (int i = 0; i < 2; ++i) {\n"
            "        for (int i = 0; i < 2; ++i) {\n"
            "            putchar(current);\n"
            "        }\n"
            "    }\n"
            "    putchar(current);\n"
            "    putchar(getchar());\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest = root / "nested.c", root / "nested.malbolge"
            path.write_text(program, encoding="utf-8")
            built = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            self.assertEqual(built.returncode, 0, built.stderr)
            for data in (bytes((0, 255)), bytes((128, 1))):
                run = helpers.StaticForBreakCPipelineTests.vm(guest, data)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, data[:1] * 5 + data[1:])
                self.assertEqual(run.stderr, b"malbolge-steps-v1:9\n")

    def test_stale_and_unlowerable_loop_values_refuse(self) -> None:
        """No ignored read or unproved runtime arithmetic may survive."""
        cases = (
            source(loop_read="putchar(current + 0);"),
            source(loop_read="putchar((unsigned char)(current + 1));"),
            source().replace(
                "    putchar(current);\n    putchar(getchar());\n",
                "    putchar(getchar());\n    putchar(current);\n",
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, text in enumerate(cases):
                with self.subTest(index=index):
                    path = root / f"invalid-{index}.c"
                    guest = root / f"invalid-{index}.malbolge"
                    path.write_text(text, encoding="utf-8")
                    built = helpers.StaticForBreakCPipelineTests.compile(path, guest)
                    self.assertNotEqual(built.returncode, 0)
                    self.assertFalse(guest.exists())


if __name__ == "__main__":
    unittest.main()
