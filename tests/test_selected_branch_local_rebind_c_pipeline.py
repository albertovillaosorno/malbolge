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
#   - Source-proven selected C branch assignments surviving branch exit.
# - Must-Not:
#   - Recover overwritten aliases or synthesize guest input on the host.
# - Allows:
#   - Inputs: pinned Clang C, source-checked JSON and binary guest stdin.
#   - Outputs: actual VM output or closed compiler refusal.
#   - Side effects: temporary compiler artifacts under .temp.
# - Split-When:
#   - General guest C control flow and local storage supersede this proof.
# - Merge-When:
#   - Source C assignment proof propagates all verified SSA identities.
# - Summary:
#   - A selected branch may return one authenticated guest-local binding.

"""Keep a freshly assigned guest byte live after a selected C branch."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from tests import test_source_local_alias_c_pipeline as aliases
from tests import test_static_for_break_c_pipeline as helpers
from tests.test_static_for_break_c_pipeline import (
    ADAPTER,
    FRONTEND,
    LAYOUT,
    ROOT,
    VM,
)


def source(*, condition: str = "1", assigned: str = "saved") -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int current = getchar();\n"
        "    int saved = current;\n"
        f"    if ({condition}) {{\n"
        f"        {assigned} = getchar();\n"
        f"        putchar({assigned});\n"
        "    } else {\n"
        "        putchar(getchar());\n"
        "    }\n"
        f"    putchar({assigned});\n"
        "    for (int i = 0; i < 3; ++i) {\n"
        "        int byte = getchar();\n"
        "        if (i % 2 == 0) {\n"
        "            putchar(byte);\n"
        "            continue;\n"
        "        }\n"
        "        putchar(getchar());\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class SelectedBranchLocalRebindCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(tool.is_file() for tool in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned frontend, adapter, layout and VM required")

    def test_selected_branch_rebind_survives_into_guest_stream(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "branch.c"
            guest = root / "branch.malbolge"
            path.write_text(source(), encoding="utf-8")
            built = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            self.assertEqual(built.returncode, 0, built.stderr)
            for data in (
                bytes((0, 255, 128, 1, 42, 13, 7)),
                hashlib.shake_256(b"selected-C-branch-guest-rebinding").digest(7),
            ):
                with self.subTest(data=data):
                    run = helpers.StaticForBreakCPipelineTests.vm(guest, data)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(
                        run.stdout,
                        data[1:2] * 2 + data[2:3] + data[4:5] + data[5:],
                    )
                    self.assertEqual(run.stderr, b"malbolge-steps-v1:14\n")

    def test_unselected_assignment_keeps_original_live_alias(self) -> None:
        # A skipped assignment does not clobber a source-proven live alias.
        program = source(condition="0").replace(
            "    } else {\n        putchar(getchar());\n    }\n",
            "    }\n",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "unselected.c"
            guest = root / "unselected.malbolge"
            path.write_text(program, encoding="utf-8")
            built = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            self.assertEqual(built.returncode, 0, built.stderr)
            for data in (
                bytes((0, 255, 128, 1, 42, 13)),
                hashlib.shake_256(b"skipped-C-branch-write").digest(6),
            ):
                run = helpers.StaticForBreakCPipelineTests.vm(guest, data)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(
                    run.stdout,
                    data[:2] + data[3:],
                )
                self.assertEqual(run.stderr, b"malbolge-steps-v1:12\n")

    def test_stale_previous_alias_and_unproven_assignment_refuse(self) -> None:
        replacements = (
            "current = getchar();",
            "saved = (getchar());",
            "saved += getchar();",
            "saved = getchar() + 0;",
            "saved=getchar();",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, assignment in enumerate(replacements):
                with self.subTest(assignment=assignment):
                    text = source().replace("saved = getchar();", assignment, 1)
                    if index == 0:
                        text = text.replace(
                            "    putchar(saved);\n    for",
                            "    putchar(current);\n    for",
                        )
                    path = root / f"invalid-{index}.c"
                    guest = root / f"invalid-{index}.malbolge"
                    path.write_text(text, encoding="utf-8")
                    built = helpers.StaticForBreakCPipelineTests.compile(path, guest)
                    self.assertNotEqual(built.returncode, 0)
                    self.assertFalse(guest.exists())

    def test_forged_branch_assignment_and_missing_source_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "original.c"
            path.write_text(source(), encoding="utf-8")
            normalized = helpers.StaticForBreakCPipelineTests.normalized(path)
            assignment = next(
                node
                for node in normalized["nodes"]
                if node["kind"] == "binary-expression"
                and node.get("operation") == "="
                and node["span"]["begin"]["line"] == 6
            )
            for index, (offset, field, value) in enumerate(
                (
                    (0, "parent", 0),
                    (0, "operation", "+="),
                    (1, "reference", "other@0"),
                    (2, "parent", 0),
                    (3, "type", "u8"),
                    (4, "parent", 0),
                )
            ):
                with self.subTest(index=index):
                    forged = copy.deepcopy(normalized)
                    node = next(
                        node
                        for node in forged["nodes"]
                        if node["id"] == assignment["id"] + offset
                    )
                    node[field] = value
                    guest = root / f"forged-{index}.malbolge"
                    built = aliases.SourceLocalAliasCPipelineTests.adapter(
                        forged, guest, path
                    )
                    self.assertNotEqual(built.returncode, 0)
                    self.assertFalse(guest.exists())
            guest = root / "missing-source.malbolge"
            built = aliases.SourceLocalAliasCPipelineTests.adapter(
                normalized, guest, None
            )
            self.assertNotEqual(built.returncode, 0)
            self.assertFalse(guest.exists())


if __name__ == "__main__":
    unittest.main()
