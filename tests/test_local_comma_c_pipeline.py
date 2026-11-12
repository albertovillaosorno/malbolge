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
#   - Source-C comma uses of the current live input local in a real guest.
# - Must-Not:
#   - Reload a local or replay stdin from the host after a newer guest read.
# - Allows:
#   - Inputs: pinned Clang provenance, isolated binary input.
#   - Outputs: independent VM parity and fail-closed AST rejection.
#   - Side effects: temporary build artifacts only.
# - Split-When:
#   - Guest C storage and general comma expressions replace this bound.
# - Merge-When:
#   - An expression-wide source proof shares live local SSA semantics.
# - Summary:
#   - Proves local-return comma operands use the actual captured guest byte.

"""Validate live-local comma call returns inside the actual Malbolge guest."""

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
    "    putchar(first);\n"
    "    putchar((putchar(first), putchar(first)));\n"
    "    putchar(first);\n"
    "    int second = getchar();\n"
    "    putchar(second);\n"
    "    putchar((putchar(second), putchar(second)));\n"
)


class LocalCommaCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned frontend, adapter, layout and VM are required")

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
            check=False,
            capture_output=True,
            timeout=90,
        )

    @staticmethod
    def vm(target: Path, data: bytes) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [str(VM), str(target), "--input-stdin", "--report-steps"],
            input=data,
            check=False,
            capture_output=True,
            timeout=40,
        )

    def test_two_live_locals_reused_in_nested_comma_call(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "stream.c"
            target = Path(folder) / "stream.malbolge"
            source.write_text(self.source(BODY))
            compiled = self.compile(source, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            rng = random.Random(0xC0_A1_2026)
            samples = [b"\x00\xff", b"\x80\x01", b"AB"]
            samples += [bytes(rng.getrandbits(8) for _ in range(2)) for _ in range(12)]
            with ThreadPoolExecutor(max_workers=4) as executor:
                guests = executor.map(lambda data: self.vm(target, data), samples)
                for sample, guest in zip(samples, guests, strict=True):
                    with self.subTest(sample=sample):
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        self.assertEqual(
                            guest.stdout,
                            bytes((sample[0],)) * 5 + bytes((sample[1],)) * 4,
                        )
                        self.assertEqual(guest.stderr, b"malbolge-steps-v1:12\n")

    def test_local_comma_can_precede_new_guest_input(self) -> None:
        variants = (
            ("putchar((putchar(first), putchar(getchar())));", (0, 1, 1)),
            ("putchar((putchar(first), getchar()));", (0, 1)),
            ("putchar(first), putchar(first);", (0, 0)),
            ("putchar((putchar(putchar(first)), putchar(first)));", (0, 0, 0, 0)),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            for index, (statement, positions) in enumerate(variants):
                with self.subTest(statement=statement):
                    source = Path(folder) / f"variant-{index}.c"
                    target = Path(folder) / f"variant-{index}.malbolge"
                    source.write_text(
                        self.source(
                            "    int first = getchar();\n"
                            "    putchar(first);\n"
                            f"    {statement}\n"
                        )
                    )
                    compiled = self.compile(source, target)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    sample = b"\xff\x00"
                    guest = self.vm(target, sample)
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    expected = bytes((sample[0],)) + bytes(sample[i] for i in positions)
                    self.assertEqual(guest.stdout, expected)
                    reads = 2 if "getchar()" in statement else 1
                    self.assertEqual(
                        guest.stderr,
                        f"malbolge-steps-v1:{reads + len(expected) + 1}\n".encode(),
                    )

    def test_input_before_stale_local_in_one_comma_refuses_target(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "stale-in-comma.c"
            target = Path(folder) / "stale-in-comma.malbolge"
            source.write_text(
                self.source(
                    "    int first = getchar();\n"
                    "    putchar(first);\n"
                    "    putchar((getchar(), putchar(first)));\n"
                )
            )
            compiled = self.compile(source, target)
            self.assertNotEqual(compiled.returncode, 0)
            self.assertFalse(target.exists())

    def test_forged_local_comma_ancestry_refuses_publication(self) -> None:
        changes = (
            (13, ("parent",), 17),
            (16, ("span", "end", "byte"), 1),
            (17, ("operation",), "+"),
            (18, ("parent",), 2),
            (18, ("span", "begin", "column"), 0),
            (21, ("operation",), "integral-cast"),
            (22, ("reference",), "second@161"),
            (23, ("span", "end", "byte"), 999),
            (26, ("parent",), 17),
            (27, ("reference",), "first@999"),
            (43, ("reference",), "external:getchar"),
            (47, ("type",), "u32"),
            (52, ("parent",), 47),
            (57, ("reference",), "first@47"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "original.c"
            source.write_text(self.source(BODY))
            normalized = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "local-comma-v1",
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=20,
            )
            self.assertEqual(normalized.returncode, 0, normalized.stderr)
            original = json.loads(normalized.stdout)
            for index, (node_id, path, value) in enumerate(changes):
                with self.subTest(node_id=node_id, path=path):
                    changed = copy.deepcopy(original)
                    node = next(n for n in changed["nodes"] if n["id"] == node_id)
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
                        input=json.dumps(changed, separators=(",", ":")).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_stale_local_after_new_input_refuses_target(self) -> None:
        body = (
            "    int first = getchar();\n"
            "    putchar(first);\n"
            "    int second = getchar();\n"
            "    putchar(second);\n"
            "    putchar((putchar(first), putchar(second)));\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "stale.c"
            target = Path(folder) / "stale.malbolge"
            source.write_text(self.source(body))
            compiled = self.compile(source, target)
            self.assertNotEqual(compiled.returncode, 0)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
