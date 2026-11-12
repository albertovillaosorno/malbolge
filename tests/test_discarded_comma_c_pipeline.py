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
#   - Source-proven standalone C comma expressions with runtime byte effects.
# - Must-Not:
#   - Elide reads, fabricate guest output or claim EOF parity.
# - Allows:
#   - Inputs: pinned Clang normalized C and successful binary stdin.
#   - Outputs: independent runtime output/steps and refusal assertions.
#   - Side effects: isolated temporary test files only.
# - Split-When:
#   - General dynamic guest C expression evaluation replaces this grammar.
# - Merge-When:
#   - Comma expression lowering handles arbitrary source-proven effects.
# - Summary:
#   - Discarded comma operands must execute in source order in the VM.

"""End-to-end guest execution for source-C discarded comma input chains."""

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
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
ADAPTER = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT = ROOT / ".cache/rust/target/debug/malbolge_layout"
VM = ROOT / ".cache/rust/target/debug/malbolge"
INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"

BODY = (
    "    int first = getchar();\n"
    "    putchar(putchar(first));\n"
    "    getchar(), getchar(), getchar();\n"
    "    putchar((getchar(), getchar()));\n"
    "    int last = getchar();\n"
    "    putchar(putchar(last));\n"
)


class DiscardedCommaCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler and VM executables are not built")

    @staticmethod
    def source(body: str) -> str:
        return "#include <stdio.h>\nvoid stream(void) {\n" + body + "}\n"

    @classmethod
    def compile_source(
        cls, source: Path, target: Path
    ) -> subprocess.CompletedProcess[bytes]:
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
            timeout=90,
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
                "standalone-comma-v1",
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=20,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)

    def test_complete_seven_input_five_output_guest(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "comma-sequence.c"
            target = Path(folder) / "comma-sequence.malbolge"
            source.write_text(self.source(BODY))
            built = self.compile_source(source, target)
            self.assertEqual(built.returncode, 0, built.stderr)
            self.assertTrue(target.is_file())

            rng = random.Random(0xC0A7_2026)
            samples = [b"\x00\xff\x80\x01\n\x7f\xfe", b"ABCDEFG"]
            samples += [bytes(rng.getrandbits(8) for _ in range(7)) for _ in range(10)]

            def run_guest(data: bytes) -> subprocess.CompletedProcess[bytes]:
                return subprocess.run(
                    [str(VM), str(target), "--input-stdin", "--report-steps"],
                    input=data,
                    capture_output=True,
                    check=False,
                    timeout=40,
                )

            with ThreadPoolExecutor(max_workers=6) as executor:
                for data, result in zip(
                    samples, executor.map(run_guest, samples), strict=True
                ):
                    # Three discarded reads are not visible as output;
                    # the comma argument discards the next read as well.
                    first, _a, _b, _c, _d, selected, last = data
                    oracle = bytes((first, first, selected, last, last))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, oracle)
                    self.assertEqual(result.stderr, b"malbolge-steps-v1:13\n")

    def test_standalone_comma_input_only_executes_every_read(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "only-reads.c"
            target = Path(folder) / "only-reads.malbolge"
            source.write_text(self.source("    getchar(), getchar(), getchar();\n"))
            built = self.compile_source(source, target)
            self.assertEqual(built.returncode, 0, built.stderr)
            vm = subprocess.run(
                [str(VM), str(target), "--input-stdin", "--report-steps"],
                input=b"\x00\xff\x80",
                capture_output=True,
                check=False,
                timeout=40,
            )
            self.assertEqual(vm.returncode, 0, vm.stderr)
            self.assertEqual(vm.stdout, b"")
            self.assertEqual(vm.stderr, b"malbolge-steps-v1:4\n")

    def test_bounded_long_comma_chain_and_excess_refusal(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            for count in (2, 16, 17):
                with self.subTest(reads=count):
                    source = Path(folder) / f"chain-{count}.c"
                    target = Path(folder) / f"chain-{count}.malbolge"
                    expression = ", ".join("getchar()" for _ in range(count))
                    source.write_text(self.source(f"    {expression};\n"))
                    compiled = self.compile_source(source, target)
                    if count == 17:
                        self.assertNotEqual(compiled.returncode, 0)
                        self.assertFalse(target.exists())
                        continue
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    vm = subprocess.run(
                        [str(VM), str(target), "--input-stdin", "--report-steps"],
                        input=bytes(range(count)),
                        capture_output=True,
                        check=False,
                        timeout=40,
                    )
                    self.assertEqual(vm.returncode, 0, vm.stderr)
                    self.assertEqual(vm.stdout, b"")
                    self.assertEqual(
                        vm.stderr,
                        f"malbolge-steps-v1:{count + 1}\n".encode(),
                    )

    def test_unsupported_comma_effects_refuse_publication(self) -> None:
        invalid = (
            "    getchar(), putchar(65);\n",
            "    putchar(65), getchar();\n",
            "    getchar(), 42;\n",
            "    getchar() + getchar();\n",
            "    getchar(), getc(stdin);\n",
            "    (getchar(), getchar());\n",
            "    getchar(), (void)getchar();\n",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            for index, fragment in enumerate(invalid):
                with self.subTest(index=index):
                    source = Path(folder) / f"invalid-{index}.c"
                    target = Path(folder) / f"invalid-{index}.malbolge"
                    source.write_text(
                        self.source(
                            BODY.replace(
                                "    getchar(), getchar(), getchar();\n", fragment
                            )
                        )
                    )
                    result = self.compile_source(source, target)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_comma_ancestry_refuses_publication(self) -> None:
        changes = (
            (16, ("operation",), "+"),
            (16, ("parent",), 1),
            (16, ("type",), "u32"),
            (16, ("span", "end", "column"), 100),
            (17, ("parent",), 2),
            (17, ("operation",), "*"),
            (17, ("span", "begin", "byte"), 100),
            (18, ("parent",), 16),
            (18, ("reference",), "external:putchar"),
            (20, ("parent",), 16),
            (20, ("span", "begin", "column"), 4),
            (23, ("parent",), 16),
            (23, ("span", "end", "byte"), 1),
            (24, ("operation",), "integral-cast"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "original.c"
            source.write_text(self.source(BODY))
            original = self.normalized(source)
            for index, (node_id, path, value) in enumerate(changes):
                with self.subTest(index=index):
                    forged = copy.deepcopy(original)
                    nodes = forged["nodes"]
                    assert isinstance(nodes, list)
                    node = next(n for n in nodes if n["id"] == node_id)
                    field = node
                    for key in path[:-1]:
                        field = field[key]
                    field[path[-1]] = value
                    target = Path(folder) / f"forged-{index}.malbolge"
                    result = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(target),
                            "--capsule",
                        ],
                        input=json.dumps(forged, separators=(",", ":")).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
