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
#   - Successful-input unsigned-byte casts inside complete counted C streams.
# - Must-Not:
#   - Treat EOF, signed narrowing, mutable guest state or host input as safe.
# - Allows:
#   - Inputs: pinned C frontend, forged normalized nodes, binary guest stdin.
#   - Outputs: exact guest byte/step parity or fail-closed compiler refusal.
#   - Side effects: isolated temporary source and output artifacts.
# - Split-When:
#   - General guest C casts and byte arithmetic supersede the identity proof.
# - Merge-When:
#   - A typed expression verifier handles all byte-preserving conversions.
# - Summary:
#   - Byte-preserving C casts reuse actual guest input, without a new read.

"""Verify unsigned char casts over successful guest inputs, including 0xff."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests import test_static_for_break_c_pipeline as break_helpers
from tests.test_static_for_break_c_pipeline import (
    ADAPTER,
    FRONTEND,
    LAYOUT,
    ROOT,
    VM,
)


def source(operand: str = "(unsigned char)current") -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    for (int i = 0; i < 4; ++i) {\n"
        "        int current = getchar();\n"
        "        if (i % 2 == 0) {\n"
        f"            putchar({operand});\n"
        "            continue;\n"
        "        }\n"
        f"        putchar({operand});\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class UnsignedCharCastCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(tool.is_file() for tool in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler, layout and normative VM required")

    def test_compound_loop_cast_preserves_actual_binary_guest_input(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "cast.c"
            target = root / "cast.malbolge"
            path.write_text(source(), encoding="utf-8")
            result = break_helpers.StaticForBreakCPipelineTests.compile(path, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(target.is_file())
            for data in (
                bytes((0, 255, 128, 1, 42)),
                hashlib.shake_256(b"unsigned-char-guest-0000").digest(5),
            ):
                guest = subprocess.run(
                    [str(VM), str(target), "--input-stdin", "--report-steps"],
                    input=data,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(guest.stdout, data)
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:11\n")

    def test_signed_narrowing_and_effectful_operands_refuse(self) -> None:
        candidates = (
            source("(signed char)current"),
            source("(signed   char)current"),
            source("(unsigned char)(current + 1)"),
            source("(unsigned char)getchar()"),
            source("(unsigned char)(current++)"),
            source("(unsigned char)i"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, candidate in enumerate(candidates):
                with self.subTest(index=index):
                    path = root / f"invalid-{index}.c"
                    target = root / f"invalid-{index}.malbolge"
                    path.write_text(candidate, encoding="utf-8")
                    result = break_helpers.StaticForBreakCPipelineTests.compile(
                        path, target
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_cast_nodes_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "cast.c"
            path.write_text(source(), encoding="utf-8")
            normalized = break_helpers.StaticForBreakCPipelineTests.normalized(path)
            nodes = normalized["nodes"]
            cast = next(
                node
                for node in nodes
                if node["kind"] == "cast-expression" and node.get("type") == "u8"
            )
            promoted = next(node for node in nodes if node["id"] == cast["parent"])
            call = next(node for node in nodes if node["id"] == promoted["parent"])
            self.assertEqual(call["reference"], "external:putchar")
            mutations = (
                (cast["id"], "type", "i8"),
                (cast["id"], "operation", "no-op"),
                (cast["id"], "parent", 2),
                (cast["id"], "reference", "i@52"),
                (cast["id"], "name", "spoof"),
                (cast["id"], "span", {"begin": {"byte": 0}}),
            )
            for index, (node_id, field, value) in enumerate(mutations):
                with self.subTest(index=index):
                    forged = copy.deepcopy(normalized)
                    next(node for node in forged["nodes"] if node["id"] == node_id)[
                        field
                    ] = value
                    output = root / f"forged-{index}.malbolge"
                    result = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(output),
                            "--source",
                            str(path),
                            "--capsule",
                        ],
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(output.exists())

    def test_missing_source_and_coherent_signed_spoof_refuse(self) -> None:
        """Equal-width signed spelling cannot borrow forged unsigned types."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "signed.c"
            path.write_text(source("(signed   char)current"), encoding="utf-8")
            original = break_helpers.StaticForBreakCPipelineTests.normalized(path)
            forged = copy.deepcopy(original)
            cast_nodes = [
                node
                for node in forged["nodes"]
                if node["kind"] == "cast-expression" and node.get("type") == "i8"
            ]
            self.assertEqual(len(cast_nodes), 2)
            for node in cast_nodes:
                node["type"] = "u8"
            for index, witness in enumerate((None, path)):
                with self.subTest(witness=witness):
                    target = root / f"spoof-{index}.malbolge"
                    command = [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(target),
                    ]
                    if witness is not None:
                        command.extend(("--source", str(witness)))
                    command.append("--capsule")
                    result = subprocess.run(
                        command,
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(target.exists())
            unsigned_path = root / "unsigned.c"
            unsigned_path.write_text(source(), encoding="utf-8")
            unsigned_ast = break_helpers.StaticForBreakCPipelineTests.normalized(
                unsigned_path
            )
            target = root / "missing-source.malbolge"
            result = subprocess.run(
                [
                    str(ADAPTER),
                    "--layout-backend",
                    str(LAYOUT),
                    "--output",
                    str(target),
                    "--capsule",
                ],
                input=json.dumps(unsigned_ast).encode(),
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertNotEqual(result.returncode, 0, result.stderr)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
