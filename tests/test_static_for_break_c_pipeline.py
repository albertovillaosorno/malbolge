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
import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast

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


def guest_or_explicit_eof_refusal(
    test: unittest.TestCase,
    compiled: subprocess.CompletedProcess[bytes],
    artifact: Path,
) -> bool:
    """Require real guest publication or a typed refusal for unhandled C EOF.

    Successful-byte-only source proofs do not authorize an executable whose
    stdin may exhaust. A rejection is not guest equivalence evidence.
    """
    source = artifact.with_suffix(".c")
    test.assertTrue(source.is_file())
    # Prove the observable EOF behavior of the *original C source* before
    # allowing any compiler success. A byte-only backend's apparent success
    # on full input streams is insufficient to publish an executable.
    vectors = (b"", b"\x00", b"\xff", b"\x00\x80")
    clang = ROOT / ".dependencies/llvm/22.1.8/bin/clang"
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(ROOT / ".dependencies/llvm/22.1.8/lib")
    with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
        root = Path(directory)
        wrapper = root / "entry.c"
        wrapper.write_text(
            f'#include "{source.resolve()}"\n'
            "int main(void) { stream(); return 0; }\n",
            encoding="utf-8",
        )
        expected: dict[bytes, bytes] = {}
        for optimization in ("-O0", "-O2"):
            native = root / f"native-{optimization[2:]}"
            built = subprocess.run(
                [
                    str(clang),
                    "-std=c23",
                    optimization,
                    "-fsanitize=undefined",
                    "-fno-sanitize-recover=all",
                    str(wrapper),
                    "-o",
                    str(native),
                ],
                env=env,
                capture_output=True,
                check=False,
                timeout=20,
            )
            test.assertEqual(built.returncode, 0, built.stderr)
            for data in vectors:
                run = subprocess.run(
                    [str(native)],
                    input=data,
                    capture_output=True,
                    check=False,
                    timeout=10,
                )
                test.assertEqual(run.returncode, 0, run.stderr)
                if data in expected:
                    test.assertEqual(run.stdout, expected[data])
                else:
                    expected[data] = run.stdout

    if compiled.returncode != 0:
        test.assertIn(b"normalized frontend rejected: Unsupported", compiled.stderr)
        test.assertFalse(artifact.exists())
        return False
    test.assertTrue(artifact.is_file())
    for data in vectors:
        guest = subprocess.run(
            [str(VM), str(artifact), "--input-stdin", "--max-steps", "100000"],
            input=data,
            capture_output=True,
            check=False,
            timeout=15,
        )
        test.assertEqual(guest.returncode, 0, guest.stderr)
        test.assertEqual(guest.stdout, expected[data])
    return True


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
                    if not guest_or_explicit_eof_refusal(self, result, target):
                        continue
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
            if not guest_or_explicit_eof_refusal(self, result, target):
                return
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
            if not guest_or_explicit_eof_refusal(self, result, target):
                return
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
            # Canonical continue is now supported; reject dynamic control.
            original.replace("break;", "if (current) break;"),
            original.replace("break;", "if (current) return;"),
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
            nodes = cast(list[dict[str, object]], artifact["nodes"])
            selected = next(node for node in nodes if node["kind"] == "break-statement")
            selected_span = cast(dict[str, dict[str, int]], selected["span"])
            variations = (
                ("parent", 2),
                ("kind", "continue-statement"),
                ("type", "i32"),
                ("operation", "++"),
                ("span.begin.column", selected_span["begin"]["column"] + 1),
                ("span.end.byte", selected_span["end"]["byte"] + 1),
            )
            for index, (field, value) in enumerate(variations):
                with self.subTest(index=index):
                    forged = copy.deepcopy(artifact)
                    node = next(
                        node
                        for node in cast(list[dict[str, object]], forged["nodes"])
                        if node["id"] == selected["id"]
                    )
                    target = node
                    parts = field.split(".")
                    for part in parts[:-1]:
                        target = cast(dict[str, object], target)[part]
                    cast(dict[str, object], target)[parts[-1]] = value
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
