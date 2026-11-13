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
#   - Source-proven parenthesized and negated C induction branch parity.
# - Must-Not:
#   - Host-evaluate guest bytes or admit effects in source-time predicates.
# - Allows:
#   - Inputs: pinned Clang C, binary stdin, forged normalized ASTs.
#   - Outputs: normative guest VM parity, fail-closed diagnostics.
#   - Side effects: temporary source and guest artifacts.
# - Split-When:
#   - Dynamic guest control-flow consumes these Boolean expressions.
# - Merge-When:
#   - Static C induction expression proof shares one bounded contract.
# - Summary:
#   - Negated and grouped induction conditions preserve live guest I/O.

"""Whole-C grouped and negated induction conditions select guest I/O."""

from __future__ import annotations

import copy
import json
import random
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests import test_induction_static_for_c_pipeline as helpers
from tests.test_compound_induction_for_c_pipeline import program

ADAPTER = helpers.ADAPTER
FRONTEND = helpers.FRONTEND
LAYOUT = helpers.LAYOUT
ROOT = helpers.ROOT
VM = helpers.VM


class NegatedInductionForCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler and guest VM are required")

    @staticmethod
    def compile(path: Path, target: Path) -> subprocess.CompletedProcess[bytes]:
        return helpers.InductionStaticForCPipelineTests.compile(path, target)

    @staticmethod
    def vm(path: Path, data: bytes) -> subprocess.CompletedProcess[bytes]:
        return helpers.InductionStaticForCPipelineTests.vm(path, data)

    @staticmethod
    def normalized(path: Path) -> dict[str, object]:
        return helpers.InductionStaticForCPipelineTests.normalized(path)

    def test_whole_negated_grouped_program_runs_guest(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "whole.c"
            target = root / "whole.malbolge"
            source.write_text(
                program("!(i == 1 || (i >= 3 && i < 4))"),
                encoding="utf-8",
            )
            result = self.compile(source, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            for data in (
                bytes((0, 255, 128, 1, 42, 9, 27)),
                bytes((92, 18, 45, 202, 213, 77, 19)),
            ):
                expected = bytes(
                    (data[0], data[0], data[1], data[2], data[3], data[3], data[5])
                )
                guest = self.vm(target, data)
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(guest.stdout, expected)
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:14\n")

    def test_seeded_grouping_matrix_matches_guest_oracle(self) -> None:
        cases = (
            ("double", "!!(i < 3)", 4, lambda i: i < 3),
            (
                "grouped",
                "(i == 1 || (i >= 2 && i != 3))",
                4,
                lambda i: i == 1 or (i >= 2 and i != 3),
            ),
            ("not-and", "!(i == 0) && (i < 3)", 5, lambda i: i != 0 and i < 3),
            ("short", "!(i == 0 || (i < 2))", 2, lambda i: not (i == 0 or i < 2)),
        )
        rng = random.Random(0xB001E)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for label, expression, bound, selected in cases:
                with self.subTest(label=label):
                    source = root / f"{label}.c"
                    target = root / f"{label}.malbolge"
                    source.write_text(program(expression, bound), encoding="utf-8")
                    compiled = self.compile(source, target)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    for data in (
                        bytes((0, 255, 128, 1, 42, 9, 27, 45, 103)),
                        bytes(rng.randrange(256) for _ in range(16)),
                    ):
                        cursor = 0
                        output = bytearray()
                        for i in range(bound):
                            current = data[cursor]
                            cursor += 1
                            if selected(i):
                                output.extend((current, current))
                                continue
                            if i == 3:
                                break
                            output.append(current)
                            output.append(data[cursor])
                            cursor += 1
                        output.append(data[cursor])
                        cursor += 1
                        guest = self.vm(target, data)
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        self.assertEqual(guest.stdout, bytes(output))
                        self.assertEqual(
                            guest.stderr,
                            f"malbolge-steps-v1:{cursor + len(output) + 1}\n".encode(),
                        )

    def test_dynamic_or_effectful_predicates_refuse_artifact(self) -> None:
        source = program("!(i == 1 || (i >= 3 && i < 4))")
        variants = (
            source.replace("i == 1", "current == 1"),
            source.replace("i == 1", "getchar() == 1"),
            source.replace("i == 1", "i++ == 1"),
            source.replace("i == 1", "i = 1"),
            source.replace("i == 1", "i + 1 == 2"),
            source.replace("i == 1", "getchar() || i == 1"),
            source.replace("++i)", "i += 2)"),
            program("!(i == 1 || (i >= 3 && i < 4))", bound=17),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, variant in enumerate(variants):
                with self.subTest(index=index):
                    path = root / f"negative-{index}.c"
                    target = root / f"negative-{index}.malbolge"
                    path.write_text(variant, encoding="utf-8")
                    self.assertNotEqual(self.compile(path, target).returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_grouping_and_negation_nodes_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "whole.c"
            path.write_text(
                program("!(i == 1 || (i >= 3 && i < 4))"),
                encoding="utf-8",
            )
            normalized = self.normalized(path)
            nodes = normalized["nodes"]
            unary = next(n for n in nodes if n.get("operation") == "!")
            outer = next(n for n in nodes if n["parent"] == unary["id"])
            logical = next(n for n in nodes if n["parent"] == outer["id"])
            inner = next(
                n
                for n in nodes
                if n["parent"] == logical["id"]
                and n["kind"] == "parenthesized-expression"
            )
            comparison = next(
                n
                for n in nodes
                if n["parent"] == logical["id"] and n["kind"] == "binary-expression"
            )
            cast = next(n for n in nodes if n["parent"] == comparison["id"])
            variable = next(n for n in nodes if n["parent"] == cast["id"])
            mutations = (
                (unary["id"], "operation", "~"),
                (unary["id"], "type", "u32"),
                (unary["id"], "parent", 2),
                (unary["id"], "span.end.byte", 1),
                (unary["id"], "constant_integer", "1"),
                (outer["id"], "operation", "!"),
                (outer["id"], "span.begin.column", 1),
                (logical["id"], "parent", 2),
                (inner["id"], "operation", "!"),
                (inner["id"], "span.end.byte", 1),
                (variable["id"], "reference", "i@999999"),
                (cast["id"], "operation", "integral-cast"),
            )
            for index, (node_id, field, value) in enumerate(mutations):
                with self.subTest(index=index):
                    forged = copy.deepcopy(normalized)
                    node = next(n for n in forged["nodes"] if n["id"] == node_id)
                    leaf = node
                    parts = field.split(".")
                    for key in parts[:-1]:
                        leaf = leaf[key]
                    leaf[parts[-1]] = value
                    target = root / f"forged-{index}.malbolge"
                    result = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(target),
                            "--capsule",
                        ],
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
