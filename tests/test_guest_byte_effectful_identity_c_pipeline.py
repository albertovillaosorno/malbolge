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
#   - Source-proven identity compositions over effectful guest C byte calls.
# - Must-Not:
#   - Fold guest input, skip nested output, or admit nonidentity arithmetic.
# - Allows:
#   - Inputs: pinned Clang source/AST and binary VM input streams.
#   - Outputs: independent normative guest VM parity and fail-closed refusal.
#   - Side effects: isolated temporary compiler artifacts only.
# - Split-When:
#   - General dynamic C expression lowering replaces the source proof.
# - Merge-When:
#   - Effectful byte expression proofs have a common typed value model.
# - Summary:
#   - C identities retain values from genuine guest input/output effects.
# - Description:
#   - Executes compound C through guest VM and rejects forged source.
# - Usage:
#   - Run tests.test_guest_byte_effectful_identity_c_pipeline.
# - Defaults:
#   - No production I/O or shared guest state.

"""Real guest input/output under composed source-C identity expressions."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from typing import cast, override

from tests import test_guest_byte_composed_identity_c_pipeline as previous

ROOT = previous.ROOT
FRONTEND = previous.FRONTEND
ADAPTER = previous.ADAPTER
LAYOUT = previous.LAYOUT
VM = previous.VM
COMPILE = previous.COMPILE
RUN = previous.RUN
NORMALIZED = previous.NORMALIZED
PROJECT = previous.PROJECT
SpanCoordinates = dict[str, dict[str, int]]


def source(
    *,
    expression: str = "(putchar(getchar()) + 0) ^ 0",
    bound: int = 3,
) -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int current = getchar();\n"
        f"    for (int i = 0; i < {bound}; ++i) {{\n"
        "        if (i % 2 == 0) {\n"
        "            putchar(current);\n"
        "            continue;\n"
        "        }\n"
        "        putchar(current);\n"
        "    }\n"
        f"    putchar({expression});\n"
        "}\n"
    )


class GuestByteEffectfulIdentityCPipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned frontend, adapter and normative VM required")

    def test_complete_loop_and_branch_preserve_nested_call_effect(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program, guest = root / "effectful.c", root / "effectful.malbolge"
            _ = program.write_text(source(), encoding="utf-8")
            compiled = COMPILE(program, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            seeds = (bytes((113, i)) for i in range(12))
            seeded = (hashlib.shake_256(seed).digest(2) for seed in seeds)
            for data in (bytes((0, 255)), bytes((255, 0)), *seeded):
                with self.subTest(data=data):
                    actual = RUN(guest, data)
                    self.assertEqual(actual.returncode, 0, actual.stderr)
                    self.assertEqual(
                        actual.stdout, bytes((data[0],) * 3 + (data[1],) * 2)
                    )
                    self.assertEqual(actual.stderr, b"malbolge-steps-v1:8\n")

    def test_direct_input_and_nested_outputs_preserve_guest_order(self) -> None:
        variants = (
            ("((getchar() & 255) + 0) % 256", 1, 7),
            ("((putchar(putchar(getchar())) & 255) + 0) % 256", 3, 9),
            ("(((putchar(getchar()) * 1) >> 0) - 0) / 1", 2, 8),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, (expression, count, steps) in enumerate(variants):
                with self.subTest(expression=expression):
                    program = root / f"variant-{index}.c"
                    guest = root / f"variant-{index}.malbolge"
                    _ = program.write_text(
                        source(expression=expression), encoding="utf-8"
                    )
                    compiled = COMPILE(program, guest)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    for data in (bytes((0, 255)), bytes((255, 0))):
                        actual = RUN(guest, data)
                        self.assertEqual(actual.returncode, 0, actual.stderr)
                        self.assertEqual(
                            actual.stdout,
                            bytes((data[0],) * 3 + (data[1],) * count),
                        )
                        self.assertEqual(
                            actual.stderr,
                            f"malbolge-steps-v1:{steps}\n".encode(),
                        )

    def test_zero_trip_loop_does_not_synthesize_first_output(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program, guest = root / "zero.c", root / "zero.malbolge"
            _ = program.write_text(source(bound=0), encoding="utf-8")
            compiled = COMPILE(program, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (bytes((0, 255)), bytes((255, 0))):
                actual = RUN(guest, data)
                self.assertEqual(actual.returncode, 0, actual.stderr)
                self.assertEqual(actual.stdout, bytes((data[1],) * 2))
                self.assertEqual(actual.stderr, b"malbolge-steps-v1:5\n")

    def test_nonidentity_arithmetic_and_hidden_effects_refuse(self) -> None:
        expressions = (
            "(putchar(getchar()) + 1) ^ 0",
            "(putchar(getchar()) + 0) ^ 1",
            "(getchar() + 0) * 2",
            "putchar(getchar()) + getchar()",
            "(putchar(getchar()) && 1) ^ 0",
            "((putchar(getchar()) + 0) / 0)",
            "(putchar(getchar()) - 0) + current",
            "(current + getchar()) ^ 0",
            "(putchar(getchar()) & 254) % 256",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, expression in enumerate(expressions):
                with self.subTest(expression=expression):
                    program = root / f"refuse-{index}.c"
                    guest = root / f"refuse-{index}.malbolge"
                    _ = program.write_text(
                        source(expression=expression), encoding="utf-8"
                    )
                    rejected = COMPILE(program, guest)
                    self.assertNotEqual(rejected.returncode, 0)
                    self.assertFalse(guest.exists())

    def test_forged_ast_and_source_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "verified.c"
            _ = program.write_text(source(), encoding="utf-8")
            original = NORMALIZED(program)
            nodes = cast(list[dict[str, object]], original["nodes"])
            for index, node in enumerate(nodes):
                begin = cast(dict[str, dict[str, int]], node["span"])["begin"]
                if begin["line"] != 11:
                    continue
                for field in ("parent", "span"):
                    with self.subTest(node=node["id"], field=field):
                        forged = copy.deepcopy(original)
                        changed = cast(list[dict[str, object]], forged["nodes"])
                        if field == "parent":
                            changed[index]["parent"] = (
                                1 if changed[index]["parent"] == 2 else 2
                            )
                        else:
                            candidate_span = changed[index]["span"]
                            span = cast(SpanCoordinates, candidate_span)
                            span["begin"]["column"] += 1
                        guest = root / f"forge-{field}-{index}.malbolge"
                        rejected = PROJECT(forged, guest, program)
                        self.assertNotEqual(rejected.returncode, 0)
                        self.assertFalse(guest.exists())
            for index, (old, new) in enumerate(
                (
                    ("+ 0", "+ 1"),
                    ("^ 0", "^ 1"),
                    ("putchar(getchar())", "putchar(getchax())"),
                )
            ):
                witness = root / f"altered-{index}.c"
                altered = source().replace(old, new)
                _ = witness.write_text(altered, encoding="utf-8")
                forged = copy.deepcopy(original)
                digest = hashlib.sha256(witness.read_bytes()).hexdigest()
                source_object = cast(dict[str, object], forged["source"])
                source_object["sha256"] = digest
                guest = root / f"source-forge-{index}.malbolge"
                rejected = PROJECT(forged, guest, witness)
                self.assertNotEqual(rejected.returncode, 0)
                self.assertFalse(guest.exists())
            guest = root / "missing.malbolge"
            rejected = PROJECT(original, guest, None)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertFalse(guest.exists())


if __name__ == "__main__":
    _ = unittest.main()
