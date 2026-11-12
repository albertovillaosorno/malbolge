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
#   - Guest VM parity for counted input-local loops inside constant C branches.
# - Must-Not:
#   - Pretend that compile-time C branching implies dynamic guest control.
# - Allows:
#   - Inputs: pinned Clang normalized C and binary guest stdin.
#   - Outputs: real VM stdout, exact VM steps, fail-closed compiler refusals.
#   - Side effects: temporary source and guest artifacts only.
# - Split-When:
#   - General guest byte-value storage supersedes accumulator-local replay.
# - Merge-When:
#   - Static branch and loop lowering share a common provenance proof.
# - Summary:
#   - Selected branch-local loops carry fresh input SSA between calls.

"""Nested counted loops in constant C branches preserve live byte identity."""

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
VM = ROOT / ".cache/rust/target/debug/malbolge"
INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"


def source(*, selected: bool = True, outer: int = 2, inner: int = 2) -> str:
    condition = "1" if selected else "0"
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        f"    if ({condition}) {{\n"
        f"        for (int i = 0; i < {outer}; ++i) {{\n"
        f"            for (int i = 0; i < {inner}; ++i) {{\n"
        "                int current = getchar();\n"
        "                putchar(putchar(current));\n"
        "            }\n"
        "            putchar(getchar());\n"
        "        }\n"
        "    } else {\n"
        "        for (int i = 0; i < 2; ++i) {\n"
        "            putchar(getchar());\n"
        "        }\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


def else_local_source(*, stale: bool = False) -> str:
    tail = "putchar(before);" if stale else "putchar(getchar());"
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int before = getchar();\n"
        "    if (0) {\n"
        "        putchar(before);\n"
        "    } else {\n"
        "        for (int i = 0; i < 2; ++i) {\n"
        "            int current = getchar();\n"
        "            putchar(putchar(current));\n"
        "        }\n"
        "    }\n"
        f"    {tail}\n"
        "}\n"
    )


class StaticIfCountedLoopCPipelineTests(unittest.TestCase):
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
            timeout=40,
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
                "if-loop",
                str(path),
            ],
            capture_output=True,
            check=False,
            timeout=20,
        )
        if result.returncode:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)

    def test_selected_and_skipped_counted_loops_match_binary_guest(self) -> None:
        rng = random.Random(0x1FCAFE)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for selected, outer, inner in ((True, 1, 1), (True, 2, 2), (False, 2, 2)):
                with self.subTest(selected=selected, outer=outer, inner=inner):
                    path = root / f"source-{selected}-{outer}-{inner}.c"
                    target = root / f"source-{selected}-{outer}-{inner}.malbolge"
                    path.write_text(
                        source(selected=selected, outer=outer, inner=inner),
                        encoding="utf-8",
                    )
                    built = self.compile(path, target)
                    self.assertEqual(built.returncode, 0, built.stderr)
                    reads = outer * (inner + 1) + 1 if selected else 3
                    inputs = (
                        bytes((0, 255, 128, 1, 42, 3, 254) * reads)[:reads],
                        bytes(rng.randrange(256) for _ in range(reads)),
                    )
                    for data in inputs:
                        with self.subTest(data=data):
                            result = self.vm(target, data)
                            self.assertEqual(result.returncode, 0, result.stderr)
                            expected = bytearray()
                            cursor = 0
                            if selected:
                                for _ in range(outer):
                                    for _ in range(inner):
                                        expected.extend((data[cursor],) * 2)
                                        cursor += 1
                                    expected.append(data[cursor])
                                    cursor += 1
                            else:
                                expected.extend(data[:2])
                                cursor = 2
                            expected.append(data[cursor])
                            self.assertEqual(result.stdout, bytes(expected))
                            self.assertEqual(
                                result.stderr,
                                f"malbolge-steps-v1:{1 + reads + len(expected)}\n".encode(),
                            )

    def test_selected_else_loop_overwrites_outer_input_identity(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "else-loop.c"
            target = root / "else-loop.malbolge"
            path.write_text(else_local_source(), encoding="utf-8")
            built = self.compile(path, target)
            self.assertEqual(built.returncode, 0, built.stderr)
            for data in (bytes((77, 0, 255, 128)), bytes((1, 42, 3, 254))):
                with self.subTest(data=data):
                    result = self.vm(target, data)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(
                        result.stdout,
                        bytes((data[1], data[1], data[2], data[2], data[3])),
                    )
                    self.assertEqual(result.stderr, b"malbolge-steps-v1:10\n")
            stale_path = root / "stale.c"
            stale_target = root / "stale.malbolge"
            stale_path.write_text(else_local_source(stale=True), encoding="utf-8")
            rejected = self.compile(stale_path, stale_target)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertFalse(stale_target.exists())

    def test_untrusted_branch_loop_source_refuses_publication(self) -> None:
        mutations = (
            source().replace("if (1)", "if (getchar())"),
            source().replace("putchar(putchar(current));", "putchar(current + 1);"),
            source().replace("int current = getchar();", "int current = 2;"),
            source().replace(
                "for (int i = 0; i < 2; ++i)", "for (int i = 0; i < 2; i += 2)"
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, candidate in enumerate(mutations):
                with self.subTest(index=index):
                    path = root / f"bad-{index}.c"
                    target = root / f"bad-{index}.malbolge"
                    path.write_text(candidate, encoding="utf-8")
                    built = self.compile(path, target)
                    self.assertNotEqual(built.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_selected_loop_ancestry_refuses(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "source.c"
            path.write_text(source(), encoding="utf-8")
            original = self.normalized(path)
            nodes = original["nodes"]
            loop = next(node for node in nodes if node["kind"] == "for-statement")
            local = next(
                node
                for node in nodes
                if node["kind"] == "variable-declaration" and node["name"] == "current"
            )
            variants = (
                (loop["id"], "parent", 2),
                (loop["id"], "span.begin.column", 1),
                (local["id"], "parent", 2),
                (local["id"], "reference", "current@1"),
            )
            for index, (node_id, field, value) in enumerate(variants):
                with self.subTest(index=index):
                    forged = copy.deepcopy(original)
                    node = next(n for n in forged["nodes"] if n["id"] == node_id)
                    slot = node
                    parts = field.split(".")
                    for part in parts[:-1]:
                        slot = slot[part]
                    slot[parts[-1]] = value
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
