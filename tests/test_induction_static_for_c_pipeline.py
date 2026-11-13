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
#   - Guest VM parity for finite source-C induction-dependent byte branches.
# - Must-Not:
#   - Treat dynamic C byte predicates as source constants or host-computed I/O.
# - Allows:
#   - Inputs: pinned Clang C, forged normalized AST, binary guest stdin.
#   - Outputs: guest stdout/steps and fail-closed unsupported diagnostics.
#   - Side effects: isolated temporary guest artifacts only.
# - Split-When:
#   - General guest runtime C control replaces source-time bounded replay.
# - Merge-When:
#   - Other static counted-loop C control shares one proof contract.
# - Summary:
#   - Every static trip selects its own branch but reads fresh guest input.

"""Counter-dependent branches must select different guest I/O per C trip."""

from __future__ import annotations

import copy
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
ADAPTER = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT = ROOT / ".cache/rust/target/debug/malbolge_layout"
RELEASE_VM = ROOT / ".cache/rust/target/release/malbolge"
VM = RELEASE_VM if RELEASE_VM.is_file() else ROOT / ".cache/rust/target/debug/malbolge"
INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"


def exit_program(bound: int = 4) -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        f"    for (int i = 0; i < {bound}; ++i) {{\n"
        "        int current = getchar();\n"
        "        if (i == 1) {\n"
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


def comparison_program(operation: str, bound: int = 4) -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        f"    for (int i = 0; i < {bound}; ++i) {{\n"
        "        int current = getchar();\n"
        f"        if (i {operation} 2) {{\n"
        "            putchar(putchar(current));\n"
        "        } else {\n"
        "            putchar(current);\n"
        "        }\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


