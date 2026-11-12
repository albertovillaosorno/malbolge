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
#   - Whole-C counted-loop continue parity against the normative guest VM.
# - Must-Not:
#   - Confuse compile-time continue proof with dynamic guest C control.
# - Allows:
#   - Inputs: pinned Clang C, forged normalized JSON, binary guest stdin.
#   - Outputs: guest stdout, exact steps, fail-closed compiler refusals.
#   - Side effects: isolated test artifacts under .temp only.
# - Split-When:
#   - General guest branch/loop lowering supersedes source-time unrolling.
# - Merge-When:
#   - Counted C control replay has one shared source-proof contract.
# - Summary:
#   - Selected continue skips the current body suffix but not later trips.

"""Source-proven C continue replays each later iteration's guest input."""

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


def continue_source(*, bound: int = 3, predicate: str = "1") -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        f"    for (int i = 0; i < {bound}; ++i) {{\n"
        "        int current = getchar();\n"
        "        putchar(putchar(current));\n"
        f"        if ({predicate}) {{\n"
        "            continue;\n"
        "        } else {\n"
        "            putchar(getchar());\n"
        "        }\n"
        "        putchar(getchar());\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


def nested_continue_source() -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    for (int i = 0; i < 2; ++i) {\n"
        "        for (int i = 0; i < 2; ++i) {\n"
        "            int current = getchar();\n"
        "            putchar(putchar(current));\n"
        "            if (1) {\n"
        "                continue;\n"
        "            }\n"
        "            putchar(getchar());\n"
        "        }\n"
        "        putchar(getchar());\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class StaticForContinueCPipelineTests(unittest.TestCase):
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
                "continue-loop",
                str(path),
            ],
            capture_output=True,
            check=False,
            timeout=20,
        )
        if result.returncode:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)

    def test_selected_continue_preserves_later_fresh_inputs(self) -> None:
        rng = random.Random(0xC071)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for count, predicate in ((1, "1"), (3, "1"), (4, "!(0 == 1) && (2 > 1)")):
                with self.subTest(count=count, predicate=predicate):
                    path = root / f"selected-{count}.c"
                    target = root / f"selected-{count}.malbolge"
                    path.write_text(
                        continue_source(bound=count, predicate=predicate),
                        encoding="utf-8",
                    )
                    result = self.compile(path, target)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    for data in (
                        bytes((0, 255, 128, 1, 42)[: count + 1]),
                        bytes(rng.randrange(256) for _ in range(count + 1)),
                    ):
                        with self.subTest(data=data):
                            vm = self.vm(target, data)
                            self.assertEqual(vm.returncode, 0, vm.stderr)
                            expected = bytes(
                                byte
                                for index, value in enumerate(data)
                                for byte in (
                                    (value, value) if index < count else (value,)
                                )
                            )
                            self.assertEqual(vm.stdout, expected)
                            self.assertEqual(
                                vm.stderr,
                                f"malbolge-steps-v1:{3 * count + 3}\n".encode(),
                            )

    def test_unselected_continue_executes_tail(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "skipped.c"
            target = root / "skipped.malbolge"
            path.write_text(continue_source(bound=1, predicate="0"), encoding="utf-8")
            result = self.compile(path, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            for data in (bytes((0, 255, 128, 1)), bytes((7, 0, 3, 255))):
                with self.subTest(data=data):
                    vm = self.vm(target, data)
                    self.assertEqual(vm.returncode, 0, vm.stderr)
                    self.assertEqual(
                        vm.stdout, bytes((data[0], data[0], data[1], data[2], data[3]))
                    )
                    self.assertEqual(vm.stderr, b"malbolge-steps-v1:10\n")

    def test_nested_continue_skips_inner_suffix_only(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "nested.c"
            target = root / "nested.malbolge"
            path.write_text(nested_continue_source(), encoding="utf-8")
            result = self.compile(path, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            for data in (
                bytes((0, 255, 128, 1, 42, 9, 7)),
                bytes((1, 42, 3, 254, 128, 3, 0)),
            ):
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
                                data[1],
                                data[2],
                                data[3],
                                data[3],
                                data[4],
                                data[4],
                                data[5],
                                data[6],
                            )
                        ),
                    )
                    self.assertEqual(vm.stderr, b"malbolge-steps-v1:19\n")

    def test_untrusted_continue_sources_refuse_publication(self) -> None:
        original = continue_source()
        variants = (
            original.replace("continue;", "return;"),
            original.replace("if (1)", "if (getchar())"),
            original.replace("int current = getchar();", "int current = 4;"),
            original.replace(
                "for (int i = 0; i < 3; ++i)", "for (int i = 0; i < 3; i += 2)"
            ),
            original.replace("putchar(getchar());\n    }", "putchar(42);\n    }"),
            continue_source(bound=17),
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

    def test_forged_continue_ancestry_or_span_refuses_publication(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "source.c"
            path.write_text(continue_source(), encoding="utf-8")
            artifact = self.normalized(path)
            nodes = artifact["nodes"]
            selected = next(
                node for node in nodes if node["kind"] == "continue-statement"
            )
            variations = (
                ("parent", 2),
                ("kind", "break-statement"),
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
