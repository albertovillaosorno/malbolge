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
#   - Nested literal C condition guest-effect source and VM evidence.
# - Must-Not:
#   - Erase unselected unknown effects or replay guest inputs on the host.
# - Allows:
#   - Inputs: pinned Clang and bounded binary VM streams.
#   - Outputs: independent oracle parity and malformed-source refusals.
#   - Side effects: isolated temporary compilation products.
# - Split-When:
#   - General runtime guest branch lowering replaces literal selection.
# - Merge-When:
#   - Adjacent branch suite owns nested source-level control.
# - Summary:
#   - Verifies nested literal if/else ancestry and ordered guest I/O.

"""Nested source-C constant branches executed by the normative guest VM."""

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
    "    if (1) if (0) putchar(getchar()); else putchar((putchar(first), first));\n"
    "    putchar(getchar());\n"
    "    if (0) if (1) putchar(getchar()); else putchar(getchar());\n"
    "    putchar(getchar());\n"
)


class NestedStaticIfCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned frontend, adapter, layout and guest VM required")

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
    def normalized(source: Path) -> dict[str, object]:
        result = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "nested-static-if",
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=20,
        )
        if result.returncode:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)

    @staticmethod
    def vm(target: Path, sample: bytes) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [str(VM), str(target), "--input-stdin", "--report-steps"],
            input=sample,
            capture_output=True,
            check=False,
            timeout=30,
        )

    def test_real_guest_nested_conditions_preserve_input_oracle(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "nested.c"
            target = Path(directory) / "nested.malbolge"
            source.write_text(self.source(BODY))
            built = self.compile(source, target)
            self.assertEqual(built.returncode, 0, built.stderr)
            rng = random.Random(0x1F_11_2026)
            samples = [b"\x00\xff\x80", b"\xff\x00\x01", b"ABC"]
            samples += [bytes(rng.getrandbits(8) for _ in range(3)) for _ in range(9)]
            with ThreadPoolExecutor(max_workers=6) as executor:
                guests = executor.map(lambda sample: self.vm(target, sample), samples)
                for sample, guest in zip(samples, guests, strict=True):
                    with self.subTest(sample=sample):
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        self.assertEqual(
                            guest.stdout,
                            bytes((sample[0], sample[0], sample[1], sample[2])),
                        )
                        self.assertEqual(guest.stderr, b"malbolge-steps-v1:8\n")

    def test_multiline_outer_arm_executes_nested_literal_branch(self) -> None:
        body = (
            "    int first = getchar();\n"
            "    if (1) {\n"
            "        if (0) putchar(getchar()); else putchar(first);\n"
            "        putchar(getchar());\n"
            "    } else {\n"
            "        putchar(getchar());\n"
            "    }\n"
            "    putchar(getchar());\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "multiline.c"
            target = Path(directory) / "multiline.malbolge"
            source.write_text(self.source(body))
            built = self.compile(source, target)
            self.assertEqual(built.returncode, 0, built.stderr)
            samples = (b"\x00\xff\x80", b"ABC", b"\xff\x00\x01")
            with ThreadPoolExecutor(max_workers=3) as executor:
                guests = executor.map(lambda sample: self.vm(target, sample), samples)
                for sample, guest in zip(samples, guests, strict=True):
                    with self.subTest(sample=sample):
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        self.assertEqual(guest.stdout, sample)
                        self.assertEqual(guest.stderr, b"malbolge-steps-v1:7\n")

    def test_unselected_nested_input_does_not_execute(self) -> None:
        body = (
            "    if (0) if (1) putchar(getchar()); else putchar(getchar());\n"
            "    putchar(getchar());\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "skipped.c"
            target = Path(directory) / "skipped.malbolge"
            source.write_text(self.source(body))
            built = self.compile(source, target)
            self.assertEqual(built.returncode, 0, built.stderr)
            samples = (b"\x00\xff", b"\xff\x00", b"Q")
            with ThreadPoolExecutor(max_workers=3) as executor:
                guests = executor.map(lambda sample: self.vm(target, sample), samples)
                for sample, guest in zip(samples, guests, strict=True):
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(guest.stdout, sample[:1])
                    self.assertEqual(guest.stderr, b"malbolge-steps-v1:3\n")

    def test_else_if_chain_uses_only_selected_live_local(self) -> None:
        body = (
            "    int first = getchar();\n"
            "    if (0) putchar(getchar()); else if (0) putchar(getchar()); "
            "else if (1) putchar(first); else putchar(getchar());\n"
            "    putchar(getchar());\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "else-if.c"
            target = Path(directory) / "else-if.malbolge"
            source.write_text(self.source(body))
            built = self.compile(source, target)
            self.assertEqual(built.returncode, 0, built.stderr)
            samples = (b"\x00\xff", b"\xff\x00", b"QR", b"\x80\x7f")
            with ThreadPoolExecutor(max_workers=4) as executor:
                guests = executor.map(lambda sample: self.vm(target, sample), samples)
                for sample, guest in zip(samples, guests, strict=True):
                    with self.subTest(sample=sample):
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        self.assertEqual(guest.stdout, sample)
                        self.assertEqual(guest.stderr, b"malbolge-steps-v1:5\n")

    def test_four_levels_compile_and_five_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for depth in (4, 5):
                with self.subTest(depth=depth):
                    source = Path(directory) / f"depth-{depth}.c"
                    target = Path(directory) / f"depth-{depth}.malbolge"
                    body = "    " + "if (1) " * depth + "putchar(getchar());\n"
                    source.write_text(self.source(body))
                    built = self.compile(source, target)
                    if depth == 5:
                        self.assertNotEqual(built.returncode, 0)
                        self.assertFalse(target.exists())
                        continue
                    self.assertEqual(built.returncode, 0, built.stderr)
                    guest = self.vm(target, b"\xff")
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(guest.stdout, b"\xff")
                    self.assertEqual(guest.stderr, b"malbolge-steps-v1:3\n")

    def test_nested_condition_metadata_forgeries_refuse_publication(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "nested.c"
            source.write_text(self.source(BODY))
            original = self.normalized(source)
            inner = next(
                n
                for n in original["nodes"]
                if n["kind"] == "if-statement" and n["parent"] != 2
            )
            inner_literal = next(
                n
                for n in original["nodes"]
                if n["parent"] == inner["id"] and n["kind"] == "integer-literal"
            )
            skipped = next(
                n
                for n in original["nodes"]
                if n["kind"] == "if-statement"
                and n["parent"] != 2
                and n["id"] != inner["id"]
            )
            cases = (
                (inner["id"], "parent", 2),
                (inner["id"], "kind", "while-statement"),
                (inner["id"], "span.begin.byte", 1),
                (inner["id"], "span.begin.line", 1),
                (inner["id"], "span.begin.column", 1),
                (inner["id"], "span.end.byte", 1),
                (inner["id"], "span.end.column", 1),
                (inner["id"], "operation", "+"),
                (inner["id"], "reference", "external:getchar"),
                (inner["id"], "type_name", "i32"),
                (inner["id"], "literal", "1"),
                (inner_literal["id"], "parent", 2),
                (inner_literal["id"], "literal", "1"),
                (inner_literal["id"], "constant_integer", "1"),
                (inner_literal["id"], "span.begin.byte", 1),
                (skipped["id"], "parent", 2),
                (skipped["id"], "span.end.byte", 1),
            )
            for index, (node_id, field, value) in enumerate(cases):
                with self.subTest(node_id=node_id, field=field):
                    forged = copy.deepcopy(original)
                    node = next(n for n in forged["nodes"] if n["id"] == node_id)
                    if field.startswith("span."):
                        _, endpoint, coord = field.split(".")
                        node["span"][endpoint][coord] = value
                    else:
                        node[field] = value
                    target = Path(directory) / f"forged-{index}.malbolge"
                    result = subprocess.run(
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
                        timeout=20,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_unsupported_nested_arms_refuse_publication(self) -> None:
        variants = (
            "    if (1) if (0) putchar(getchar() + 1); else putchar(getchar());\n",
            "    if (1) if (0) putchar(getchar()); else putchar(65);\n",
            "    if (0) if (1) putchar(65); else putchar(getchar());\n",
            "    if (getchar()) if (1) putchar(getchar());\n",
            "    if (1) if (getchar()) putchar(getchar());\n",
            "    if (0) putchar(getchar()); else if (1) putchar(65);\n",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, body in enumerate(variants):
                with self.subTest(index=index):
                    source = Path(directory) / f"bad-{index}.c"
                    target = Path(directory) / f"bad-{index}.malbolge"
                    source.write_text(self.source(body))
                    result = self.compile(source, target)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
