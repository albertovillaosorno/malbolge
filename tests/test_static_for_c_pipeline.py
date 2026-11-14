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
#   - Whole-C bounded counted-loop source authentication and guest byte I/O.
# - Must-Not:
#   - Claim runtime guest loops or substitute host I/O for VM effects.
# - Allows:
#   - Inputs: pinned normalized Clang and isolated binary input streams.
#   - Outputs: actual VM oracle parity and fail-closed source refusals.
#   - Side effects: temporary compilation artifacts only.
# - Split-When:
#   - Dynamic C loop induction replaces compile-time bounded unrolling.
# - Merge-When:
#   - A general verified C control-flow compiler owns this loop subset.
# - Summary:
#   - Replays source-checked finite for loops as actual guest effects.

"""Counted C loops must replay actual guest reads and writes in order."""

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


def source(count: int = 3, *, loop: str | None = None, body: str | None = None) -> str:
    header = loop or f"for (int i = 0; i < {count}; ++i)"
    statements = body or (
        "        putchar(getchar());\n"
        "        getchar();\n"
        "        putchar(putchar(getchar()));\n"
    )
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        f"    {header} {{\n"
        f"{statements}"
        "    }\n"
        "    if (1) {\n"
        "        putchar(getchar());\n"
        "    } else {\n"
        "        getchar();\n"
        "    }\n"
        "}\n"
    )


class StaticForCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(p.is_file() for p in (FRONTEND, ADAPTER, LAYOUT, VM)):
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
            timeout=90,
        )

    @staticmethod
    def vm(target: Path, data: bytes) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [str(VM), str(target), "--input-stdin", "--report-steps"],
            input=data,
            capture_output=True,
            check=False,
            timeout=35,
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
                "counted-for",
                str(path),
            ],
            capture_output=True,
            check=False,
            timeout=20,
        )
        if result.returncode:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)

    def test_counted_loop_with_discard_branch_and_nested_writes(self) -> None:
        rng = random.Random(0xF0510)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for count in (1, 3, 4):
                with self.subTest(count=count):
                    path = root / f"count-{count}.c"
                    target = root / f"count-{count}.malbolge"
                    path.write_text(source(count))
                    built = self.compile(path, target)
                    self.assertEqual(built.returncode, 0, built.stderr)
                    for data in (
                        bytes((0, 255, 128, 1) * (count + 1)),
                        bytes(rng.getrandbits(8) for _ in range(3 * count + 1)),
                    ):
                        result = self.vm(target, data)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        expected = bytearray()
                        for index in range(count):
                            expected.append(data[3 * index])
                            expected.extend((data[3 * index + 2],) * 2)
                        expected.append(data[3 * count])
                        self.assertEqual(result.stdout, bytes(expected))
                        self.assertEqual(
                            result.stderr,
                            f"malbolge-steps-v1:{6 * count + 3}\n".encode(),
                        )

    def test_static_branch_inside_counted_loop_preserves_order(self) -> None:
        body = (
            "        if (0) {\n"
            "            getchar();\n"
            "        } else {\n"
            "            putchar(getchar());\n"
            "        }\n"
            "        putchar(getchar());\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "nested-if-for.c"
            target = root / "nested-if-for.malbolge"
            path.write_text(source(body=body))
            compiled = self.compile(path, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            data = bytes((0, 255, 128, 1, 5, 254, 64))
            guest = self.vm(target, data)
            self.assertEqual(guest.returncode, 0, guest.stderr)
            self.assertEqual(guest.stdout, data)
            self.assertEqual(guest.stderr, b"malbolge-steps-v1:15\n")

    def test_sixteen_iterations_replay_guest_input_without_byte_fixture(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "sixteen.c"
            target = root / "sixteen.malbolge"
            path.write_text(source(16, body="        putchar(getchar());\n"))
            built = self.compile(path, target)
            self.assertEqual(built.returncode, 0, built.stderr)
            data = bytes(
                (0, 255, 1, 128, 254, 7, 42, 63, 97, 13, 201, 202, 3, 6, 9, 127, 4)
            )
            guest = self.vm(target, data)
            self.assertEqual(guest.returncode, 0, guest.stderr)
            self.assertEqual(guest.stdout, data)
            self.assertEqual(guest.stderr, b"malbolge-steps-v1:35\n")

    def test_unsupported_loop_shapes_do_not_publish(self) -> None:
        # Starts, inclusive bounds, postfix/compound increments and selected
        # break/continue already have independent positive compiler tests.
        # Keep only genuinely unproved source and effect shapes here.
        bad_headers = (
            "for (int i = 0; i < 17; ++i)",
            "for (int i=0; i<3; ++i)",
            "for (int i = 0; i < 3; --i)",
            "for (int i = 0; i < 3; ++i, ++i)",
            "for (int i = 4; i != 3; ++i)",
        )
        bad_bodies = (
            "        putchar(i);\n",
            "        putchar(getchar() + 1);\n",
            "        ++i;\n        putchar(getchar());\n",
            "        if (getchar()) putchar(getchar());\n",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, candidate in enumerate(
                [source(loop=h) for h in bad_headers]
                + [source(body=b) for b in bad_bodies]
            ):
                with self.subTest(index=index):
                    path = root / f"bad-{index}.c"
                    target = root / f"bad-{index}.malbolge"
                    path.write_text(candidate)
                    built = self.compile(path, target)
                    self.assertNotEqual(built.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_loop_ancestry_refuses_publication(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "original.c"
            path.write_text(source())
            original = self.normalized(path)
            nodes = original["nodes"]
            loop = next(n for n in nodes if n["kind"] == "for-statement")
            init = next(n for n in nodes if n["kind"] == "variable-declaration")
            bound = next(
                n
                for n in nodes
                if n["kind"] == "integer-literal" and n.get("literal") == "3"
            )
            increment = next(
                n
                for n in nodes
                if n["kind"] == "unary-expression" and n.get("operation") == "++"
            )
            loop_body = next(
                n
                for n in nodes
                if n["kind"] == "compound-statement" and n["parent"] == loop["id"]
            )
            changes = (
                (loop["id"], "span.end.line", 3),
                (loop["id"], "span.begin.column", 6),
                (init["id"], "reference", "i@0"),
                (init["id"], "storage_duration", "static"),
                (bound["id"], "constant_integer", "4"),
                (bound["id"], "parent", 2),
                (increment["id"], "operation", "--"),
                (increment["id"], "span.begin.byte", 0),
                (loop_body["id"], "parent", 2),
                (loop_body["id"], "span.end.column", 1),
            )
            for index, (node_id, field, value) in enumerate(changes):
                with self.subTest(index=index, field=field):
                    forged = copy.deepcopy(original)
                    node = next(n for n in forged["nodes"] if n["id"] == node_id)
                    slot = node
                    for key in field.split(".")[:-1]:
                        slot = slot[key]
                    slot[field.split(".")[-1]] = value
                    target = root / f"forged-{index}.malbolge"
                    proc = subprocess.run(
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
                    self.assertNotEqual(proc.returncode, 0)
                    self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
