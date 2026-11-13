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
#   - Whole-C compound induction predicates with actual guest byte I/O.
# - Must-Not:
#   - Fold input bytes or accept runtime C predicates as source constants.
# - Allows:
#   - Inputs: pinned Clang, binary stdin, forged normalized AST.
#   - Outputs: VM parity and fail-closed diagnostics without guest publication.
#   - Side effects: isolated temporary C sources and guest artifacts.
# - Split-When:
#   - Dynamic C predicates gain real guest control-flow lowering.
# - Merge-When:
#   - Bounded induction branches share an exact source-proof contract.
# - Summary:
#   - Compound induction checks select each trip before guest byte replay.

"""Whole-program C compound loop predicates retain fresh guest byte effects."""

from __future__ import annotations

import copy
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_induction_static_for_c_pipeline import (
    ADAPTER,
    DRIVER,
    FRONTEND,
    INCLUDE,
    LAYOUT,
    RESOURCE,
    ROOT,
    VM,
)


def program(predicate: str = "i >= 1 && i < 3", bound: int = 4) -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        f"    for (int i = 0; i < {bound}; ++i) {{\n"
        "        int current = getchar();\n"
        f"        if ({predicate}) {{\n"
        "            putchar(putchar(current));\n"
        "            continue;\n"
        "        }\n"
        "        if (i == 3) {\n"
        "            break;\n"
        "        }\n"
        "        putchar(current);\n"
        "        putchar(getchar());\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


def oracle(predicate: str, bound: int, data: bytes) -> tuple[bytes, int]:
    index = 0
    output = bytearray()
    for i in range(bound):
        current = data[index]
        index += 1
        selected = {
            "and": 1 <= i < 3,
            "or": i == 0 or i == 2,
            "nested": i < 1 or (1 <= i < 3),
            "literal": i < 3 and bool(1),
        }[predicate]
        if selected:
            output.extend((current, current))
            continue
        if i == 3:
            break
        output.append(current)
        output.append(data[index])
        index += 1
    output.append(data[index])
    return bytes(output), index + 1


class CompoundInductionForCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned source-C frontend, compiler and guest VM needed")

    @staticmethod
    def compile(path: Path, target: Path) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--capsule",
                "--output",
                str(target),
                str(path),
            ],
            capture_output=True,
            check=False,
            timeout=90,
        )

    @staticmethod
    def vm(path: Path, data: bytes) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [str(VM), str(path), "--input-stdin", "--report-steps"],
            input=data,
            capture_output=True,
            check=False,
            timeout=30,
        )

    @staticmethod
    def normalized(path: Path) -> dict[str, object]:
        result = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "compound",
                str(path),
            ],
            capture_output=True,
            check=False,
            timeout=20,
        )
        if result.returncode:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)

    def test_compound_trip_control_matches_real_guest_vm(self) -> None:
        rng = random.Random(0xC0A7D)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for label, predicate, bound in (
                ("and", "i >= 1 && i < 3", 4),
                ("or", "i == 0 || i == 2", 4),
                ("nested", "i < 1 || i >= 1 && i < 3", 4),
                ("literal", "i < 3 && 1", 4),
                ("and-short", "i >= 1 && i < 3", 2),
            ):
                with self.subTest(label=label):
                    path = root / f"{label}.c"
                    target = root / f"{label}.malbolge"
                    path.write_text(program(predicate, bound), encoding="utf-8")
                    result = self.compile(path, target)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    for data in (
                        bytes((0, 255, 128, 1, 42, 9, 27, 45)),
                        bytes(rng.randrange(256) for _ in range(8)),
                    ):
                        expected, consumed = oracle(label.split("-")[0], bound, data)
                        vm = self.vm(target, data)
                        self.assertEqual(vm.returncode, 0, vm.stderr)
                        self.assertEqual(vm.stdout, expected)
                        self.assertEqual(
                            vm.stderr,
                            f"malbolge-steps-v1:{consumed + len(expected) + 1}\n".encode(),
                        )

    def test_runtime_conditions_and_unbounded_source_refuse(self) -> None:
        source = program()
        variants = (
            source.replace("i >= 1", "current >= 1"),
            source.replace("i < 3", "getchar() < 3"),
            source.replace("i < 3", "i + 1 < 3"),
            source.replace("i < 3", "i < getchar()"),
            source.replace("i < 3", "i = 3"),
            source.replace("++i)", "i += 2)"),
            program(bound=17),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, variant in enumerate(variants):
                with self.subTest(index=index):
                    path = root / f"invalid-{index}.c"
                    target = root / f"invalid-{index}.malbolge"
                    path.write_text(variant, encoding="utf-8")
                    self.assertNotEqual(self.compile(path, target).returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_compound_tree_refuses(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "source.c"
            path.write_text(program(), encoding="utf-8")
            normalized = self.normalized(path)
            nodes = normalized["nodes"]
            logical = next(node for node in nodes if node.get("operation") == "&&")
            first = next(node for node in nodes if node["parent"] == logical["id"])
            second = next(
                node
                for node in nodes
                if node["parent"] == logical["id"] and node["id"] != first["id"]
            )
            cast = next(node for node in nodes if node["parent"] == second["id"])
            variable = next(node for node in nodes if node["parent"] == cast["id"])
            mutations = (
                (logical["id"], "operation", "++"),
                (logical["id"], "parent", 2),
                (logical["id"], "constant_integer", "1"),
                (logical["id"], "span.end.byte", 0),
                (first["id"], "parent", 2),
                (first["id"], "operation", "+"),
                (second["id"], "operation", "*"),
                (second["id"], "span.begin.byte", 0),
                (cast["id"], "operation", "integral-cast"),
                (variable["id"], "reference", "i@99999"),
            )
            for index, (node_id, field, value) in enumerate(mutations):
                with self.subTest(index=index):
                    forged = copy.deepcopy(normalized)
                    node = next(n for n in forged["nodes"] if n["id"] == node_id)
                    field_target = node
                    parts = field.split(".")
                    for part in parts[:-1]:
                        field_target = field_target[part]
                    field_target[parts[-1]] = value
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
