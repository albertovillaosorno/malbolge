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
#   - Assignment in a C comma-output argument retains the guest input byte.
# - Must-Not:
#   - Restore a stale C alias or substitute host output for guest semantics.
# - Allows:
#   - Inputs: pinned Clang C, binary VM stdin, forged normalized AST.
#   - Outputs: guest parity or explicit refusal without publication.
#   - Side effects: temporary test files only.
# - Split-When:
#   - A general guest C expression runtime subsumes bounded byte proofs.
# - Merge-When:
#   - Comma effects become generic SSA guest expression lowering.
# - Summary:
#   - Source-checked comma assignment followed by the rebound C local.
# - Description:
#   - Compares a complete C branch/loop stream against actual guest bytes.
# - Usage:
#   - Run the comma-assigned-output unittest module.
# - Defaults:
#   - All guest I/O is isolated in temporary test files.

"""Whole-source guest parity for output of a comma-rebound C byte."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from typing import cast, override

from tests import test_source_local_alias_c_pipeline as alias
from tests import test_static_for_break_c_pipeline as pipeline

ROOT = pipeline.ROOT
FRONTEND = pipeline.FRONTEND
ADAPTER = pipeline.ADAPTER
LAYOUT = pipeline.LAYOUT
VM = pipeline.VM
COMPILE = pipeline.StaticForBreakCPipelineTests.compile
RUN = pipeline.StaticForBreakCPipelineTests.vm
NORMALIZED = pipeline.StaticForBreakCPipelineTests.normalized
PROJECT = alias.SourceLocalAliasCPipelineTests.adapter


DEFAULT_EXPRESSION = "current = getchar(), current"


def source(*, bound: int = 3, expression: str = DEFAULT_EXPRESSION) -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int current = getchar();\n"
        "    putchar(current);\n"
        f"    for (int i = 0; i < {bound}; ++i) {{\n"
        f"        putchar(({expression}));\n"
        "        if (i % 2 == 0) {\n"
        "            putchar(current);\n"
        "            continue;\n"
        "        }\n"
        "        putchar(current);\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class CommaAssignedOutputCPipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned Clang, adapter, layout and guest VM required")

    def test_complete_loop_matches_real_binary_guest_oracle(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest_path = root / "stream.c", root / "stream.malbolge"
            _ = path.write_text(source(), encoding="utf-8")
            compiled = COMPILE(path, guest_path)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            samples = (
                bytes((0, 255, 128, 1, 42)),
                bytes((255, 0, 1, 128, 0)),
                *(hashlib.shake_256(bytes((i,))).digest(5) for i in range(16)),
            )
            for data in samples:
                with self.subTest(data=data):
                    actual = RUN(guest_path, data)
                    self.assertEqual(actual.returncode, 0, actual.stderr)
                    self.assertEqual(
                        actual.stdout,
                        bytes(
                            (
                                data[0],
                                data[1],
                                data[1],
                                data[2],
                                data[2],
                                data[3],
                                data[3],
                                data[4],
                            )
                        ),
                    )
                    self.assertEqual(actual.stderr, b"malbolge-steps-v1:14\n")

    def test_zero_trip_skips_assignment_and_read(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest_path = root / "zero.c", root / "zero.malbolge"
            _ = path.write_text(source(bound=0), encoding="utf-8")
            compiled = COMPILE(path, guest_path)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (bytes((0, 255)), bytes((255, 0))):
                actual = RUN(guest_path, data)
                self.assertEqual(actual.returncode, 0, actual.stderr)
                self.assertEqual(actual.stdout, data)
                self.assertEqual(actual.stderr, b"malbolge-steps-v1:5\n")

    def test_selected_and_skipped_branch_preserves_local_identity(self) -> None:
        template = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    int current = getchar();\n"
            "    if ({predicate}) {\n"
            "        putchar((current = getchar(), current));\n"
            "    }\n"
            "    putchar(current);\n"
            "    putchar(getchar());\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for selected in (False, True):
                with self.subTest(selected=selected):
                    path = root / f"branch-{int(selected)}.c"
                    target = root / f"branch-{int(selected)}.malbolge"
                    _ = path.write_text(
                        template.replace("{predicate}", str(int(selected))),
                        encoding="utf-8",
                    )
                    compiled = COMPILE(path, target)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    for data in (
                        bytes((0, 255, 128)),
                        bytes((255, 0, 1)),
                    ):
                        guest = RUN(target, data)
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        if selected:
                            self.assertEqual(
                                guest.stdout, bytes((data[1], data[1], data[2]))
                            )
                            step_report = b"malbolge-steps-v1:7\n"
                            self.assertEqual(guest.stderr, step_report)
                        else:
                            expected = bytes((data[0], data[1]))
                            self.assertEqual(guest.stdout, expected)
                            step_report = b"malbolge-steps-v1:5\n"
                            self.assertEqual(guest.stderr, step_report)

    def test_stale_top_level_rebind_refuses_old_alias(self) -> None:
        template = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    int current = getchar();\n"
            "    int previous = current;\n"
            "    getchar();\n"
            "    putchar((current = getchar(), current));\n"
            "    putchar(current);\n"
            "    {consumer}\n"
            "    putchar(getchar());\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "rebound.c"
            target = root / "rebound.malbolge"
            stream = template.replace("{consumer}", "")
            _ = path.write_text(stream, encoding="utf-8")
            result = COMPILE(path, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            for data in (bytes((0, 255, 128, 42)), bytes((255, 0, 1, 2))):
                guest = RUN(target, data)
                self.assertEqual(guest.returncode, 0, guest.stderr)
                expected = bytes((data[2], data[2], data[3]))
                self.assertEqual(guest.stdout, expected)
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:8\n")
            invalid = root / "stale.c"
            invalid_target = root / "stale.malbolge"
            _ = invalid.write_text(
                template.replace("{consumer}", "putchar(previous);"),
                encoding="utf-8",
            )
            rejected = COMPILE(invalid, invalid_target)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertFalse(invalid_target.exists())

    def test_unimplemented_or_stale_values_refuse(self) -> None:
        invalid = (
            "current == getchar(), current",
            "current = getchar(), current + 1",
            "current = getchar(), getchar()",
            "current = getchar(), putchar(current)",
            "current = getchar(), current = getchar()",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, expression in enumerate(invalid):
                with self.subTest(expression=expression):
                    path, guest_path = (
                        root / f"bad-{index}.c",
                        root / f"bad-{index}.malbolge",
                    )
                    invalid_source = source(expression=expression)
                    _ = path.write_text(invalid_source, encoding="utf-8")
                    result = COMPILE(path, guest_path)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(guest_path.exists())

    def test_clang_mutations_and_sha_adjusted_source_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "stream.c"
            _ = path.write_text(source(), encoding="utf-8")
            normalized = NORMALIZED(path)
            missing = root / "missing.malbolge"
            rejected = PROJECT(normalized, missing, None)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertFalse(missing.exists())
            nodes = cast(list[dict[str, object]], normalized["nodes"])
            selected: list[dict[str, object]] = []
            for node in nodes:
                node_span = cast(dict[str, dict[str, int]], node["span"])
                if node_span["begin"]["line"] == 6:
                    selected.append(node)
            for index, node in enumerate(selected):
                with self.subTest(index=index):
                    forged = copy.deepcopy(normalized)
                    changed = cast(list[dict[str, object]], forged["nodes"])
                    changed[cast(int, node["id"]) - 1]["parent"] = 2
                    guest_path = root / f"forged-{index}.malbolge"
                    result = PROJECT(forged, guest_path, path)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(guest_path.exists())
            altered = source().replace(
                "current = getchar(), current",
                "current = getchar() + current",
            )
            path2 = root / "altered.c"
            _ = path2.write_text(altered, encoding="utf-8")
            forged = copy.deepcopy(normalized)
            digest = hashlib.sha256(altered.encode()).hexdigest()
            cast(dict[str, object], forged["source"])["sha256"] = digest
            target = root / "spoof.malbolge"
            result = PROJECT(forged, target, path2)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    _ = unittest.main()
