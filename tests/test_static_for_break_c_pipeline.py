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
#   - Whole-C counted-loop break parity against the normative guest VM.
# - Must-Not:
#   - Confuse compile-time break proof with dynamic guest C control.
# - Allows:
#   - Inputs: pinned Clang C, forged normalized JSON, binary guest stdin.
#   - Outputs: guest stdout, exact steps, fail-closed compiler refusals.
#   - Side effects: isolated test artifacts under .temp only.
# - Split-When:
#   - General guest branch/loop lowering supersedes source-time unrolling.
# - Merge-When:
#   - Counted C control replay has one shared source-proof contract.
# - Summary:
#   - Selected break terminates only its authenticated counted C loop.

"""Source-proven counted C break executes the correct guest byte prefix."""

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
# Both builds run the same normative profile VM. Prefer its faster release
# build for binary matrices, retaining the repository debug-build fallback.
RELEASE_VM = ROOT / ".cache/rust/target/release/malbolge"
VM = RELEASE_VM if RELEASE_VM.is_file() else ROOT / ".cache/rust/target/debug/malbolge"
INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"


def break_source(*, bound: int = 3, predicate: str = "1") -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        f"    for (int i = 0; i < {bound}; ++i) {{\n"
        "        int current = getchar();\n"
        "        putchar(putchar(current));\n"
        f"        if ({predicate}) {{\n"
        "            break;\n"
        "        } else {\n"
        "            putchar(getchar());\n"
        "        }\n"
        "        putchar(getchar());\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


def nested_break_source(*, bound: int = 3) -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    for (int i = 0; i < 2; ++i) {\n"
        f"        for (int i = 0; i < {bound}; ++i) {{\n"
        "            int current = getchar();\n"
        "            putchar(putchar(current));\n"
        "            if (1) {\n"
        "                break;\n"
        "            }\n"
        "            putchar(getchar());\n"
        "        }\n"
        "        putchar(getchar());\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class StaticForBreakCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(tool.is_file() for tool in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned Clang, adapter, layout and VM required")

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
                "break-loop",
                str(path),
            ],
            capture_output=True,
            check=False,
            timeout=20,
        )
        if result.returncode:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)

    def test_selected_break_exits_first_iteration_without_skipped_reads(self) -> None:
        rng = random.Random(0xB2EA)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for count, predicate in ((1, "1"), (3, "1"), (16, "!(0 == 1) && (2 > 1)")):
                with self.subTest(count=count, predicate=predicate):
                    path = root / f"early-{count}.c"
                    target = root / f"early-{count}.malbolge"
                    path.write_text(
                        break_source(bound=count, predicate=predicate),
                        encoding="utf-8",
                    )
                    result = self.compile(path, target)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    for data in (
                        bytes((0, 255)),
                        bytes((128, 1)),
                        bytes(rng.randrange(256) for _ in range(2)),
                    ):
                        with self.subTest(data=data):
                            vm = self.vm(target, data)
                            self.assertEqual(vm.returncode, 0, vm.stderr)
                            self.assertEqual(
                                vm.stdout, bytes((data[0], data[0], data[1]))
                            )
                            self.assertEqual(vm.stderr, b"malbolge-steps-v1:6\n")

    def test_skipped_break_runs_else_and_later_body_effects(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "skipped.c"
            target = root / "skipped.malbolge"
            path.write_text(break_source(bound=1, predicate="0"), encoding="utf-8")
            result = self.compile(path, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            for data in (bytes((0, 255, 128, 1)), bytes((7, 0, 3, 255))):
                with self.subTest(data=data):
                    vm = self.vm(target, data)
                    expected = bytes((data[0], data[0], data[1], data[2], data[3]))
                    self.assertEqual(vm.returncode, 0, vm.stderr)
                    self.assertEqual(vm.stdout, expected)
                    self.assertEqual(vm.stderr, b"malbolge-steps-v1:10\n")

    def test_nested_break_exits_inner_only(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "nested.c"
            target = root / "nested.malbolge"
            path.write_text(nested_break_source(), encoding="utf-8")
            result = self.compile(path, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            for data in (bytes((0, 255, 128, 1, 42)), bytes((1, 42, 3, 254, 128))):
                with self.subTest(data=data):
                    vm = self.vm(target, data)
                    self.assertEqual(vm.returncode, 0, vm.stderr)
                    self.assertEqual(
                        vm.stdout,
                        bytes(
                            (
                                data[0],
                                data[0],
                                data[1],
                                data[2],
                                data[2],
                                data[3],
                                data[4],
                            )
                        ),
                    )
                    self.assertEqual(vm.stderr, b"malbolge-steps-v1:13\n")

    def test_untrusted_break_forms_refuse_target_publication(self) -> None:
        original = break_source()
        variants = (
            original.replace("break;", "continue;"),
            original.replace("break;", "return;"),
            original.replace("if (1)", "if (getchar())"),
            original.replace("int current = getchar();", "int current = 4;"),
            original.replace(
                "for (int i = 0; i < 3; ++i)", "for (int i = 0; i < 3; i += 2)"
            ),
            original.replace("putchar(getchar());\n    }", "putchar(42);\n    }"),
            break_source(bound=17),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, candidate in enumerate(variants):
                with self.subTest(index=index):
                    path = root / f"invalid-{index}.c"
                    target = root / f"invalid-{index}.malbolge"
                    path.write_text(candidate, encoding="utf-8")
                    result = self.compile(path, target)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_break_ancestry_or_span_refuses_publication(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "source.c"
            path.write_text(break_source(), encoding="utf-8")
            artifact = self.normalized(path)
            nodes = artifact["nodes"]
            selected = next(node for node in nodes if node["kind"] == "break-statement")
            variations = (
                ("parent", 2),
                ("kind", "continue-statement"),
                ("type", "i32"),
                ("operation", "++"),
                ("span.begin.column", selected["span"]["begin"]["column"] + 1),
                ("span.end.byte", selected["span"]["end"]["byte"] + 1),
            )
            for index, (field, value) in enumerate(variations):
                with self.subTest(index=index):
                    forged = copy.deepcopy(artifact)
                    node = next(
                        node for node in forged["nodes"] if node["id"] == selected["id"]
                    )
                    target = node
                    parts = field.split(".")
                    for part in parts[:-1]:
                        target = target[part]
                    target[parts[-1]] = value
                    output = root / f"forged-{index}.malbolge"
                    result = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(output),
                            "--capsule",
                        ],
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
