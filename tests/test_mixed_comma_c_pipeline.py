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
#   - Source-C comma operand guest I/O effect conformance.
# - Must-Not:
#   - Invent guest output, discard C effects or assume EOF parity.
# - Allows:
#   - Inputs: pinned Clang JSON and independent binary stdin samples.
#   - Outputs: normative VM parity, source and AST refusal checks.
#   - Side effects: temporary local artifacts only.
# - Split-When:
#   - General guest C expression control replaces this bounded grammar.
# - Merge-When:
#   - All comma operand forms share a complete effect verifier.
# - Summary:
#   - Discarded successful putchar calls are still observable writes.

"""Execute full source-C mixed comma read/write programs in real Malbolge."""

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

MIXED = (
    "    int first = getchar();\n"
    "    putchar(putchar(first));\n"
    "    getchar(), putchar(getchar()), getchar();\n"
    "    putchar(putchar(getchar()));\n"
)


class MixedCommaCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler and normative VM are not built")

    @staticmethod
    def source(body: str) -> str:
        return "#include <stdio.h>\nvoid stream(void) {\n" + body + "}\n"

    @staticmethod
    def compile(source: Path, target: Path) -> subprocess.CompletedProcess[bytes]:
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
    def frontend(source: Path) -> dict[str, object]:
        result = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "mixed-comma-v1",
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=20,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)

    @staticmethod
    def run_guest(target: Path, stdin: bytes) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [str(VM), str(target), "--input-stdin", "--report-steps"],
            input=stdin,
            capture_output=True,
            check=False,
            timeout=40,
        )

    def test_complete_mixed_source_with_local_and_nested_return(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "mixed.c"
            target = Path(folder) / "mixed.malbolge"
            source.write_text(self.source(MIXED))
            compiled = self.compile(source, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(target.is_file())

            rng = random.Random(0xC0A5_2026)
            samples = [b"\x00\xff\x80\x01\x7f", b"ABCDE"]
            samples += [bytes(rng.getrandbits(8) for _ in range(5)) for _ in range(10)]
            with ThreadPoolExecutor(max_workers=6) as executor:
                results = executor.map(
                    lambda data: self.run_guest(target, data), samples
                )
                for stdin, result in zip(samples, results, strict=True):
                    first, _discarded, middle, _last, final = stdin
                    oracle = bytes((first, first, middle, final, final))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, oracle)
                    self.assertEqual(result.stderr, b"malbolge-steps-v1:11\n")

    def test_mixed_call_boundaries_and_ordered_write_effects(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            for count in (2, 4, 16, 17):
                with self.subTest(count=count):
                    source = Path(folder) / f"mixed-{count}.c"
                    target = Path(folder) / f"mixed-{count}.malbolge"
                    parts = [
                        "putchar(getchar())" if i % 2 else "getchar()"
                        for i in range(count)
                    ]
                    source.write_text(self.source("    " + ", ".join(parts) + ";\n"))
                    result = self.compile(source, target)
                    if count == 17:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertFalse(target.exists())
                        continue
                    self.assertEqual(result.returncode, 0, result.stderr)
                    stdin = bytes(range(count))
                    guest = self.run_guest(target, stdin)
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(guest.stdout, stdin[1::2])
                    steps = count + count // 2 + 1
                    self.assertEqual(
                        guest.stderr, f"malbolge-steps-v1:{steps}\n".encode()
                    )

    def test_unsupported_effects_refuse_target_publication(self) -> None:
        invalid = (
            "getchar(), putchar(65), getchar()",
            "getchar(), putchar(getchar() + 1), getchar()",
            "getchar(), putchar(putchar(getchar())), getchar()",
            "getchar(), (putchar(getchar())), getchar()",
            "(getchar(), putchar(getchar())), getchar()",
            "getchar(), putchar(getchar()), getchar() + 1",
            "getchar(), putchar(getchar()), 42",
            "getchar(), getchar() == 0, getchar()",
            "getchar(), (void)putchar(getchar()), getchar()",
            "getchar(), putchar(getchar()), putchar(0)",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            for index, expression in enumerate(invalid):
                with self.subTest(index=index):
                    source = Path(folder) / f"invalid-{index}.c"
                    target = Path(folder) / f"invalid-{index}.malbolge"
                    source.write_text(self.source(f"    {expression};\n"))
                    result = self.compile(source, target)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_clang_mixed_call_metadata_refuses_publication(self) -> None:
        changes = (
            (16, ("operation",), "+"),
            (16, ("parent",), 1),
            (16, ("type",), "u32"),
            (16, ("span", "end", "column"), 999),
            (17, ("operation",), "*"),
            (17, ("span", "begin", "byte"), 20),
            (18, ("parent",), 16),
            (18, ("reference",), "external:putchar"),
            (21, ("parent",), 16),
            (21, ("reference",), "external:getchar"),
            (21, ("span", "begin", "column"), 2),
            (22, ("operation",), "integral-cast"),
            (23, ("type",), "fn()->i32"),
            (24, ("parent",), 17),
            (24, ("span", "end", "byte"), 1),
            (27, ("parent",), 17),
            (27, ("span", "end", "line"), 1),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "original.c"
            source.write_text(self.source(MIXED))
            original = self.frontend(source)
            for index, (node_id, path, value) in enumerate(changes):
                with self.subTest(index=index):
                    forged = copy.deepcopy(original)
                    nodes = forged["nodes"]
                    assert isinstance(nodes, list)
                    node = next(node for node in nodes if node["id"] == node_id)
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
