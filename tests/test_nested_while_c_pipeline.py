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
#   - End-to-end guest parity and forged-source refusals for nested while.
# - Must-Not:
#   - Substitute host stdout for real Malbolge VM output.
# - Allows:
#   - Inputs: pinned normalized Clang, adapter, layout, and normative guest.
#   - Outputs: matching recurrence bytes or explicit source rejection.
#   - Side effects: temporary source/guest paths only.
# - Split-When:
#   - General source-proof loop replay subsumes this C fixture.
# - Merge-When:
#   - Whole-program dynamic control validation replaces this boundary.
# - Summary:
#   - Both C loops must execute once, in both parity branches.

"""Source-authenticated direct nested while loops reach actual Malbolge."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests/compiler/c-frontend/accepted/local_nested_while_fibonacci.c"
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
ADAPTER = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT = ROOT / ".cache/rust/target/debug/malbolge_layout"
VM = ROOT / ".cache/rust/target/debug/malbolge"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"


def independent_oracle() -> bytes:
    a, b = 1, 1
    output = bytearray()
    for _ in range(12):
        following = (a + b) & 255
        mask = 0
        outer = inner = 0
        while outer < 1:
            while inner < 1:
                if following & 1:
                    mask ^= 26
                else:
                    mask |= 0
                inner += 1
                outer += 1
        output.append((following ^ mask) & 31)
        a, b = b, following
    return bytes(output)


class NestedWhilePipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(p.is_file() for p in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler binaries not available")

    @staticmethod
    def normalize(source: Path) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/nested-while-fibonacci-v1",
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=20,
            env={**os.environ, "TMPDIR": str(ROOT / ".temp")},
        )

    @staticmethod
    def project(normalized: bytes, output: Path) -> subprocess.CompletedProcess[bytes]:
        # Refuse downstream work immediately after normalized C admission.
        # The intentionally failing backend identifies a successful frontend
        # projection without incurring slow guest layout search for negatives.
        return subprocess.run(
            [str(ADAPTER), "--layout-backend", "/bin/false", "--output", str(output)],
            input=normalized,
            capture_output=True,
            check=False,
            timeout=20,
        )

    def test_direct_nested_while_full_guest_parity(self) -> None:
        expected = independent_oracle()
        self.assertEqual(expected, bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "nested-while.malbolge"
            built = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/nested-while-fibonacci-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(SOURCE),
                ],
                capture_output=True,
                check=False,
                timeout=240,
                env={**os.environ, "TMPDIR": str(ROOT / ".temp")},
            )
            self.assertEqual(built.returncode, 0, built.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((0, 255, 128))):
                run = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, expected)
                self.assertEqual(run.stderr, b"malbolge-steps-v1:47\n")

    def test_nonterminating_and_effectful_sources_refuse(self) -> None:
        original = SOURCE.read_text()
        variants = {
            "outer-not-advanced": original.replace("outer += 1U;", "outer += 0U;"),
            "inner-not-advanced": original.replace("inner += 1U;", "inner += 0U;"),
            "outer-unbounded": original.replace("outer < 1U", "outer < 100U"),
            "inner-unbounded": original.replace("inner < 1U", "inner < 100U"),
            "unknown-input": original.replace(
                "mask ^= 26U;", "mask ^= (unsigned)getchar();"
            ),
            "outer-counter-write": original.replace("outer += 1U;", "i += 1U;"),
            "selected-undefined": original.replace(
                "inner += 1U;", "inner += (1U / 0U);"
            ),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, content in variants.items():
                with self.subTest(label=label):
                    self.assertNotEqual(content, original)
                    source = Path(scratch) / f"{label}.c"
                    source.write_text(content)
                    normalized = self.normalize(source)
                    if normalized.returncode:
                        continue  # A strict Clang refusal also fails closed.
                    guest = Path(scratch) / f"{label}.malbolge"
                    outcome = self.project(normalized.stdout, guest)
                    self.assertIn(b"normalized frontend rejected", outcome.stderr)
                    self.assertFalse(guest.exists())

    def test_forged_nested_while_spans_refuse(self) -> None:
        normalized = self.normalize(SOURCE)
        self.assertEqual(normalized.returncode, 0, normalized.stderr)
        nodes = json.loads(normalized.stdout)["nodes"]
        outer = next(n for n in nodes if n["kind"] == "while-statement")
        inner = next(
            n
            for n in nodes
            if n["kind"] == "while-statement" and n["parent"] == outer["id"]
        )
        predicate = next(
            n
            for n in nodes
            if n["parent"] == outer["id"] and n["kind"] == "binary-expression"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            valid = self.project(normalized.stdout, Path(scratch) / "valid.malbolge")
            self.assertIn(b"layout backend exited", valid.stderr)
            variants = {
                "inner-parent": (inner, "parent", None),
                "inner-begin-byte": (inner, "begin", "byte"),
                "inner-begin-line": (inner, "begin", "line"),
                "inner-begin-column": (inner, "begin", "column"),
                "inner-end-column": (inner, "end", "column"),
                "outer-begin-byte": (outer, "begin", "byte"),
                "outer-begin-column": (outer, "begin", "column"),
                "predicate-end-byte": (predicate, "end", "byte"),
                "predicate-end-column": (predicate, "end", "column"),
            }
            for label, (node, field, coordinate) in variants.items():
                with self.subTest(label=label):
                    candidate = json.loads(normalized.stdout)
                    forged = candidate["nodes"][node["id"] - 1]
                    if coordinate is None:
                        forged[field] += 1
                    else:
                        forged["span"][field][coordinate] += 1
                    guest = Path(scratch) / f"{label}.malbolge"
                    result = self.project(json.dumps(candidate).encode(), guest)
                    self.assertIn(b"normalized frontend rejected", result.stderr)
                    self.assertFalse(guest.exists())