def nested_program() -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    for (int i = 0; i < 2; ++i) {\n"
        "        for (int i = 0; i < 3; ++i) {\n"
        "            if (i == 1) {\n"
        "                putchar(getchar());\n"
        "                continue;\n"
        "            }\n"
        "            putchar(getchar());\n"
        "        }\n"
        "        putchar(getchar());\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


def exit_oracle(bound: int, data: bytes) -> tuple[bytes, int]:
    cursor = 0
    output: list[int] = []
    for i in range(bound):
        current = data[cursor]
        cursor += 1
        if i == 1:
            output.extend((current, current))
            continue
        if i == 3:
            break
        output.append(current)
        output.append(data[cursor])
        cursor += 1
    output.append(data[cursor])
    cursor += 1
    return bytes(output), cursor


class InductionStaticForCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(tool.is_file() for tool in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C frontend, compiler, layout and VM required")

    @staticmethod
    def compile(path: Path, target: Path) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [
                sys.executable, "-B", str(DRIVER), "--repository-tools",
                "--capsule", "--output", str(target), str(path),
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
        process = subprocess.run(
            [
                str(FRONTEND), "--guest-include", str(INCLUDE),
                "--resource-dir", str(RESOURCE), "--source-id", "induction",
                str(path),
            ],
            capture_output=True,
            check=False,
            timeout=20,
        )
        if process.returncode:
            raise AssertionError(process.stderr)
        return json.loads(process.stdout)

    def test_induction_drives_selected_continue_and_later_break(self) -> None:
        rng = random.Random(0xC0FFEE)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for bound in (1, 2, 4, 5):
                with self.subTest(bound=bound):
                    path = root / f"exits-{bound}.c"
                    target = root / f"exits-{bound}.malbolge"
                    path.write_text(exit_program(bound), encoding="utf-8")
                    result = self.compile(path, target)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    for data in (
                        bytes((0, 255, 128, 1, 42, 11, 127, 233, 16)),
                        bytes(rng.randrange(256) for _ in range(10)),
                    ):
                        expected, reads = exit_oracle(bound, data)
                        vm = self.vm(target, data)
                        self.assertEqual(vm.returncode, 0, vm.stderr)
                        self.assertEqual(vm.stdout, expected)
                        self.assertEqual(
                            vm.stderr,
                            f"malbolge-steps-v1:{reads + len(expected) + 1}\n".encode(),
                        )

    def test_six_induction_comparisons_select_per_trip(self) -> None:
        predicates = {
            "==": lambda i: i == 2,
            "!=": lambda i: i != 2,
            "<": lambda i: i < 2,
            "<=": lambda i: i <= 2,
            ">": lambda i: i > 2,
            ">=": lambda i: i >= 2,
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, (operation, predicate) in enumerate(predicates.items()):
                with self.subTest(operation=operation):
                    path = root / f"comparison-{index}.c"
                    target = root / f"comparison-{index}.malbolge"
                    path.write_text(comparison_program(operation), encoding="utf-8")
                    result = self.compile(path, target)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    for data in (bytes((0, 255, 128, 1, 42)),
                                 bytes((99, 14, 239, 0, 155))):
                        expected = bytes(
                            byte
                            for i, byte in enumerate(data[:4])
                            for _ in range(2 if predicate(i) else 1)
                        ) + data[4:]
                        vm = self.vm(target, data)
                        self.assertEqual(vm.returncode, 0, vm.stderr)
                        self.assertEqual(vm.stdout, expected)
                        self.assertEqual(
                            vm.stderr,
                            f"malbolge-steps-v1:{len(data) + len(expected) + 1}\n".encode(),
                        )

    def test_shadowed_inner_counter_continue_preserves_outer_io(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "nested.c"
            target = root / "nested.malbolge"
            path.write_text(nested_program(), encoding="utf-8")
            result = self.compile(path, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            for data in (bytes((0, 255, 128, 1, 42, 11, 127, 233, 16)),
                         bytes((16, 233, 127, 11, 42, 1, 128, 255, 0))):
                vm = self.vm(target, data)
                self.assertEqual(vm.returncode, 0, vm.stderr)
                self.assertEqual(vm.stdout, data)
                self.assertEqual(vm.stderr, b"malbolge-steps-v1:19\n")

    def test_postfix_induction_preserves_branch_exits_and_live_stdin(self) -> None:
        rng = random.Random(0x50F17)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for bound in (1, 2, 4, 5):
                with self.subTest(bound=bound):
                    source = exit_program(bound).replace(
                        "++i)", "i++)"
                    ).replace("i == 1", "i && !(i == 3)")
                    path = root / f"postfix-{bound}.c"
                    target = root / f"postfix-{bound}.malbolge"
                    path.write_text(source, encoding="utf-8")
                    result = self.compile(path, target)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    for data in (
                        bytes((0, 255, 128, 1, 42, 11, 127, 233, 16)),
                        bytes(rng.randrange(256) for _ in range(10)),
                    ):
                        output = bytearray()
                        cursor = 0
                        for i in range(bound):
                            current = data[cursor]
                            cursor += 1
                            if i != 0 and i != 3:
                                output.extend((current, current))
                                continue
                            if i == 3:
                                break
                            output.append(current)
                            output.append(data[cursor])
                            cursor += 1
                        output.append(data[cursor])
                        cursor += 1
                        vm = self.vm(target, data)
                        self.assertEqual(vm.returncode, 0, vm.stderr)
                        self.assertEqual(vm.stdout, bytes(output))
                        self.assertEqual(
                            vm.stderr,
                            f"malbolge-steps-v1:{cursor + len(output) + 1}\n".encode(),
                        )

    def test_postfix_increment_forged_geometry_refuses(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "postfix.c"
            path.write_text(exit_program().replace("++i)", "i++)"),
                            encoding="utf-8")
            normalized = self.normalized(path)
            nodes = normalized["nodes"]
            loop = next(n for n in nodes if n["kind"] == "for-statement")
            increment = next(
                n for n in nodes if n["parent"] == loop["id"]
                and n["kind"] == "unary-expression"
            )
            variable = next(n for n in nodes if n["parent"] == increment["id"])
            mutations = (
                (increment["id"], "operation", "--"),
                (increment["id"], "parent", 2),
                (increment["id"], "type", "u32"),
                (increment["id"], "constant_integer", "1"),
                (increment["id"], "span.end.byte", 0),
                (variable["id"], "reference", "i@999999"),
                (variable["id"], "parent", 2),
                (variable["id"], "span.begin.byte", 0),
                (variable["id"], "span.end.byte", 0),
                (variable["id"], "span.begin.column", 0),
            )
            for index, (node_id, field, value) in enumerate(mutations):
                with self.subTest(index=index):
                    forged = copy.deepcopy(normalized)
                    node = next(n for n in forged["nodes"] if n["id"] == node_id)
                    target_field = node
                    components = field.split(".")
                    for component in components[:-1]:
                        target_field = target_field[component]
                    target_field[components[-1]] = value
                    target = root / f"forged-postfix-{index}.malbolge"
                    result = subprocess.run(
                        [
                            str(ADAPTER), "--layout-backend", str(LAYOUT),
                            "--output", str(target), "--capsule",
                        ],
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(target.exists())

    def test_compound_unit_step_retains_live_io_and_exact_exits(self) -> None:
        rng = random.Random(0xA11CE)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for bound in (2, 4):
                with self.subTest(bound=bound):
                    source = exit_program(bound).replace(
                        "++i)", "i += 1)"
                    ).replace("i == 1", "i && !(i == 3)")
                    path = root / f"compound-{bound}.c"
                    target = root / f"compound-{bound}.malbolge"
                    path.write_text(source, encoding="utf-8")
                    result = self.compile(path, target)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    for data in (
                        bytes((0, 255, 128, 1, 42, 11, 127, 233, 16)),
                        bytes(rng.randrange(256) for _ in range(10)),
                    ):
                        output = bytearray()
                        cursor = 0
                        for i in range(bound):
                            current = data[cursor]
                            cursor += 1
                            if i != 0 and i != 3:
                                output.extend((current, current))
                                continue
                            if i == 3:
                                break
                            output.append(current)
                            output.append(data[cursor])
                            cursor += 1
                        output.append(data[cursor])
                        cursor += 1
                        vm = self.vm(target, data)
                        self.assertEqual(vm.returncode, 0, vm.stderr)
                        self.assertEqual(vm.stdout, bytes(output))
                        self.assertEqual(
                            vm.stderr,
                            f"malbolge-steps-v1:{cursor + len(output) + 1}\n".encode(),
                        )

    def test_compound_step_source_and_forged_literal_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            original = exit_program().replace("++i)", "i += 1)")
            for index, variant in enumerate((
                original.replace("i += 1", "i += 2"),
                original.replace("i += 1", "i += 0"),
                original.replace("i += 1", "i -= 1"),
                original.replace("i += 1", "i += getchar()"),
                original.replace("i += 1", "i += 1U"),
            )):
                with self.subTest(source=index):
                    path = root / f"invalid-compound-{index}.c"
                    target = root / f"invalid-compound-{index}.malbolge"
                    path.write_text(variant, encoding="utf-8")
                    self.assertNotEqual(self.compile(path, target).returncode, 0)
                    self.assertFalse(target.exists())
            path = root / "compound.c"
            path.write_text(original, encoding="utf-8")
            normalized = self.normalized(path)
            nodes = normalized["nodes"]
            increment = next(
                node for node in nodes
                if node["kind"] == "compound-assignment-expression"
            )
            operands = [node for node in nodes if node["parent"] == increment["id"]]
            self.assertEqual(len(operands), 2)
            variable, literal = operands
            mutations = (
                (increment["id"], "operation", "-="),
                (increment["id"], "parent", 2),
                (increment["id"], "span.end.byte", 0),
                (variable["id"], "reference", "i@999999"),
                (variable["id"], "span.end.column", 0),
                (literal["id"], "constant_integer", "2"),
                (literal["id"], "literal", "2"),
                (literal["id"], "parent", 2),
                (literal["id"], "span.begin.byte", 0),
                (literal["id"], "type", "u32"),
            )
            for index, (node_id, field, value) in enumerate(mutations):
                with self.subTest(forged=index):
                    forged = copy.deepcopy(normalized)
                    node = next(n for n in forged["nodes"] if n["id"] == node_id)
                    target_field = node
                    components = field.split(".")
                    for component in components[:-1]:
                        target_field = target_field[component]
                    target_field[components[-1]] = value
                    target = root / f"forged-compound-{index}.malbolge"
                    result = subprocess.run(
                        [
                            str(ADAPTER), "--layout-backend", str(LAYOUT),
                            "--output", str(target), "--capsule",
                        ],
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(target.exists())

    def test_unsupported_dynamic_control_refuses_artifact(self) -> None:
        source = exit_program()
        variants = (
            source.replace("if (i == 1)", "if (current == 1)"),
            source.replace("if (i == 1)", "if (getchar() == 1)"),
            source.replace("if (i == 1)", "if ((i + 1) == 2)"),
            source.replace("if (i == 1)", "if (i == getchar())"),
            source.replace("if (i == 1)", "if (i == 1 && getchar())"),
            source.replace("if (i == 1)", "if (i = 1)"),
            source.replace("++i)", "i += 2)"),
            exit_program(bound=17),
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

    def test_forged_induction_reference_or_ast_span_refuses(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "source.c"
            path.write_text(exit_program(), encoding="utf-8")
            normalized = self.normalized(path)
            nodes = normalized["nodes"]
            predicate = next(
                node for node in nodes
                if node["kind"] == "binary-expression"
                and node.get("operation") == "=="
            )
            cast = next(
                node for node in nodes
                if node["parent"] == predicate["id"]
                and node["kind"] == "cast-expression"
            )
            variable = next(
                node for node in nodes if node["parent"] == cast["id"]
            )
            mutations = (
                (predicate["id"], "operation", "*"),
                (predicate["id"], "parent", 2),
                (predicate["id"], "constant_integer", "1"),
                (cast["id"], "operation", "integral-cast"),
                (variable["id"], "reference", "i@999999"),
                (variable["id"], "parent", 2),
                (variable["id"], "span.begin.byte", 0),
                (predicate["id"], "span.end.byte", 0),
            )
            for index, (node_id, field, value) in enumerate(mutations):
                with self.subTest(index=index):
                    forged = copy.deepcopy(normalized)
                    node = next(n for n in forged["nodes"] if n["id"] == node_id)
                    target_field = node
                    path_components = field.split(".")
                    for component in path_components[:-1]:
                        target_field = target_field[component]
                    target_field[path_components[-1]] = value
                    target = root / f"forged-{index}.malbolge"
                    result = subprocess.run(
                        [
                            str(ADAPTER), "--layout-backend", str(LAYOUT),
                            "--output", str(target), "--capsule",
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
