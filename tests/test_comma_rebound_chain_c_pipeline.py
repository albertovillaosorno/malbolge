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
#   - Source-proven comma assignment followed by repeated live C byte uses.
# - Must-Not:
#   - Reconstruct a stale C local or elide successful guest effects.
# - Allows:
#   - Inputs: source C, pinned Clang nodes, binary guest stdin.
#   - Outputs: normative guest stdout or fail-closed refusal.
#   - Side effects: isolated test files.
# - Split-When:
#   - General guest C expression lowering replaces bounded byte proofs.
# - Merge-When:
#   - Comma sequencing and assignments share generic C SSA lowering.
# - Summary:
#   - A comma input assignment makes later operands read its fresh guest byte.
# - Description:
#   - Whole-C branch and loop tests with source/AST tamper checks.
# - Usage:
#   - Run test_comma_rebound_chain_c_pipeline.
# - Defaults:
#   - Fixtures live only in temporary directories.

"""Guest parity for reassignment and subsequent comma operands."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from typing import cast, override

from tests import test_comma_assigned_output_c_pipeline as previous

ROOT = previous.ROOT
FRONTEND = previous.FRONTEND
ADAPTER = previous.ADAPTER
LAYOUT = previous.LAYOUT
VM = previous.VM
COMPILE = previous.COMPILE
RUN = previous.RUN
NORMALIZED = previous.NORMALIZED
PROJECT = previous.PROJECT


def source(
    *, bound: int = 3, expression: str = "current = getchar(), current, current"
) -> str:
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


class CommaReboundChainCPipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler stages and normative VM required")

    def test_whole_loop_reuses_assigned_binary_byte(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest_path = root / "stream.c", root / "stream.malbolge"
            path.write_text(source(), encoding="utf-8")
            compiled = COMPILE(path, guest_path)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            samples = (
                bytes((0, 255, 128, 1)),
                bytes((255, 0, 1, 128)),
                *(hashlib.shake_256(bytes((35, i))).digest(4) for i in range(16)),
            )
            for data in samples:
                with self.subTest(data=data):
                    guest = RUN(guest_path, data)
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(
                        guest.stdout,
                        bytes((data[1], data[1], data[2], data[2], data[3])),
                    )
                    self.assertEqual(guest.stderr, b"malbolge-steps-v1:10\n")

    def test_effectful_middle_operand_writes_the_rebound_byte(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest_path = root / "effectful.c", root / "effectful.malbolge"
            path.write_text(
                source(expression="current = getchar(), putchar(current), current"),
                encoding="utf-8",
            )
            compiled = COMPILE(path, guest_path)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            samples = (
                bytes((0, 255, 128, 1)),
                bytes((255, 0, 1, 128)),
                *(hashlib.shake_256(bytes((36, i))).digest(4) for i in range(12)),
            )
            for data in samples:
                with self.subTest(data=data):
                    guest = RUN(guest_path, data)
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(
                        guest.stdout,
                        bytes(
                            (
                                data[1],
                                data[1],
                                data[1],
                                data[2],
                                data[2],
                                data[2],
                                data[3],
                            )
                        ),
                    )
                    self.assertEqual(guest.stderr, b"malbolge-steps-v1:12\n")

    def test_zero_trip_skips_rebinding(self) -> None:
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

    def test_unsupported_expressions_fail_closed(self) -> None:
        expressions = (
            "current == getchar(), current, current",
            "current = getchar(), current + 1, current",
            "current = getchar(), getchar(), current",
            "current = getchar(), current, previous",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, expression in enumerate(expressions):
                with self.subTest(expression=expression):
                    path = root / f"invalid-{index}.c"
                    target = root / f"invalid-{index}.malbolge"
                    text = source(expression=expression)
                    if "previous" in text:
                        text = text.replace(
                            "    int current = getchar();\n",
                            "    int current = getchar();\n    int previous = current;\n",
                        )
                    path.write_text(text, encoding="utf-8")
                    result = COMPILE(path, target)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_ast_and_sha_adjusted_original_source_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "valid.c"
            path.write_text(source(), encoding="utf-8")
            normalized = NORMALIZED(path)
            nodes = cast(list[dict[str, object]], normalized["nodes"])
            for index, node in enumerate(nodes):
                extent = cast(dict[str, dict[str, int]], node["span"])
                if extent["begin"]["line"] != 6:
                    continue
                forged = copy.deepcopy(normalized)
                changed = cast(list[dict[str, object]], forged["nodes"])
                changed[cast(int, node["id"]) - 1]["parent"] = 2
                target = root / f"tamper-{index}.malbolge"
                result = PROJECT(forged, target, path)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(target.exists())
            missing = root / "no-source.malbolge"
            rejected = PROJECT(normalized, missing, None)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertFalse(missing.exists())
            tampered = source().replace(
                "current = getchar(), current, current",
                "current = getchar() + current, current",
            )
            alternate = root / "tampered.c"
            alternate.write_text(tampered, encoding="utf-8")
            forged = copy.deepcopy(normalized)
            cast(dict[str, object], forged["source"])["sha256"] = hashlib.sha256(
                tampered.encode()
            ).hexdigest()
            target = root / "source-spoof.malbolge"
            result = PROJECT(forged, target, alternate)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(target.exists())
            # Clang-shaped local references cannot be replayed against a
            # SHA-adjusted original C file with a different same-width name.
            alternate.write_text(
                source().replace(
                    "current = getchar(), current, current",
                    "current = getchar(), prevous, current",
                ),
                encoding="utf-8",
            )
            forged = copy.deepcopy(normalized)
            cast(dict[str, object], forged["source"])["sha256"] = hashlib.sha256(
                alternate.read_bytes()
            ).hexdigest()
            other = root / "renamed-spoof.malbolge"
            result = PROJECT(forged, other, alternate)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(other.exists())
            # A SHA-adjusted `+` has the same source extent as `,` and
            # leaves every referenced C identifier unchanged.
            altered_operator = source().replace("current, current", "current+ current")
            alternate.write_text(altered_operator, encoding="utf-8")
            forged = copy.deepcopy(normalized)
            cast(dict[str, object], forged["source"])["sha256"] = hashlib.sha256(
                alternate.read_bytes()
            ).hexdigest()
            changed_operator = root / "operator-spoof.malbolge"
            result = PROJECT(forged, changed_operator, alternate)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(changed_operator.exists())


if __name__ == "__main__":
    unittest.main()
