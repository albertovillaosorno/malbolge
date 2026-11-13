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
#   - Static C induction truth-value conditions with real guest input/output.
# - Must-Not:
#   - Treat runtime guest state as a known compile-time C scalar.
# - Allows:
#   - Inputs: pinned Clang, binary guest input, forged normalized trees.
#   - Outputs: VM byte parity and explicit compiler refusal without artifacts.
#   - Side effects: isolated temporary source and target paths.
# - Split-When:
#   - Runtime guest state can control actual conditional branches.
# - Merge-When:
#   - Pure induction predicate proofs use the same source-time invariant.
# - Summary:
#   - A bounded `i` truth test chooses effects for each independent guest trip.

"""Pure C induction truth conditions retain dynamic guest byte I/O."""

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


def truth_oracle(bound: int, data: bytes) -> tuple[bytes, int]:
    output = bytearray()
    consumed = 0
    for i in range(bound):
        current = data[consumed]
        consumed += 1
        if i and i != 3:
            output.extend((current, current))
            continue
        if i == 3:
            break
        output.append(current)
        output.append(data[consumed])
        consumed += 1
    output.append(data[consumed])
    consumed += 1
    return bytes(output), consumed


class InductionTruthForCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(
            path.is_file()
            for path in (helpers.FRONTEND, helpers.ADAPTER, helpers.LAYOUT, helpers.VM)
        ):
            self.skipTest("pinned Clang, adapter, layout and VM are required")

    @staticmethod
    def compile(path: Path, target: Path) -> subprocess.CompletedProcess[bytes]:
        return helpers.InductionStaticForCPipelineTests.compile(path, target)

    @staticmethod
    def vm(path: Path, data: bytes) -> subprocess.CompletedProcess[bytes]:
        return helpers.InductionStaticForCPipelineTests.vm(path, data)

    @staticmethod
    def normalized(path: Path) -> dict[str, object]:
        return helpers.InductionStaticForCPipelineTests.normalized(path)

    def test_whole_induction_truth_program_runs_guest(self) -> None:
        with tempfile.TemporaryDirectory(dir=helpers.ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "truth.c"
            target = root / "truth.malbolge"
            source.write_text(program("i && !(i == 3)"), encoding="utf-8")
            compiled = self.compile(source, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255, 128, 1, 42, 9, 27)),
                bytes((201, 45, 254, 0, 137, 26, 44)),
            ):
                expected, consumed = truth_oracle(4, data)
                guest = self.vm(target, data)
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(guest.stdout, expected)
                self.assertEqual(
                    guest.stderr,
                    f"malbolge-steps-v1:{consumed + len(expected) + 1}\n".encode(),
                )

    def test_seeded_direct_negated_and_combined_truth(self) -> None:
        cases = (
            ("direct", "i", 2, lambda i: bool(i)),
            ("negated", "!i", 4, lambda i: not i),
            ("combined", "i && i < 3", 4, lambda i: 0 < i < 3),
        )
        rng = random.Random(0xCA5C4DE)
        with tempfile.TemporaryDirectory(dir=helpers.ROOT / ".temp") as directory:
            root = Path(directory)
            for label, expression, bound, predicate in cases:
                with self.subTest(label=label):
                    source = root / f"{label}.c"
                    target = root / f"{label}.malbolge"
                    source.write_text(program(expression, bound), encoding="utf-8")
                    compiled = self.compile(source, target)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    for data in (
                        bytes((0, 255, 128, 1, 42, 9, 27, 53, 160)),
                        bytes(rng.randrange(256) for _ in range(12)),
                    ):
                        output = bytearray()
                        cursor = 0
                        for i in range(bound):
                            current = data[cursor]
                            cursor += 1
                            if predicate(i):
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

    def test_guest_input_truth_and_induction_mutations_refuse(self) -> None:
        source = program("i && !(i == 3)")
        invalid = (
            source.replace("i &&", "current &&"),
            source.replace("i &&", "getchar() &&"),
            source.replace("i &&", "i++ &&"),
            source.replace("i &&", "i = 1 &&"),
            source.replace("i &&", "i + 1 &&"),
            source.replace("i &&", "putchar(1) &&"),
            source.replace("++i)", "i += 2)"),
            program("i && !(i == 3)", bound=17),
        )
        with tempfile.TemporaryDirectory(dir=helpers.ROOT / ".temp") as directory:
            root = Path(directory)
            for index, text in enumerate(invalid):
                with self.subTest(index=index):
                    path = root / f"invalid-{index}.c"
                    target = root / f"invalid-{index}.malbolge"
                    path.write_text(text, encoding="utf-8")
                    self.assertNotEqual(self.compile(path, target).returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_scalar_read_metadata_refuses(self) -> None:
        with tempfile.TemporaryDirectory(dir=helpers.ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "truth.c"
            source.write_text(program("i && !(i == 3)"), encoding="utf-8")
            normalized = self.normalized(source)
            nodes = normalized["nodes"]
            logical = next(n for n in nodes if n.get("operation") == "&&")
            scalar = next(n for n in nodes if n["parent"] == logical["id"])
            variable = next(n for n in nodes if n["parent"] == scalar["id"])
            mutations = (
                (scalar["id"], "operation", "integral-cast"),
                (scalar["id"], "type", "u32"),
                (scalar["id"], "parent", 2),
                (scalar["id"], "span.end.byte", 0),
                (scalar["id"], "constant_integer", "1"),
                (variable["id"], "reference", "current@85"),
                (variable["id"], "parent", 2),
                (variable["id"], "span.begin.column", 0),
            )
            for index, (node_id, field, value) in enumerate(mutations):
                with self.subTest(index=index):
                    forged = copy.deepcopy(normalized)
                    node = next(n for n in forged["nodes"] if n["id"] == node_id)
                    target_field = node
                    parts = field.split(".")
                    for part in parts[:-1]:
                        target_field = target_field[part]
                    target_field[parts[-1]] = value
                    target = root / f"forged-{index}.malbolge"
                    result = subprocess.run(
                        [
                            str(helpers.ADAPTER),
                            "--layout-backend",
                            str(helpers.LAYOUT),
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
