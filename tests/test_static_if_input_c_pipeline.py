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
#   - Source-verified constant C if arms with genuine guest byte I/O.
# - Must-Not:
#   - Execute a skipped input or use host stdout to imitate guest effects.
# - Allows:
#   - Inputs: pinned normalized C, isolated binary stdin.
#   - Outputs: independent guest byte oracles and source/AST refusal.
#   - Side effects: temporary artifacts only.
# - Split-When:
#   - Dynamic guest control-flow and general C blocks are implemented.
# - Merge-When:
#   - The general C control-flow lowerer reuses guest input SSA.
# - Summary:
#   - Confirms static control conditions preserve runtime guest effects.

"""Compile source-C static if statements to real Malbolge guest effects."""

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
    "    if (0) putchar(getchar());\n"
    "    if (1) putchar(first);\n"
    "    if (0) putchar(first);\n"
    "    if (1) putchar(getchar());\n"
    "    putchar(getchar());\n"
)


class StaticIfInputCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned frontend, adapter, layout and VM required")

    @staticmethod
    def source(body: str) -> str:
        return "#include <stdio.h>\nvoid stream(void) {\n" + body + "}\n"

    @staticmethod
    def compile(source: Path, target: Path) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [sys.executable, "-B", str(DRIVER), "--repository-tools", "--capsule",
             "--output", str(target), str(source)],
            capture_output=True, check=False, timeout=90,
        )

    @staticmethod
    def vm(target: Path, data: bytes) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [str(VM), str(target), "--input-stdin", "--report-steps"],
            input=data, capture_output=True, check=False, timeout=40,
        )

    @staticmethod
    def normalized(source: Path) -> dict[str, object]:
        result = subprocess.run(
            [str(FRONTEND), "--guest-include", str(INCLUDE), "--resource-dir",
             str(RESOURCE), "--source-id", "static-if-source", str(source)],
            capture_output=True, check=False, timeout=20,
        )
        if result.returncode:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)

    def test_static_if_preserves_selected_guest_reads_and_writes(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "stream.c"
            target = Path(directory) / "stream.malbolge"
            source.write_text(self.source(BODY))
            built = self.compile(source, target)
            self.assertEqual(built.returncode, 0, built.stderr)
            rng = random.Random(0x5A71_F2026)
            samples = [b"\x00\xff\x80", b"\xff\x00\x01", b"ABC"]
            samples += [bytes(rng.getrandbits(8) for _ in range(3)) for _ in range(12)]
            with ThreadPoolExecutor(max_workers=4) as executor:
                guests = executor.map(lambda sample: self.vm(target, sample), samples)
                for sample, guest in zip(samples, guests, strict=True):
                    with self.subTest(sample=sample):
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        self.assertEqual(guest.stdout, sample)
                        self.assertEqual(guest.stderr, b"malbolge-steps-v1:7\n")

    def test_if_else_selects_only_one_guest_arm(self) -> None:
        body = (
            "    int first = getchar();\n"
            "    if (0) putchar(getchar()); else putchar(first);\n"
            "    if (1) putchar(first); else putchar(getchar());\n"
            "    if (1) putchar(getchar()); else putchar(first);\n"
            "    putchar(getchar());\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "ifelse.c"
            target = Path(directory) / "ifelse.malbolge"
            source.write_text(self.source(body))
            built = self.compile(source, target)
            self.assertEqual(built.returncode, 0, built.stderr)
            rng = random.Random(0xE15E_2026)
            samples = [b"\x00\xff\x80", b"\xff\x00\x01"]
            samples += [bytes(rng.getrandbits(8) for _ in range(3)) for _ in range(8)]
            with ThreadPoolExecutor(max_workers=4) as executor:
                guests = executor.map(lambda data: self.vm(target, data), samples)
                for data, guest in zip(samples, guests, strict=True):
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(
                        guest.stdout,
                        bytes((data[0], data[0], data[1], data[2])),
                    )
                    self.assertEqual(guest.stderr, b"malbolge-steps-v1:8\n")

    def test_if_else_rejects_forged_skipped_arm(self) -> None:
        body = (
            "    int first = getchar();\n"
            "    if (0) putchar(getchar()); else putchar(first);\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "ifelse.c"
            source.write_text(self.source(body))
            original = self.normalized(source)
            changes = (
                (8, "span.end.byte", 1),
                (10, "parent", 2),
                (10, "reference", "external:getchar"),
                (13, "parent", 8),
                (16, "parent", 2),
                (16, "span.begin.column", 1),
                (19, "reference", "first@1000"),
            )
            for index, (node_id, field, value) in enumerate(changes):
                forged = copy.deepcopy(original)
                node = next(n for n in forged["nodes"] if n["id"] == node_id)
                target_field = node
                for part in field.split(".")[:-1]:
                    target_field = target_field[part]
                target_field[field.split(".")[-1]] = value
                target = Path(directory) / f"forged-else-{index}.malbolge"
                result = subprocess.run(
                    [str(ADAPTER), "--layout-backend", str(LAYOUT),
                     "--output", str(target), "--capsule"],
                    input=json.dumps(forged, separators=(",", ":")).encode(),
                    capture_output=True, check=False, timeout=30,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(target.exists())

    def test_skipped_and_selected_nested_effects(self) -> None:
        bodies = (
            (
                ("    if (0) getchar();\n"
                 "    if (1) putchar(putchar(getchar()));\n"),
                b"Z", b"ZZ", 4,
            ),
            (
                ("    if (1) getchar();\n"
                 "    if (0) putchar(getchar());\n"
                 "    putchar(getchar());\n"),
                b"AB", b"B", 4,
            ),
            (
                ("    int live = getchar();\n"
                 "    if (1) putchar(putchar(live));\n"
                 "    if (0) putchar(getchar());\n"),
                b"\xff", b"\xff\xff", 4,
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, (body, data, expected, steps) in enumerate(bodies):
                with self.subTest(body=body):
                    source = Path(directory) / f"variant-{index}.c"
                    target = Path(directory) / f"variant-{index}.malbolge"
                    source.write_text(self.source(body))
                    built = self.compile(source, target)
                    self.assertEqual(built.returncode, 0, built.stderr)
                    guest = self.vm(target, data)
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(guest.stdout, expected)
                    self.assertEqual(
                        guest.stderr, f"malbolge-steps-v1:{steps}\n".encode(),
                    )

    def test_unproved_source_if_is_not_published(self) -> None:
        invalid = (
            "if (getchar()) putchar(first);",
            "if (first) putchar(first);",
            "if (1) { putchar(first); ++first; }",
            "if (1) putchar(first); else ++first;",
            "if (1) putchar(first + 1);",
            "if (0) putchar(first + 1);",
            "if (1) ++first;",
            "if (1) putchar(65);",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, statement in enumerate(invalid):
                with self.subTest(statement=statement):
                    source = Path(directory) / f"invalid-{index}.c"
                    target = Path(directory) / f"invalid-{index}.malbolge"
                    source.write_text(self.source(
                        "    int first = getchar();\n" f"    {statement}\n"
                        "    putchar(first);\n"
                    ))
                    result = self.compile(source, target)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_condition_provenance_refuses_guest(self) -> None:
        edits = (
            (8, "parent", 1),
            (8, "kind", "for-statement"),
            (8, "operation", "!"),
            (8, "span.end.byte", 1),
            (9, "constant_integer", "1"),
            (9, "literal", "1"),
            (9, "parent", 2),
            (9, "span.begin.column", 1),
            (9, "type", "u32"),
            (10, "parent", 2),
            (10, "span.begin.byte", 1),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "original.c"
            source.write_text(self.source(BODY))
            original = self.normalized(source)
            for index, (node_id, field, value) in enumerate(edits):
                with self.subTest(index=index):
                    forged = copy.deepcopy(original)
                    node = next(n for n in forged["nodes"] if n["id"] == node_id)
                    target_field = node
                    for part in field.split(".")[:-1]:
                        target_field = target_field[part]
                    target_field[field.split(".")[-1]] = value
                    target = Path(directory) / f"forged-{index}.malbolge"
                    result = subprocess.run(
                        [str(ADAPTER), "--layout-backend", str(LAYOUT),
                         "--output", str(target), "--capsule"],
                        input=json.dumps(forged, separators=(",", ":")).encode(),
                        capture_output=True, check=False, timeout=30,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
