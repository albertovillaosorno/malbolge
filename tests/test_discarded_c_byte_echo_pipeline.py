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
#   - Source-C discarded runtime input in composed live byte streams.
# - Must-Not:
#   - Drop a guest read, fabricate output or claim C EOF parity.
# - Allows:
#   - Inputs: isolated pinned Clang artifacts and successful binary bytes.
#   - Outputs: independent guest output, step and refusal evidence.
#   - Side effects: temporary test artifacts only.
# - Split-When:
#   - General guest-side C expression evaluation subsumes this slice.
# - Merge-When:
#   - Full C I/O effect lowering proves discarded evaluations.
# - Summary:
#   - Unused input must consume exactly one byte in guest evaluation order.

"""Exercise discarded real guest input inside a complete C I/O program."""

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

COMMA_BODY = (
    "    int first = getchar();\n"
    "    putchar(first);\n"
    "    putchar((getchar(), getchar()));\n"
    "    int last = getchar();\n"
    "    putchar(putchar(last));\n"
)

BODY = (
    "    int first = getchar();\n"
    "    putchar(first);\n"
    "    getchar();\n"
    "    putchar(putchar(getchar()));\n"
    "    int last = getchar();\n"
    "    putchar(last);\n"
    "    putchar(last);\n"
)


class DiscardedCByteEchoPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler and VM executables are not built")

    @staticmethod
    def source(body: str) -> str:
        return "#include <stdio.h>\nvoid stream(void) {\n" + body + "}\n"

    @classmethod
    def build(cls, source: Path, target: Path) -> subprocess.CompletedProcess[bytes]:
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
                "discarded-byte-v1",
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=20,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)

    def test_complete_source_consumes_discarded_byte_in_guest(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "discarded.c"
            target = Path(folder) / "discarded.malbolge"
            source.write_text(self.source(BODY))
            compiled = self.build(source, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(target.is_file())
            random_bytes = random.Random(0xD15CA2D)
            samples = [b"\x00\xff\x80\x01", b"A\n\xfeZ"]
            samples += [
                bytes(random_bytes.getrandbits(8) for _ in range(4)) for _ in range(12)
            ]

            def run_guest(data: bytes) -> subprocess.CompletedProcess[bytes]:
                return subprocess.run(
                    [str(VM), str(target), "--input-stdin", "--report-steps"],
                    input=data,
                    capture_output=True,
                    check=False,
                    timeout=40,
                )

            with ThreadPoolExecutor(max_workers=7) as executor:
                for data, result in zip(
                    samples, executor.map(run_guest, samples), strict=True
                ):
                    # Byte 1 is read but intentionally has no output.
                    first, _discarded, nested, last = data
                    oracle = bytes((first, nested, nested, last, last))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, oracle)
                    self.assertEqual(result.stderr, b"malbolge-steps-v1:10\n")

    def test_comma_argument_sequences_two_real_reads(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "comma.c"
            target = Path(folder) / "comma.malbolge"
            source.write_text(self.source(COMMA_BODY))
            compiled = self.build(source, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            seeded = random.Random(0xC0AAB1)
            samples = [b"\x00\xff\x80\x01", b"A\n\xfeZ"]
            samples += [
                bytes(seeded.getrandbits(8) for _ in range(4)) for _ in range(8)
            ]

            def run_guest(data: bytes) -> subprocess.CompletedProcess[bytes]:
                return subprocess.run(
                    [str(VM), str(target), "--input-stdin", "--report-steps"],
                    input=data,
                    capture_output=True,
                    check=False,
                    timeout=40,
                )

            with ThreadPoolExecutor(max_workers=7) as executor:
                for data, vm in zip(
                    samples, executor.map(run_guest, samples), strict=True
                ):
                    first, _discarded, selected, last = data
                    self.assertEqual(vm.returncode, 0, vm.stderr)
                    self.assertEqual(vm.stdout, bytes((first, selected, last, last)))
                    self.assertEqual(vm.stderr, b"malbolge-steps-v1:9\n")

    def test_effectful_input_only_source_really_executes_guest_reads(self) -> None:
        body = "    getchar();\n    getchar();\n"
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "consume.c"
            target = Path(folder) / "consume.malbolge"
            source.write_text(self.source(body))
            compiled = self.build(source, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (b"\x00\xff", b"\xfe\x01"):
                vm = subprocess.run(
                    [str(VM), str(target), "--input-stdin", "--report-steps"],
                    input=data,
                    capture_output=True,
                    check=False,
                    timeout=40,
                )
                self.assertEqual(vm.returncode, 0, vm.stderr)
                self.assertEqual(vm.stdout, b"")
                self.assertEqual(vm.stderr, b"malbolge-steps-v1:3\n")

    def test_comma_argument_mutations_refuse_publication(self) -> None:
        changes = (
            (16, ("parent",), 2),
            (16, ("kind",), "cast-expression"),
            (16, ("span", "begin", "byte"), 97),
            (17, ("parent",), 13),
            (17, ("operation",), "+"),
            (17, ("span", "end", "column"), 98),
            (18, ("parent",), 16),
            (18, ("span", "end", "byte"), 109),
            (20, ("reference",), "external:putchar"),
            (21, ("parent",), 18),
            (21, ("span", "begin", "column"), 24),
            (23, ("type",), "ptr(fn()->i32)"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "comma-base.c"
            source.write_text(self.source(COMMA_BODY))
            original = self.normalized(source)
            for i, (node_id, path, value) in enumerate(changes):
                with self.subTest(index=i):
                    forged = copy.deepcopy(original)
                    nodes = forged["nodes"]
                    assert isinstance(nodes, list)
                    node = next(n for n in nodes if n["id"] == node_id)
                    field = node
                    for key in path[:-1]:
                        field = field[key]
                    field[path[-1]] = value
                    target = Path(folder) / f"comma-forged-{i}.malbolge"
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

    def test_invalid_c_effect_sequences_do_not_publish(self) -> None:
        cases = (
            BODY.replace("    getchar();\n", "    getchar() + 1;\n"),
            BODY.replace("    getchar();\n", "    getchar(), putchar(65);\n"),
            BODY.replace("    getchar();\n", "    getc(stdin);\n"),
            BODY.replace("    getchar();\n", "    first = getchar();\n"),
            BODY.replace("    putchar(putchar(getchar()));\n", "    putchar(first);\n"),
            BODY.replace("    getchar();\n", "    (void)42;\n"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            for i, body in enumerate(cases):
                with self.subTest(index=i):
                    source = Path(folder) / f"unsupported-{i}.c"
                    target = Path(folder) / f"unsupported-{i}.malbolge"
                    source.write_text(self.source(body))
                    result = self.build(source, target)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_discarded_call_proof_does_not_publish(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "original.c"
            source.write_text(self.source(BODY))
            original = self.normalized(source)
            changes = (
                (13, ("parent",), 1),
                (13, ("reference",), "external:putchar"),
                (13, ("type",), "u32"),
                (13, ("span", "end", "byte"), 98),
                (13, ("span", "begin", "column"), 6),
                (14, ("parent",), 2),
                (14, ("operation",), "integral-cast"),
                (14, ("span", "end", "column"), 99),
                (15, ("parent",), 13),
                (15, ("reference",), "external:putchar"),
                (15, ("span", "begin", "byte"), 91),
                (15, ("name",), "getchar"),
            )
            for i, (node_id, path, value) in enumerate(changes):
                with self.subTest(index=i):
                    forged = copy.deepcopy(original)
                    nodes = forged["nodes"]
                    assert isinstance(nodes, list)
                    node = next(n for n in nodes if n["id"] == node_id)
                    field = node
                    for name in path[:-1]:
                        field = field[name]
                    field[path[-1]] = value
                    target = Path(folder) / f"forged-{i}.malbolge"
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
