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
#   - Source-proven compositions of successful guest byte identities.
# - Must-Not:
#   - Fold guest input or admit hidden effects or nonidentity expressions.
# - Allows:
#   - Inputs: pinned C source and normalized Clang expression ancestry.
#   - Outputs: normative guest byte/step parity or refusal.
#   - Side effects: isolated compiler artifacts only.
# - Split-When:
#   - General typed guest arithmetic expression lowering replaces this proof.
# - Merge-When:
#   - Byte identity expression lowering becomes an independent module.
# - Summary:
#   - Composed exact identities preserve resident guest data at runtime.

"""Whole-C and VM proof for composed byte-preserving C expressions."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from typing import cast, override

from tests import test_guest_byte_identity_arithmetic_c_pipeline as previous

ROOT = previous.ROOT
FRONTEND = previous.FRONTEND
ADAPTER = previous.ADAPTER
LAYOUT = previous.LAYOUT
VM = previous.VM
COMPILE = previous.COMPILE
RUN = previous.RUN
NORMALIZED = previous.NORMALIZED
PROJECT = previous.PROJECT


def source(*, expression: str = "(current + 0) ^ 0", bound: int = 3) -> str:
    return previous.source(expression=expression, bound=bound)


class GuestByteComposedIdentityCPipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if not all(tool.is_file() for tool in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler and normative guest VM required")

    def test_complete_program_preserves_input_through_composed_ops(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest = root / "compound.c", root / "compound.malbolge"
            path.write_text(source(), encoding="utf-8")
            compiled = COMPILE(path, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255)),
                bytes((255, 0)),
                *(hashlib.shake_256(bytes((109, i))).digest(2) for i in range(12)),
            ):
                with self.subTest(data=data):
                    actual = RUN(guest, data)
                    self.assertEqual(actual.returncode, 0, actual.stderr)
                    self.assertEqual(actual.stdout, bytes((data[0],) * 4 + (data[1],)))
                    self.assertEqual(actual.stderr, b"malbolge-steps-v1:8\n")

    def test_multiple_depths_and_identity_families_in_guest(self) -> None:
        expressions = (
            "((current & 255) + 0) % 256",
            "current ^ 0 | 0",
            "(((current * 1) >> 0) - 0) / 1",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, expression in enumerate(expressions):
                with self.subTest(expression=expression):
                    path, guest = (
                        root / f"compound-{index}.c",
                        root / f"compound-{index}.malbolge",
                    )
                    path.write_text(source(expression=expression), encoding="utf-8")
                    compiled = COMPILE(path, guest)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    data = bytes((0, 255)) if index % 2 else bytes((255, 0))
                    actual = RUN(guest, data)
                    self.assertEqual(actual.returncode, 0, actual.stderr)
                    self.assertEqual(actual.stdout, bytes((data[0],) * 4 + (data[1],)))
                    self.assertEqual(actual.stderr, b"malbolge-steps-v1:8\n")

    def test_zero_trip_avoids_composed_effect(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest = root / "zero.c", root / "zero.malbolge"
            path.write_text(source(bound=0), encoding="utf-8")
            compiled = COMPILE(path, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            data = bytes((0, 255))
            actual = RUN(guest, data)
            self.assertEqual(actual.returncode, 0, actual.stderr)
            self.assertEqual(actual.stdout, data)
            self.assertEqual(actual.stderr, b"malbolge-steps-v1:5\n")

    def test_nonidentities_and_hidden_effects_refuse(self) -> None:
        expressions = (
            "(current + 1) ^ 0",
            "(current + 0) ^ 1",
            "(current & 254) % 256",
            "(current + getchar()) ^ 0",
            "(current + 0) || 1",
            "(current / 0) ^ 0",
            "(current + 0) * 2",
            "(getchar() + 0) ^ 0",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, expression in enumerate(expressions):
                with self.subTest(expression=expression):
                    path, guest = (
                        root / f"bad-{index}.c",
                        root / f"bad-{index}.malbolge",
                    )
                    path.write_text(source(expression=expression), encoding="utf-8")
                    rejected = COMPILE(path, guest)
                    self.assertNotEqual(rejected.returncode, 0)
                    self.assertFalse(guest.exists())

    def test_forged_ast_and_source_witnesses_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "verified.c"
            path.write_text(source(), encoding="utf-8")
            original = NORMALIZED(path)
            nodes = cast(list[dict[str, object]], original["nodes"])
            for index, node in enumerate(nodes):
                node_span = cast(dict[str, dict[str, int]], node["span"])
                if node_span["begin"]["line"] != 6:
                    continue
                for field in ("parent", "span"):
                    with self.subTest(node=node["id"], field=field):
                        forged = copy.deepcopy(original)
                        changed = cast(list[dict[str, object]], forged["nodes"])
                        if field == "parent":
                            changed[index]["parent"] = 2
                        else:
                            extent = cast(
                                dict[str, dict[str, int]], changed[index]["span"]
                            )
                            extent["begin"]["column"] += 1
                        guest = root / f"forged-{field}-{index}.malbolge"
                        rejected = PROJECT(forged, guest, path)
                        self.assertNotEqual(rejected.returncode, 0)
                        self.assertFalse(guest.exists())
            for index, (old, new) in enumerate(
                (
                    ("current + 0", "current + 1"),
                    ("current + 0", "currenz + 0"),
                    ("^ 0", "^ 1"),
                )
            ):
                witness = root / f"altered-{index}.c"
                witness.write_text(source().replace(old, new), encoding="utf-8")
                forged = copy.deepcopy(original)
                cast(dict[str, object], forged["source"])["sha256"] = hashlib.sha256(
                    witness.read_bytes()
                ).hexdigest()
                guest = root / f"spoof-{index}.malbolge"
                rejected = PROJECT(forged, guest, witness)
                self.assertNotEqual(rejected.returncode, 0)
                self.assertFalse(guest.exists())
            guest = root / "missing.malbolge"
            rejected = PROJECT(original, guest, None)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertFalse(guest.exists())


if __name__ == "__main__":
    unittest.main()
