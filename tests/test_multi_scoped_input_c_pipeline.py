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
#   - Sequential scoped C input declarations in complete guest streams.
# - Must-Not:
#   - Recover stale source locals or trust forged normalized C evidence.
# - Allows:
#   - Inputs: pinned C frontend, original C source and binary guest stdin.
#   - Outputs: actual guest VM parity or explicit compiler refusal.
#   - Side effects: isolated temporary files under .temp.
# - Split-When:
#   - General C lexical storage supersedes bounded scoped input proofs.
# - Merge-When:
#   - Source-proven guest byte SSA supports arbitrary lexical blocks.
# - Summary:
#   - Multiple ordered scoped inputs overwrite the resident guest byte.

"""Verify multiple guest reads declared inside a single static C arm."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

from tests import test_source_local_alias_c_pipeline as aliases
from tests import test_static_for_break_c_pipeline as helpers
from tests.test_static_for_break_c_pipeline import ADAPTER
from tests.test_static_for_break_c_pipeline import FRONTEND
from tests.test_static_for_break_c_pipeline import LAYOUT
from tests.test_static_for_break_c_pipeline import ROOT
from tests.test_static_for_break_c_pipeline import VM


def source(
    *,
    condition: str = "1",
    middle: str = "int second = getchar();",
    second_output: str = "second",
    after: str = "putchar(getchar());",
) -> str:
    """Build one complete, source-verified C branch and loop.

    Returns:
        Canonical C source for the static-branch byte-stream experiment.

    """
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int current = getchar();\n"
        "    putchar(current);\n"
        f"    if ({condition}) {{\n"
        "        int current = getchar();\n"
        "        putchar(current);\n"
        "        int copy = current;\n"
        "        putchar(copy);\n"
        f"        {middle}\n"
        f"        putchar({second_output});\n"
        "        int third = getchar();\n"
        "        putchar(third);\n"
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


def loop_source(*, first: str = "int unused = getchar();") -> str:
    """Build a counted C loop that reads two new locals each trip.

    Returns:
        Complete source to run in the actual Malbolge VM.

    """
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    for (int i = 0; i < 3; ++i) {\n"
        f"        {first}\n"
        "        int current = getchar();\n"
        "        int copy = current;\n"
        "        if (i % 2 == 0) {\n"
        "            putchar(copy);\n"
        "            continue;\n"
        "        }\n"
        "        putchar(current);\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


SECOND_DECLARATION_LINE = 10
DECLARATION_NODE = "declaration-statement"
SELECTED_STEPS = b"malbolge-steps-v1:19\n"
SKIPPED_STEPS = b"malbolge-steps-v1:12\n"
LOOP_STEPS = b"malbolge-steps-v1:12\n"


class MultiScopedInputCPipelineTests(unittest.TestCase):
    """Check real guest parity and fail-closed original C proof."""

    def setUp(self) -> None:
        """Skip only when a pinned compiler pipeline tool is missing."""
        if not all(tool.is_file() for tool in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned Clang, compiler, layout and VM required")

    def test_three_scoped_reads_and_alias_match_binary_guest_vm(self) -> None:
        """Compare selected C streams against independent binary oracles."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest = root / "multi.c", root / "multi.malbolge"
            path.write_text(source(), encoding="utf-8")
            compiled = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            assert compiled.returncode == 0, compiled.stderr
            for data in (
                bytes((0, 255, 128, 1, 42, 13, 7, 255, 0)),
                hashlib.shake_256(b"three-source-scoped-byte-reads").digest(9),
            ):
                with self.subTest(data=data):
                    run = helpers.StaticForBreakCPipelineTests.vm(guest, data)
                    assert run.returncode == 0, run.stderr
                    expected = data[:1] + data[1:2] * 2 + data[2:6] + data[7:9]
                    assert run.stdout == expected
                    assert run.stderr == SELECTED_STEPS

    def test_skipped_scoped_reads_leave_outer_source_local_live(self) -> None:
        """Keep the original C binding when the inner arm is skipped."""
        text = source(condition="0", after="putchar(current);")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest = root / "skip.c", root / "skip.malbolge"
            path.write_text(text, encoding="utf-8")
            compiled = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            assert compiled.returncode == 0, compiled.stderr
            for data in (
                bytes((255, 128, 0, 1, 42)),
                hashlib.shake_256(b"skipped-source-scoped-byte-reads").digest(
                    5
                ),
            ):
                with self.subTest(data=data):
                    run = helpers.StaticForBreakCPipelineTests.vm(guest, data)
                    assert run.returncode == 0, run.stderr
                    assert run.stdout == data[:1] * 3 + data[1:2] + data[3:]
                    assert run.stderr == SKIPPED_STEPS

    def test_repeated_scoped_reads_in_counted_loop_match_guest_vm(self) -> None:
        """Emit genuine fresh input for every iteration, not host replay."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest = root / "loop.c", root / "loop.malbolge"
            path.write_text(loop_source(), encoding="utf-8")
            compiled = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            assert compiled.returncode == 0, compiled.stderr
            for data in (
                bytes((0, 255, 128, 42, 1, 13, 7)),
                hashlib.shake_256(b"bounded-loop-multiple-inputs").digest(7),
            ):
                with self.subTest(data=data):
                    run = helpers.StaticForBreakCPipelineTests.vm(guest, data)
                    assert run.returncode == 0, run.stderr
                    assert run.stdout == data[1:2] + data[3:4] + data[5:7]
                    assert run.stderr == LOOP_STEPS

    def test_first_loop_local_requires_original_source_witness(self) -> None:
        """Reject AST/source mismatch without a prior accumulator local."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "real.c"
            path.write_text(loop_source(), encoding="utf-8")
            normalized = helpers.StaticForBreakCPipelineTests.normalized(path)
            mutated = root / "changed.c"
            mutated.write_text(
                loop_source(first="int unused = 123456789;"),
                encoding="utf-8",
            )
            forged = copy.deepcopy(normalized)
            forged["source"]["sha256"] = hashlib.sha256(
                mutated.read_bytes()
            ).hexdigest()
            guest = root / "forged.malbolge"
            with self.subTest(case="forged-source"):
                result = aliases.SourceLocalAliasCPipelineTests.adapter(
                    forged, guest, mutated
                )
                assert result.returncode != 0
                assert not guest.exists()
            with self.subTest(case="missing-source"):
                result = aliases.SourceLocalAliasCPipelineTests.adapter(
                    normalized, guest, None
                )
                assert result.returncode != 0
                assert not guest.exists()

    def test_stale_reads_and_unsupported_scoped_declarations_refuse(
        self,
    ) -> None:
        """Reject expressions that cannot preserve the resident guest byte."""
        cases = (
            source(second_output="current"),
            source(after="putchar(current);"),
            source(middle="int second = 5;"),
            source(middle="int second = current + 0;"),
            source(middle="int second = getchar() + 0;"),
            source(middle="int second=getchar();"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, text in enumerate(cases):
                with self.subTest(case=index):
                    path = root / f"bad-{index}.c"
                    guest = root / f"bad-{index}.malbolge"
                    path.write_text(text, encoding="utf-8")
                    compiled = helpers.StaticForBreakCPipelineTests.compile(
                        path, guest
                    )
                    assert compiled.returncode != 0
                    assert not guest.exists()

    def test_source_and_normalized_second_read_forgery_refuse(self) -> None:
        """Refuse forged Clang nodes, source bytes and missing witnesses."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "real.c"
            path.write_text(source(), encoding="utf-8")
            normalized = helpers.StaticForBreakCPipelineTests.normalized(path)
            declaration = next(
                node
                for node in normalized["nodes"]
                if node["kind"] == DECLARATION_NODE
                and node["span"]["begin"]["line"] == SECOND_DECLARATION_LINE
            )
            variants = (
                (0, "parent", 0),
                (1, "type", "u8"),
                (1, "reference", "other@0"),
                (2, "reference", "external:putchar"),
                (3, "operation", "integral-cast"),
                (4, "parent", 0),
            )
            for index, (offset, field, value) in enumerate(variants):
                with self.subTest(case=index):
                    forged = copy.deepcopy(normalized)
                    node = next(
                        node
                        for node in forged["nodes"]
                        if node["id"] == declaration["id"] + offset
                    )
                    node[field] = value
                    guest = root / f"forged-{index}.malbolge"
                    compiled = aliases.SourceLocalAliasCPipelineTests.adapter(
                        forged, guest, path
                    )
                    assert compiled.returncode != 0
                    assert not guest.exists()

    def test_original_scoped_input_source_proof_is_mandatory(self) -> None:
        """Refuse absent or inconsistent original-C source witnesses."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "real.c"
            path.write_text(source(), encoding="utf-8")
            normalized = helpers.StaticForBreakCPipelineTests.normalized(path)
            guest = root / "no-source.malbolge"
            with self.subTest(case="missing"):
                result = aliases.SourceLocalAliasCPipelineTests.adapter(
                    normalized, guest, None
                )
                assert result.returncode != 0
                assert not guest.exists()
            # SHA-adjusted normalized JSON must not turn a constant into input.
            mutated = root / "different.c"
            mutated.write_text(
                source(middle="int second = 123456789;"), encoding="utf-8"
            )
            forged = copy.deepcopy(normalized)
            forged["source"]["sha256"] = hashlib.sha256(
                mutated.read_bytes()
            ).hexdigest()
            guest = root / "source-forged.malbolge"
            with self.subTest(case="sha-forgery"):
                result = aliases.SourceLocalAliasCPipelineTests.adapter(
                    forged, guest, mutated
                )
                assert result.returncode != 0
                assert not guest.exists()


if __name__ == "__main__":
    unittest.main()
