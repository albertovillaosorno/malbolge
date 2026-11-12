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
#   - Genuine guest I/O in source-authenticated static C compound arms.
# - Must-Not:
#   - Emit skipped C effects or grant runtime-dependent guest branching.
# - Allows:
#   - Inputs: pinned Clang JSON, bounded C, isolated binary guest streams.
#   - Outputs: normative VM oracles and fail-closed source/AST rejections.
#   - Side effects: temporary test artifacts only.
# - Split-When:
#   - Runtime guest C control flow handles actual block statements.
# - Merge-When:
#   - The unified C source-effect projector replaces this grammar.
# - Summary:
#   - Verifies ordered multiple effects in selected static C blocks.

"""Real Malbolge guest execution for bounded static C compound branches."""

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
    "    if (1) { putchar(first); putchar(putchar(getchar())); } "
    "else { putchar(getchar()); }\n"
    "    if (0) { getchar(); putchar(getchar()); } "
    "else { putchar(getchar()); }\n"
)


class StaticBlockInputCPipelineTests(unittest.TestCase):
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
             str(RESOURCE), "--source-id", "static-block-source", str(source)],
            capture_output=True, check=False, timeout=20,
        )
        if result.returncode:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)

    def test_complete_source_preserves_selected_multi_effect_arm(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "compound.c"
            target = Path(directory) / "compound.malbolge"
            source.write_text(self.source(BODY))
            built = self.compile(source, target)
            self.assertEqual(built.returncode, 0, built.stderr)
            rng = random.Random(0xB10C_2026)
            samples = [b"\x00\xff\x80", b"\xff\x00\x01", b"ABC"]
            samples += [bytes(rng.getrandbits(8) for _ in range(3)) for _ in range(12)]
            with ThreadPoolExecutor(max_workers=4) as executor:
                guests = executor.map(lambda sample: self.vm(target, sample), samples)
                for sample, guest in zip(samples, guests, strict=True):
                    with self.subTest(sample=sample):
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        self.assertEqual(
                            guest.stdout,
                            bytes((sample[0], sample[1], sample[1], sample[2])),
                        )
                        self.assertEqual(guest.stderr, b"malbolge-steps-v1:8\n")

    def test_blocks_preserve_input_order_and_local_liveness(self) -> None:
        # Two additional guest shapes; the 15-oracle full source test covers
        # mixed nested calls and both selected and skipped compound arms.
        cases = (
            ("    if (1) { getchar(); putchar(getchar()); }\n",
             b"\xff\x00", b"\x00", 4),
            (("    int live = getchar();\n"
              "    if (0) { putchar(getchar()); putchar(getchar()); }\n"
              "    if (1) { putchar(live); putchar(live); }\n"),
             b"\x80", b"\x80\x80", 4),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, (body, data, expected, steps) in enumerate(cases):
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

    def test_unproved_block_statements_never_publish_guest(self) -> None:
        invalid = (
            "if (getchar()) { putchar(getchar()); }",
            "if (2) { putchar(getchar()); }",
            "if (0) { putchar(65); } else { putchar(getchar()); }",
            "if (1) { putchar(getchar()); int x = getchar(); }",
            "if (1) { putchar(getchar()); ; }",
            "if (1) { putchar(getchar()); putchar(65); }",
            "if (1) { if (1) putchar(getchar()); }",
            "if (1) { putchar(getchar()), getchar(); }",
            "if (0) { putchar(getchar()); } else if (1) " +
            "{ putchar(getchar()); }",
            "if (1) { putchar(getchar()); } else { ++first; }",
            "if (1) { putchar(first); getchar(); putchar(first); }",
            "if (0) { putchar(getchar()); putchar(first); }",
            "if (1) { putchar(getchar());\n" +
            "    putchar(getchar()); }",
            "if (1) { putchar(getchar()); } " +
            "else { putchar(getchar()); putchar(42); }",
            "if (1) { " + "getchar(); " * 17 + "}",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, statement in enumerate(invalid):
                with self.subTest(statement=statement):
                    source = Path(directory) / f"invalid-{index}.c"
                    target = Path(directory) / f"invalid-{index}.malbolge"
                    source.write_text(self.source(
                        "    int first = getchar();\n"
                        f"    {statement}\n"
                    ))
                    result = self.compile(source, target)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_compound_and_both_arms_refuse_publication(self) -> None:
        changes = (
            (8, "parent", 1),
            (8, "span.end.byte", 1),
            (9, "constant_integer", "0"),
            (9, "span.begin.column", 1),
            (10, "parent", 2),
            (10, "kind", "call-expression"),
            (10, "span.begin.byte", 1),
            (10, "span.end.byte", 1),
            (10, "span.end.line", 100),
            (11, "parent", 8),
            (11, "span.begin.column", 1),
            (14, "reference", "external:getchar"),
            (16, "parent", 8),
            (19, "reference", "external:getchar"),
            (22, "span.end.column", 1),
            (25, "parent", 2),
            (25, "kind", "if-statement"),
            (25, "span.begin.byte", 1),
            (26, "parent", 8),
            (29, "reference", "external:putchar"),
            (32, "span.end.byte", 1),
            (34, "parent", 2),
            (35, "parent", 32),
            (38, "parent", 32),
            (43, "span.begin.byte", 1),
            (45, "parent", 32),
            (48, "reference", "external:putchar"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "original.c"
            source.write_text(self.source(BODY))
            original = self.normalized(source)
            for index, (node_id, field, value) in enumerate(changes):
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

    def test_compound_statement_limit(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for count in (1, 2, 17):
                with self.subTest(count=count):
                    source = Path(directory) / f"count-{count}.c"
                    target = Path(directory) / f"count-{count}.malbolge"
                    source.write_text(self.source(
                        "    if (1) { " + "getchar(); " * count + "}\n"
                    ))
                    built = self.compile(source, target)
                    if count == 17:
                        self.assertNotEqual(built.returncode, 0)
                        self.assertFalse(target.exists())
                    else:
                        self.assertEqual(built.returncode, 0, built.stderr)
                        guest = self.vm(target, bytes(range(count)))
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        self.assertEqual(guest.stdout, b"")
                        self.assertEqual(
                            guest.stderr,
                            f"malbolge-steps-v1:{count + 1}\n".encode(),
                        )


if __name__ == "__main__":
    unittest.main()
