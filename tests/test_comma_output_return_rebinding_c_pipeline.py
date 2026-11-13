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
#   - Source-proven comma assignments from successful output returns.
# - Must-Not:
#   - Erase ordered guest writes or fabricate stale C byte identities.
# - Allows:
#   - Inputs: C, pinned normalized Clang and binary guest input.
#   - Outputs: normative guest parity or fail-closed refusal.
#   - Side effects: temporary local files only.
# - Split-When:
#   - A general guest C expression lowering supersedes bounded proofs.
# - Merge-When:
#   - Comma assignment and output return use general typed guest SSA.
# - Summary:
#   - Guest output returns can rebind a local inside ordered comma effects.
# - Description:
#   - Complete C branch/loop source and real Malbolge VM validation.
# - Usage:
#   - Run test_comma_output_return_rebinding_c_pipeline.
# - Defaults:
#   - No production stdout, filesystem or network side effects.

"""End-to-end successful byte-return assignments within C comma operands."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from typing import cast, override

from tests import test_comma_rebound_chain_c_pipeline as previous

ROOT = previous.ROOT
FRONTEND = previous.FRONTEND
ADAPTER = previous.ADAPTER
LAYOUT = previous.LAYOUT
VM = previous.VM
COMPILE = previous.COMPILE
RUN = previous.RUN
NORMALIZED = previous.NORMALIZED
PROJECT = previous.PROJECT


def source(*, bound: int = 3, depth: int = 1, final_assignment: bool = False) -> str:
    assigned = "putchar(" * depth + "getchar()" + ")" * depth
    expression = "current = getchar(), current = " + assigned
    if not final_assignment:
        expression += ", current"
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int current = getchar();\n"
        f"    for (int i = 0; i < {bound}; ++i) {{\n"
        "        if (i % 2 == 0) {\n"
        f"            putchar(({expression}));\n"
        "            continue;\n"
        "        }\n"
        "        putchar(current);\n"
        "    }\n"
        "    putchar(current);\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class CommaOutputReturnRebindingCPipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C pipeline and normative guest VM required")

    def test_complete_loop_rebinds_successful_output_return(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "full.c"
            guest_path = root / "full.malbolge"
            path.write_text(source(), encoding="utf-8")
            compiled = COMPILE(path, guest_path)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            samples = (
                bytes((0, 255, 128, 1, 42, 0)),
                bytes((255, 0, 1, 128, 0, 255)),
                *(hashlib.shake_256(bytes((49, i))).digest(6) for i in range(12)),
            )
            for data in samples:
                with self.subTest(data=data):
                    guest = RUN(guest_path, data)
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(
                        guest.stdout,
                        bytes(
                            (
                                data[2],
                                data[2],
                                data[2],
                                data[4],
                                data[4],
                                data[4],
                                data[5],
                            )
                        ),
                    )
                    self.assertEqual(guest.stderr, b"malbolge-steps-v1:14\n")

    def test_nested_successful_returns_preserve_each_guest_write(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest_path = root / "nested.c", root / "nested.malbolge"
            path.write_text(source(depth=2), encoding="utf-8")
            compiled = COMPILE(path, guest_path)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            samples = (
                bytes((0, 255, 128, 1, 42, 0)),
                bytes((255, 0, 1, 128, 0, 255)),
                *(hashlib.shake_256(bytes((50, i))).digest(6) for i in range(8)),
            )
            for data in samples:
                with self.subTest(data=data):
                    guest = RUN(guest_path, data)
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(
                        guest.stdout,
                        bytes(
                            (
                                data[2],
                                data[2],
                                data[2],
                                data[2],
                                data[4],
                                data[4],
                                data[4],
                                data[4],
                                data[5],
                            )
                        ),
                    )
                    self.assertEqual(guest.stderr, b"malbolge-steps-v1:16\n")

    def test_final_comma_operand_can_assign_successful_return(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest_path = root / "last.c", root / "last.malbolge"
            path.write_text(source(final_assignment=True), encoding="utf-8")
            compiled = COMPILE(path, guest_path)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255, 128, 1, 42, 0)),
                bytes((255, 0, 1, 128, 0, 255)),
            ):
                with self.subTest(data=data):
                    guest = RUN(guest_path, data)
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(
                        guest.stdout,
                        bytes(
                            (
                                data[2],
                                data[2],
                                data[2],
                                data[4],
                                data[4],
                                data[4],
                                data[5],
                            )
                        ),
                    )
                    self.assertEqual(guest.stderr, b"malbolge-steps-v1:14\n")

    def test_zero_trip_skips_all_comma_effects(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest_path = root / "zero.c", root / "zero.malbolge"
            path.write_text(source(bound=0), encoding="utf-8")
            compiled = COMPILE(path, guest_path)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (bytes((0, 255)), bytes((255, 0))):
                guest = RUN(guest_path, data)
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(guest.stdout, data)
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:5\n")

    def test_unsupported_comma_assignments_refuse(self) -> None:
        base = source()
        original = "current = putchar(getchar())"
        invalid = (
            "current + putchar(getchar())",
            "current = putchar(getchar() + 1)",
            "current = putchar(getchar()) + 1",
            "current = putchar(current)",
            "current = (putchar(getchar()))",
            "current == putchar(getchar())",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, expression in enumerate(invalid):
                with self.subTest(expression=expression):
                    path = root / f"invalid-{index}.c"
                    guest = root / f"invalid-{index}.malbolge"
                    path.write_text(
                        base.replace(original, expression), encoding="utf-8"
                    )
                    result = COMPILE(path, guest)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(guest.exists())

    def test_clang_ancestry_and_span_forgeries_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "legitimate.c"
            path.write_text(source(), encoding="utf-8")
            normalized = NORMALIZED(path)
            nodes = cast(list[dict[str, object]], normalized["nodes"])
            for index, node in enumerate(nodes):
                extent = cast(dict[str, dict[str, int]], node["span"])
                if extent["begin"]["line"] != 6:
                    continue
                with self.subTest(node=node["id"]):
                    forged = copy.deepcopy(normalized)
                    changed = cast(list[dict[str, object]], forged["nodes"])
                    changed[index]["parent"] = 2
                    guest = root / f"parent-{index}.malbolge"
                    refused = PROJECT(forged, guest, path)
                    self.assertNotEqual(refused.returncode, 0)
                    self.assertFalse(guest.exists())
                with self.subTest(span=node["id"]):
                    forged = copy.deepcopy(normalized)
                    changed = cast(list[dict[str, object]], forged["nodes"])
                    altered = cast(dict[str, dict[str, int]], changed[index]["span"])
                    altered["begin"]["column"] += 1
                    guest = root / f"span-{index}.malbolge"
                    refused = PROJECT(forged, guest, path)
                    self.assertNotEqual(refused.returncode, 0)
                    self.assertFalse(guest.exists())

    def test_source_evidence_and_sha_adjusted_spoofs_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "legitimate.c"
            path.write_text(source(), encoding="utf-8")
            normalized = NORMALIZED(path)
            missing = root / "no-source.malbolge"
            refused = PROJECT(normalized, missing, None)
            self.assertNotEqual(refused.returncode, 0)
            self.assertFalse(missing.exists())
            original = "current = putchar(getchar())"
            for index, expression in enumerate(
                ("current + putchar(getchar())", "currenz = putchar(getchar())")
            ):
                with self.subTest(expression=expression):
                    alternate = root / f"spoof-{index}.c"
                    alternate.write_text(
                        source().replace(original, expression),
                        encoding="utf-8",
                    )
                    forged = copy.deepcopy(normalized)
                    cast(dict[str, object], forged["source"])["sha256"] = (
                        hashlib.sha256(alternate.read_bytes()).hexdigest()
                    )
                    guest = root / f"spoof-{index}.malbolge"
                    refused = PROJECT(forged, guest, alternate)
                    self.assertNotEqual(refused.returncode, 0)
                    self.assertFalse(guest.exists())


if __name__ == "__main__":
    unittest.main()
