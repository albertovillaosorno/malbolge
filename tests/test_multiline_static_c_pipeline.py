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
#   - Source-proven multiline constant-branch guest I/O acceptance.
# - Must-Not:
#   - Substitute host-emitted bytes for VM execution or accept hidden effects.
# - Allows:
#   - Inputs: pinned C frontend, canonical adapter, bounded binary streams.
#   - Outputs: byte and step parity, source and AST refusal evidence.
#   - Side effects: isolated temporary generated guest artifacts only.
# - Split-When:
#   - General runtime C control flow supersedes the static branch grammar.
# - Merge-When:
#   - The adjacent constant-branch suite owns multiline projections.
# - Summary:
#   - Verifies exact multiline call ancestry in both constant C if arms.

"""End-to-end guest VM proof for canonically indented multiline C arms."""

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
    "    if (1) {\n"
    "        putchar(first);\n"
    "        putchar(putchar(getchar()));\n"
    "    } else {\n"
    "        putchar(getchar());\n"
    "    }\n"
    "    if (0) {\n"
    "        getchar();\n"
    "        putchar(getchar());\n"
    "    } else {\n"
    "        putchar(getchar());\n"
    "    }\n"
)


class MultilineStaticCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(p.is_file() for p in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned frontend, adapter, layout and VM required")

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
    def vm(target: Path, data: bytes) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [str(VM), str(target), "--input-stdin", "--report-steps"],
            input=data,
            capture_output=True,
            check=False,
            timeout=30,
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
                "multiline-branch",
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=20,
        )
        if result.returncode:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)

    def test_two_multiline_branches_execute_binary_vm_oracles(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "multiline.c"
            target = Path(directory) / "multiline.malbolge"
            source.write_text(self.source(BODY))
            built = self.compile(source, target)
            self.assertEqual(built.returncode, 0, built.stderr)
            rng = random.Random(0x11_12_2026)
            samples = [b"\x00\xff\x80", b"\xff\x00\x01", b"ABC", b"\x80\x00\xff"]
            samples += [bytes(rng.getrandbits(8) for _ in range(3)) for _ in range(4)]
            with ThreadPoolExecutor(max_workers=4) as executor:
                for sample, guest in zip(
                    samples,
                    executor.map(lambda data: self.vm(target, data), samples),
                    strict=True,
                ):
                    with self.subTest(sample=sample):
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        self.assertEqual(
                            guest.stdout,
                            bytes((sample[0], sample[1], sample[1], sample[2])),
                        )
                        self.assertEqual(guest.stderr, b"malbolge-steps-v1:8\n")

    def test_single_statement_and_sixteen_call_bound(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for count in (1, 2, 16, 17):
                with self.subTest(count=count):
                    source = Path(directory) / f"count-{count}.c"
                    target = Path(directory) / f"count-{count}.malbolge"
                    source.write_text(
                        self.source(
                            "    if (1) {\n"
                            + "        getchar();\n" * count
                            + "    }\n"
                        )
                    )
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

    def test_unproved_multiline_statements_never_publish(self) -> None:
        invalid = (
            "    if (getchar()) {\n        putchar(getchar());\n    }\n",
            "    if (2 + 0) {\n        putchar(getchar());\n    }\n",
            "    if (1) {\n        putchar(65);\n    }\n",
            "    if (1) {\n        if (getchar()) putchar(getchar());\n    }\n",
            "    if (1) {\n        putchar(getchar());\n\n        putchar(getchar());\n    }\n",
            "    if (1) {\n      putchar(getchar());\n    }\n",
            "    if (1) {\n        putchar(getchar());\n  }\n",
            "    if (1) {\n        putchar(getchar());\n        int x = getchar();\n    }\n",
            "    if (0) {\n        putchar(65);\n    } else {\n        putchar(getchar());\n    }\n",
            "    if (1) {\n        putchar(getchar());\n        putchar(first);\n    }\n",
            "    if (1) {\n        putchar(getchar());\n        return;\n    }\n",
            "    if (1) {\n" + "        getchar();\n" * 17 + "    }\n",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, body in enumerate(invalid):
                with self.subTest(index=index):
                    source = Path(directory) / f"invalid-{index}.c"
                    target = Path(directory) / f"invalid-{index}.malbolge"
                    source.write_text(self.source(body))
                    built = self.compile(source, target)
                    self.assertNotEqual(built.returncode, 0)
                    self.assertFalse(target.exists())

    def test_multiline_provenance_forgery_refuses_publication(self) -> None:
        changes = (
            (8, "parent", 1),
            (8, "span.end.byte", 185),
            (8, "span.end.line", 8),
            (8, "span.end.column", 5),
            (9, "constant_integer", "0"),
            (10, "parent", 2),
            (10, "span.end.line", 6),
            (10, "span.end.column", 7),
            (11, "span.begin.line", 4),
            (11, "span.begin.column", 8),
            (16, "span.begin.byte", 110),
            (16, "span.begin.line", 5),
            (25, "span.end.column", 7),
            (25, "parent", 2),
            (26, "span.begin.column", 8),
            (32, "span.end.line", 14),
            (34, "span.end.line", 12),
            (35, "span.begin.byte", 207),
            (44, "span.end.column", 7),
            (45, "span.begin.line", 13),
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
