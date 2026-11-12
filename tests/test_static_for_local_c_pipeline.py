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
#   - Guest VM parity for a source-proven counted loop with a fresh C local.
# - Must-Not:
#   - Simulate guest byte I/O on the compiler host or claim guest C storage.
# - Allows:
#   - Inputs: pinned Clang JSON and binary guest stdin.
#   - Outputs: exact guest bytes/step counts and forged-AST refusals.
#   - Side effects: isolated temporary C/target files only.
# - Split-When:
#   - General guest C loop/local lowering subsumes this finite slice.
# - Merge-When:
#   - Shared compiler loop acceptance covers per-iteration local identities.
# - Summary:
#   - A new local is read on every unrolled iteration, never reused across it.

"""Execute source C with per-iteration fresh local byte inputs in Malbolge."""

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


def source(count: int = 3, *, statements: str | None = None) -> str:
    effects = statements or (
        "        int current = getchar();\n"
        "        putchar(current);\n"
        "        putchar(putchar(current));\n"
    )
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        f"    for (int i = 0; i < {count}; ++i) {{\n"
        f"{effects}"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class StaticForLocalPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(tool.is_file() for tool in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C frontend, adapter, layout and VM required")

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
            timeout=60,
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
                "loop-local",
                str(path),
            ],
            capture_output=True,
            check=False,
            timeout=15,
        )
        if result.returncode:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)

    @staticmethod
    def guest(path: Path, data: bytes) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [str(VM), str(path), "--input-stdin", "--report-steps"],
            input=data,
            capture_output=True,
            check=False,
            timeout=35,
        )

    def test_local_is_fresh_for_each_counted_guest_iteration(self) -> None:
        rng = random.Random(0xF091A)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for count in (1, 3, 4):
                with self.subTest(count=count):
                    path = root / f"local-{count}.c"
                    target = root / f"local-{count}.malbolge"
                    path.write_text(source(count), encoding="utf-8")
                    compiled = self.compile(path, target)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    for data in (
                        bytes([0, 255, 128, 1, 64][: count + 1]),
                        bytes(rng.randrange(256) for _ in range(count + 1)),
                    ):
                        guest = self.guest(target, data)
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        expected = b"".join(bytes((byte,)) * 3 for byte in data[:count])
                        expected += data[count : count + 1]
                        self.assertEqual(guest.stdout, expected)
                        self.assertEqual(
                            guest.stderr,
                            f"malbolge-steps-v1:{4 * count + 3}\n".encode(),
                        )

    def test_two_live_local_phases_and_selected_nested_branch(self) -> None:
        statements = (
            "        int first = getchar();\n"
            "        putchar(first);\n"
            "        int second = getchar();\n"
            "        if (1) {\n"
            "            putchar(putchar(second));\n"
            "        } else {\n"
            "            getchar();\n"
            "        }\n"
            "        putchar(second);\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "two-phases.c"
            target = root / "two-phases.malbolge"
            path.write_text(source(2, statements=statements), encoding="utf-8")
            compiled = self.compile(path, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255, 128, 1, 15)),
                bytes((3, 9, 0, 255, 42)),
            ):
                guest = self.guest(target, data)
                self.assertEqual(guest.returncode, 0, guest.stderr)
                expected = (
                    bytes((data[0],))
                    + bytes((data[1],)) * 3
                    + bytes((data[2],))
                    + bytes((data[3],)) * 3
                    + data[4:5]
                )
                self.assertEqual(guest.stdout, expected)
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:15\n")

    def test_branch_scoped_local_inside_counted_loop(self) -> None:
        statements = (
            "        if (1) {\n"
            "            int chosen = getchar();\n"
            "            putchar(putchar(chosen));\n"
            "        } else {\n"
            "            getchar();\n"
            "        }\n"
            "        putchar(getchar());\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "branch-local.c"
            target = root / "branch-local.malbolge"
            path.write_text(source(2, statements=statements), encoding="utf-8")
            compiled = self.compile(path, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (bytes((0, 255, 1, 128, 17)), bytes((7, 16, 33, 9, 65))):
                guest = self.guest(target, data)
                self.assertEqual(guest.returncode, 0, guest.stderr)
                expected = bytes((data[0],)) * 2 + data[1:2]
                expected += bytes((data[2],)) * 2 + data[3:5]
                self.assertEqual(guest.stdout, expected)
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:13\n")

    def test_inactive_branch_local_and_selected_else_local(self) -> None:
        statements = (
            "        if (0) {\n"
            "            int skipped = getchar();\n"
            "            putchar(skipped);\n"
            "        } else {\n"
            "            int selected = getchar();\n"
            "            putchar(putchar(selected));\n"
            "        }\n"
            "        putchar(getchar());\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "else-local.c"
            target = root / "else-local.malbolge"
            path.write_text(source(2, statements=statements), encoding="utf-8")
            compiled = self.compile(path, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (bytes((255, 0, 128, 1, 64)), bytes((3, 9, 6, 2, 7))):
                guest = self.guest(target, data)
                self.assertEqual(guest.returncode, 0, guest.stderr)
                expected = bytes((data[0],)) * 2 + data[1:2]
                expected += bytes((data[2],)) * 2 + data[3:5]
                self.assertEqual(guest.stdout, expected)
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:13\n")

    def test_nested_local_stale_input_and_forged_scope_refuse(self) -> None:
        statements = (
            "        if (1) {\n"
            "            int chosen = getchar();\n"
            "            putchar(putchar(chosen));\n"
            "        } else {\n"
            "            getchar();\n"
            "        }\n"
            "        putchar(getchar());\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "branch-local.c"
            path.write_text(source(2, statements=statements), encoding="utf-8")
            normalized = self.normalized(path)
            nodes = normalized["nodes"]
            declaration = next(
                n
                for n in nodes
                if n["kind"] == "variable-declaration" and n.get("name") == "chosen"
            )
            declaration_id = declaration["id"]
            for node_id, field, replacement in (
                (declaration_id - 1, "parent", 3),
                (declaration_id, "reference", "chosen@1"),
                (declaration_id + 1, "parent", 3),
            ):
                with self.subTest(node_id=node_id, field=field):
                    altered = copy.deepcopy(normalized)
                    changed = next(n for n in altered["nodes"] if n["id"] == node_id)
                    changed[field] = replacement
                    target = root / f"forged-scope-{node_id}.malbolge"
                    result = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(target),
                            "--capsule",
                        ],
                        input=json.dumps(altered).encode(),
                        capture_output=True,
                        check=False,
                        timeout=20,
                    )
                    self.assertNotEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(target.exists())
            invalid = source(
                2,
                statements=statements.replace(
                    "            putchar(putchar(chosen));\n",
                    "            getchar();\n            putchar(putchar(chosen));\n",
                ),
            )
            path.write_text(invalid, encoding="utf-8")
            target = root / "stale-branch.malbolge"
            result = self.compile(path, target)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(target.exists())

    def test_local_after_new_input_refuses_stale_guest_replay(self) -> None:
        mutations = (
            (
                "        int current = getchar();\n"
                "        getchar();\n"
                "        putchar(current);\n"
            ),
            (
                "        int current = getchar();\n"
                "        current++;\n"
                "        putchar(current);\n"
            ),
            "        int current = getchar();\n        putchar(current + 1);\n",
            "        int current = getchar();\n        putchar(i);\n",
            (
                "        int first = getchar();\n"
                "        int second = getchar();\n"
                "        putchar(first);\n"
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, statements in enumerate(mutations):
                with self.subTest(index=index):
                    path = root / f"invalid-{index}.c"
                    target = root / f"invalid-{index}.malbolge"
                    path.write_text(source(statements=statements), encoding="utf-8")
                    compiled = self.compile(path, target)
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_local_clang_ancestry_refuses_publication(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "loop-local.c"
            path.write_text(source(), encoding="utf-8")
            normalized = self.normalized(path)
            for node_id, field, replacement in (
                (14, "parent", 2),
                (15, "reference", "current@1"),
                (16, "parent", 14),
                (19, "parent", 2),
                (23, "reference", "i@52"),
                (24, "parent", 3),
                (31, "reference", "current@1"),
            ):
                with self.subTest(node_id=node_id, field=field):
                    altered = copy.deepcopy(normalized)
                    node = next(
                        node for node in altered["nodes"] if node["id"] == node_id
                    )
                    node[field] = replacement
                    target = root / f"forged-{node_id}-{field}.malbolge"
                    result = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(target),
                            "--capsule",
                        ],
                        input=json.dumps(altered).encode(),
                        capture_output=True,
                        check=False,
                        timeout=20,
                    )
                    self.assertNotEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
