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
#   - Guest parity for nested source-authenticated counted C loops.
# - Must-Not:
#   - Substitute host I/O for the Malbolge VM or claim dynamic C loops.
# - Allows:
#   - Inputs: pinned Clang JSON and independent binary guest streams.
#   - Outputs: real guest byte output, VM steps and fail-closed refusals.
#   - Side effects: isolated temporary compiler and guest artifacts.
# - Split-When:
#   - General guest C loop lowering supersedes bounded source unrolling.
# - Merge-When:
#   - Shared bounded-loop tests cover multiple source nesting levels.
# - Summary:
#   - Each nested iteration performs fresh guest I/O in C order.

"""Two nested finite C loops must execute distinct guest byte effects."""

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


def source(outer: int = 2, inner: int = 3) -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        f"    for (int i = 0; i < {outer}; ++i) {{\n"
        f"        for (int i = 0; i < {inner}; ++i) {{\n"
        "            int current = getchar();\n"
        "            if (1) {\n"
        "                putchar(putchar(current));\n"
        "            } else {\n"
        "                getchar();\n"
        "            }\n"
        "        }\n"
        "        putchar(getchar());\n"
        "    }\n"
        "}\n"
    )


class NestedStaticForCPipelineTests(unittest.TestCase):
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
                "nested-for",
                str(path),
            ],
            capture_output=True,
            check=False,
            timeout=20,
        )
        if result.returncode:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)

    def test_two_level_nested_guest_stream_with_branch_local(self) -> None:
        rng = random.Random(0xCAFE2)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for outer, inner in ((1, 1), (2, 2), (2, 3)):
                with self.subTest(outer=outer, inner=inner):
                    path = root / f"stream-{outer}-{inner}.c"
                    target = root / f"stream-{outer}-{inner}.malbolge"
                    path.write_text(source(outer, inner), encoding="utf-8")
                    built = self.compile(path, target)
                    self.assertEqual(built.returncode, 0, built.stderr)
                    count = outer * (inner + 1)
                    samples = (
                        bytes((0, 255, 128, 1, 64, 13, 237, 17) * count)[:count],
                        bytes(rng.randrange(256) for _ in range(count)),
                    )
                    for data in samples:
                        with self.subTest(data=data):
                            guest = self.vm(target, data)
                            self.assertEqual(guest.returncode, 0, guest.stderr)
                            expected = bytearray()
                            cursor = 0
                            for _ in range(outer):
                                for _ in range(inner):
                                    expected.extend((data[cursor],) * 2)
                                    cursor += 1
                                expected.append(data[cursor])
                                cursor += 1
                            self.assertEqual(guest.stdout, bytes(expected))
                            steps = 1 + outer * (3 * inner + 2)
                            self.assertEqual(
                                guest.stderr,
                                f"malbolge-steps-v1:{steps}\n".encode(),
                            )

    def test_nested_loop_forgery_refuses_target_publication(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "nested.c"
            path.write_text(source(), encoding="utf-8")
            normalized = self.normalized(path)
            nodes = normalized["nodes"]
            loops = [node for node in nodes if node["kind"] == "for-statement"]
            self.assertEqual(len(loops), 2)
            inner = loops[1]
            inner_body = next(
                node
                for node in nodes
                if node["kind"] == "compound-statement"
                and node["parent"] == inner["id"]
            )
            changes = (
                (inner["id"], "parent", 2),
                (inner["id"], "span.begin.column", 1),
                (inner["id"], "span.end.byte", 0),
                (inner["id"] + 2, "reference", "i@52"),
                (inner["id"] + 6, "parent", 3),
                (inner_body["id"], "parent", 3),
                (inner_body["id"], "span.end.column", 1),
            )
            for index, (node_id, field, replacement) in enumerate(changes):
                with self.subTest(index=index):
                    forged = copy.deepcopy(normalized)
                    node = next(n for n in forged["nodes"] if n["id"] == node_id)
                    slot = node
                    parts = field.split(".")
                    for part in parts[:-1]:
                        slot = slot[part]
                    slot[parts[-1]] = replacement
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
                        timeout=20,
                    )
                    self.assertNotEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(target.exists())

    def test_unsupported_nested_source_control_refuses(self) -> None:
        triple = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    for (int i = 0; i < 2; ++i) {\n"
            "        for (int i = 0; i < 2; ++i) {\n"
            "            for (int i = 0; i < 2; ++i) {\n"
            "                putchar(getchar());\n"
            "            }\n"
            "        }\n"
            "    }\n"
            "}\n"
        )
        mutations = (
            triple,
            source().replace(
                "        for (int i = 0; i < 3; ++i) {",
                "        for (int i = 0; i < 17; ++i) {",
            ),
            source().replace(
                "            int current = getchar();",
                "            int current = getchar();\n            getchar();",
            ),
            source().replace("if (1) {", "if (current) {"),
            source().replace("putchar(putchar(current));", "putchar(i);"),
            source().replace(
                "        putchar(getchar());",
                "        putchar(getchar() + 1);",
            ),
            source().replace("for (int i = 0; i < 3; ++i)", "while (1)"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, candidate in enumerate(mutations):
                with self.subTest(index=index):
                    path = root / f"unsupported-{index}.c"
                    target = root / f"unsupported-{index}.malbolge"
                    path.write_text(candidate, encoding="utf-8")
                    result = self.compile(path, target)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
