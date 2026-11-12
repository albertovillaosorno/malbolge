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
#   - Source-C nested comma operand guest-return and output-order proof.
# - Must-Not:
#   - Replay input on the host, drop comma writes or claim EOF support.
# - Allows:
#   - Inputs: pinned Clang AST and isolated binary stdin.
#   - Outputs: normative VM parity and fail-closed source/AST assertions.
#   - Side effects: disposable guest artifacts under .temp.
# - Split-When:
#   - General source-C expression lowering supersedes this bounded grammar.
# - Merge-When:
#   - Comma and standalone calls share a general guest return-value proof.
# - Summary:
#   - Nested successful putchar return bytes remain live in comma operands.

"""Run complete nested-comma C sources in the normative Malbolge guest."""

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

COMPOUND = (
    "    int first = getchar();\n"
    "    putchar(putchar(first));\n"
    "    putchar((getchar(), putchar(putchar(getchar()))));\n"
    "    getchar(), putchar(putchar(getchar())), getchar();\n"
    "    putchar(putchar(getchar()));\n"
)


class NestedCommaCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned Clang, JSON adapter, layout and VM are required")

    @staticmethod
    def source(body: str) -> str:
        return "#include <stdio.h>\nvoid stream(void) {\n" + body + "}\n"

    @staticmethod
    def compile(source: Path, target: Path) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [sys.executable, "-B", str(DRIVER), "--repository-tools", "--capsule",
             "--output", str(target), str(source)],
            capture_output=True,
            check=False,
            timeout=90,
        )

    @staticmethod
    def normalized(source: Path) -> dict[str, object]:
        proc = subprocess.run(
            [str(FRONTEND), "--guest-include", str(INCLUDE),
             "--resource-dir", str(RESOURCE), "--source-id", "nested-comma-v1",
             str(source)],
            capture_output=True,
            check=False,
            timeout=20,
        )
        if proc.returncode:
            raise AssertionError(proc.stderr)
        return json.loads(proc.stdout)

    @staticmethod
    def guest(target: Path, sample: bytes) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [str(VM), str(target), "--input-stdin", "--report-steps"],
            input=sample,
            capture_output=True,
            check=False,
            timeout=40,
        )

    def test_complete_source_preserves_seven_reads_and_nested_returns(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "stream.c"
            target = Path(folder) / "stream.malbolge"
            source.write_text(self.source(COMPOUND))
            compiled = self.compile(source, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            rng = random.Random(0xC0_11_2026)
            samples = [bytes([0, 255, 128, 1, 2, 3, 4]), b"ABCDEFG"]
            samples.extend(bytes(rng.getrandbits(8) for _ in range(7)) for _ in range(10))
            with ThreadPoolExecutor(max_workers=6) as executor:
                results = executor.map(lambda sample: self.guest(target, sample), samples)
                for sample, result in zip(samples, results, strict=True):
                    oracle = bytes((sample[0], sample[0], sample[2], sample[2],
                                    sample[2], sample[4], sample[4], sample[6],
                                    sample[6]))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, oracle)
                    self.assertEqual(result.stderr, b"malbolge-steps-v1:17\n")

    def test_nested_return_can_appear_before_or_after_final_comma_operand(self) -> None:
        variants = (
            ("putchar((putchar(putchar(getchar())), getchar()));", 2, (0, 0, 1)),
            ("putchar((getchar(), putchar(putchar(putchar(getchar())))));", 2,
             (1, 1, 1, 1)),
            ("getchar(), putchar(putchar(getchar())), getchar();", 3, (1, 1)),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            for index, (statement, reads, output_positions) in enumerate(variants):
                with self.subTest(index=index):
                    source = Path(folder) / f"variant-{index}.c"
                    target = Path(folder) / f"variant-{index}.malbolge"
                    source.write_text(self.source(f"    {statement}\n"))
                    result = self.compile(source, target)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    sample = bytes([255, 0, 128][:reads])
                    guest = self.guest(target, sample)
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(guest.stdout, bytes(sample[p] for p in output_positions))
                    self.assertEqual(
                        guest.stderr,
                        f"malbolge-steps-v1:{reads + len(output_positions) + 1}\n".encode(),
                    )

    def test_sixteen_nested_comma_writes_bounded_and_seventeen_refused(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            for depth in (16, 17):
                with self.subTest(depth=depth):
                    source = Path(folder) / f"nested-{depth}.c"
                    target = Path(folder) / f"nested-{depth}.malbolge"
                    nested = "putchar(" * depth + "getchar()" + ")" * depth
                    source.write_text(self.source(f"    putchar((getchar(), {nested}));\n"))
                    compiled = self.compile(source, target)
                    if depth == 17:
                        self.assertNotEqual(compiled.returncode, 0)
                        self.assertFalse(target.exists())
                    else:
                        self.assertEqual(compiled.returncode, 0, compiled.stderr)
                        guest = self.guest(target, b"\xff\x00")
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        self.assertEqual(guest.stdout, bytes([0]) * (depth + 1))
                        self.assertEqual(guest.stderr, b"malbolge-steps-v1:20\n")

    def test_unsupported_nested_effects_refuse_publication(self) -> None:
        invalid = (
            "putchar((getchar(), putchar(putchar(65))))",
            "putchar((getchar(), putchar(putchar(getchar() + 1))))",
            "putchar((getchar(), (putchar(putchar(getchar())))))",
            "putchar((putchar(putchar(getchar())), getchar() + 1))",
            "putchar((putchar((putchar(getchar()))), getchar()))",
            "putchar((getchar(), putchar((int)putchar(getchar()))))",
            "getchar(), putchar(putchar(65)), getchar()",
            "getchar(), putchar((putchar(getchar()))), getchar()",
            "getchar(), putchar(putchar(getchar())), getchar() + 1",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            for index, statement in enumerate(invalid):
                with self.subTest(index=index):
                    source = Path(folder) / f"invalid-{index}.c"
                    target = Path(folder) / f"invalid-{index}.malbolge"
                    source.write_text(self.source(f"    {statement};\n"))
                    compiled = self.compile(source, target)
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_nested_comma_metadata_cannot_publish(self) -> None:
        changes = (
            (20, ("parent",), 2),
            (20, ("operation",), "+"),
            (20, ("span", "end", "byte"), 99),
            (21, ("reference",), "external:putchar"),
            (24, ("parent",), 19),
            (24, ("span", "begin", "column"), 1),
            (25, ("operation",), "lvalue-to-rvalue"),
            (27, ("parent",), 20),
            (27, ("span", "end", "byte"), 1),
            (30, ("parent",), 24),
            (30, ("span", "begin", "column"), 0),
            (33, ("parent",), 19),
            (34, ("parent",), 2),
            (38, ("reference",), "external:getchar"),
            (41, ("span", "end", "column"), 1),
            (44, ("parent",), 38),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "source.c"
            source.write_text(self.source(COMPOUND))
            original = self.normalized(source)
            for index, (node_id, path, value) in enumerate(changes):
                with self.subTest(index=index):
                    forged = copy.deepcopy(original)
                    nodes = forged["nodes"]
                    assert isinstance(nodes, list)
                    node = next(item for item in nodes if item["id"] == node_id)
                    field = node
                    for key in path[:-1]:
                        field = field[key]
                    field[path[-1]] = value
                    target = Path(folder) / f"forged-{index}.malbolge"
                    result = subprocess.run(
                        [str(ADAPTER), "--layout-backend", str(LAYOUT),
                         "--output", str(target), "--capsule"],
                        input=json.dumps(forged, separators=(",", ":")).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
