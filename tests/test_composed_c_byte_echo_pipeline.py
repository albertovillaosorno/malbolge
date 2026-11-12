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
#   - Source-C local inputs composed with nested putchar returns.
# - Must-Not:
#   - Substitute host output for VM execution or assume EOF semantics.
# - Allows:
#   - Inputs: pinned Clang JSON, isolated guest binaries and byte streams.
#   - Outputs: independent runtime I/O oracles and closed refusals.
#   - Side effects: temporary compiler/VM fixtures only.
# - Split-When:
#   - General dynamic guest C call/dataflow owns this behavior.
# - Merge-When:
#   - Full source-C I/O trace regression subsumes composed calls.
# - Summary:
#   - Putchar return values must preserve the latest successful input.

"""Verify locally captured input through nested real guest output calls."""

from __future__ import annotations

import copy
import json
import random
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
FRONTEND_DIR = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin"
FRONTEND = FRONTEND_DIR / "malbolge-c-frontend"
ADAPTER = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT = ROOT / ".cache/rust/target/debug/malbolge_layout"
VM = ROOT / ".cache/rust/target/debug/malbolge"
INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"


class ComposedCByteEchoPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler and VM executables are not built")

    @staticmethod
    def source(body: str) -> str:
        return "#include <stdio.h>\nvoid emit(void) {\n" + body + "}\n"

    @staticmethod
    def build(source: Path, target: Path) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--capsule",
                "--output",
                str(target),
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=100,
        )

    @staticmethod
    def normalized(source: Path) -> dict[str, object]:
        result = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "composed-byte-return-v1",
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=20,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)

    def test_mixed_local_nested_and_direct_nested_guest_stream(self) -> None:
        cases = (
            (
                (
                    "    int first = getchar();\n"
                    "    putchar(putchar(first));\n"
                    "    putchar(first);\n"
                    "    putchar(putchar(getchar()));\n"
                    "    int second = getchar();\n"
                    "    putchar(putchar(putchar(second)));\n"
                    "    putchar(second);\n"
                ),
                (3, 2, 4),
            ),
            (
                (
                    "    putchar(putchar(getchar()));\n"
                    "    int z = getchar();\n"
                    "    putchar(putchar(z));\n"
                    "    putchar(putchar(z));\n"
                ),
                (2, 4),
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            for index, (body, repeats) in enumerate(cases):
                with self.subTest(index=index):
                    source = Path(folder) / f"composed-{index}.c"
                    target = Path(folder) / f"composed-{index}.malbolge"
                    source.write_text(self.source(body))
                    built = self.build(source, target)
                    self.assertEqual(built.returncode, 0, built.stderr)
                    self.assertTrue(target.is_file())
                    seeded = random.Random(0xC0A5E + index)
                    samples = [
                        b"\x00\xff\x80"[: len(repeats)],
                        b"A\n\xfe"[: len(repeats)],
                    ]
                    for _ in range(12):
                        sample = bytes(seeded.getrandbits(8) for _ in repeats)
                        samples.append(sample)

                    def run_guest(
                        data: bytes, *, target_path: Path = target
                    ) -> subprocess.CompletedProcess[bytes]:
                        return subprocess.run(
                            [
                                str(VM),
                                str(target_path),
                                "--input-stdin",
                                "--report-steps",
                            ],
                            input=data,
                            capture_output=True,
                            check=False,
                            timeout=40,
                        )

                    # Each VM process owns isolated machine and input state.
                    # Parallel samples preserve the independent oracle and
                    # avoid serial 15-trit memory initialization overhead.
                    with ThreadPoolExecutor(max_workers=7) as executor:
                        for data, vm in zip(
                            samples, executor.map(run_guest, samples), strict=True
                        ):
                            expected = bytes(
                                byte
                                for byte, count in zip(data, repeats)
                                for _ in range(count)
                            )
                            self.assertEqual(vm.returncode, 0, vm.stderr)
                            self.assertEqual(vm.stdout, expected)
                            steps = len(data) + len(expected) + 1
                            self.assertEqual(
                                vm.stderr, f"malbolge-steps-v1:{steps}\n".encode()
                            )

    def test_sixteen_nested_outputs_of_one_local_execute_in_guest(self) -> None:
        body = "    int x = getchar();\n    " + "putchar(" * 16 + "x" + ")" * 16 + ";\n"
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "deep-local.c"
            target = Path(folder) / "deep-local.malbolge"
            source.write_text(self.source(body))
            built = self.build(source, target)
            self.assertEqual(built.returncode, 0, built.stderr)
            self.assertTrue(target.is_file())

            def run_guest(byte: int) -> subprocess.CompletedProcess[bytes]:
                return subprocess.run(
                    [str(VM), str(target), "--input-stdin", "--report-steps"],
                    input=bytes((byte,)),
                    capture_output=True,
                    check=False,
                    timeout=40,
                )

            with ThreadPoolExecutor(max_workers=2) as executor:
                for byte, vm in zip(
                    (0, 255), executor.map(run_guest, (0, 255)), strict=True
                ):
                    self.assertEqual(vm.returncode, 0, vm.stderr)
                    self.assertEqual(vm.stdout, bytes((byte,)) * 16)
                    self.assertEqual(vm.stderr, b"malbolge-steps-v1:18\n")

    def test_rejected_source_never_publishes_guest(self) -> None:
        excessive_depth = "    int x = getchar();\n    "
        excessive_depth += "putchar(" * 17 + "x" + ")" * 17 + ";\n"
        cases = (
            "    int x = getchar();\n    putchar(putchar(x + 1));\n",
            (
                "    int x = getchar();\n    putchar(putchar(x));\n"
                "    int y = getchar();\n    putchar(putchar(x));\n"
            ),
            "    int x = getchar();\n    x = 7;\n    putchar(putchar(x));\n",
            "    int x = getchar();\n    putchar(putchar((unsigned)x));\n",
            (
                "    int x = getchar();\n    putchar(putchar(x));\n"
                "    putchar(putchar(EOF));\n"
            ),
            excessive_depth,
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            for index, body in enumerate(cases):
                with self.subTest(index=index):
                    source = Path(folder) / f"invalid-{index}.c"
                    target = Path(folder) / f"invalid-{index}.malbolge"
                    source.write_text(self.source(body))
                    result = self.build(source, target)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_local_nested_call_proofs_reject(self) -> None:
        body = "    int x = getchar();\n    putchar(putchar(putchar(x)));\n"
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "forged-base.c"
            source.write_text(self.source(body))
            original = self.normalized(source)
            changes = (
                (8, ("parent",), 1),
                (11, ("parent",), 2),
                (14, ("parent",), 2),
                (17, ("parent",), 8),
                (18, ("reference",), "x@999"),
                (8, ("span", "end", "column"), 99),
                (11, ("span", "begin", "byte"), 0),
                (14, ("span", "end", "byte"), 999),
                (17, ("span", "begin", "column"), 100),
                (18, ("span", "end", "column"), 999),
                (9, ("operation",), "integral-cast"),
                (15, ("reference",), "external:getchar"),
                (17, ("operation",), "integral-cast"),
                (14, ("type",), "u32"),
            )
            for index, (node_id, path, value) in enumerate(changes):
                with self.subTest(index=index):
                    forged = copy.deepcopy(original)
                    nodes = forged["nodes"]
                    assert isinstance(nodes, list)
                    node = next(n for n in nodes if n["id"] == node_id)
                    field = node
                    for name in path[:-1]:
                        field = field[name]
                    field[path[-1]] = value
                    target = Path(folder) / f"forged-{index}.malbolge"
                    forged_json = json.dumps(forged, separators=(",", ":"))
                    forged_bytes = forged_json.encode()
                    result = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(target),
                            "--capsule",
                        ],
                        input=forged_bytes,
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
