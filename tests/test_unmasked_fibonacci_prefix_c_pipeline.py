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
#   - Full source-C unmasked Fibonacci guest VM proof.
# - Must-Not:
#   - Replace guest arithmetic with host output or publish unsupported C.
# - Allows:
#   - Inputs: pinned C frontend, JSON projector and guest VM.
#   - Outputs: an admitted guest stream or a typed refusal.
#   - Side effects: local temporary compiler and VM execution.
# - Split-When:
#   - General guest runtime state supersedes source projection.
# - Merge-When:
#   - Full unmasked Fibonacci production guest covers the same prefix.
# - Summary:
#   - Evolved guest scratch emits the full original twelve-byte recurrence.

"""Original full Fibonacci reaches the VM through evolved guest scratch."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests/compiler/c-frontend/accepted/conditional_fibonacci.c"
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
ADAPTER = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT = ROOT / ".cache/rust/target/debug/malbolge_layout"
VM = ROOT / ".cache/rust/target/debug/malbolge"


def original_oracle(count: int) -> bytes:
    previous, current = 1, 1
    output = bytearray()
    for _ in range(count):
        following = (previous + current) & 255
        output.append(following if following % 2 == 0 else following ^ 0x5A)
        previous, current = current, following
    return bytes(output)


class UnmaskedFibonacciPrefixPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler and VM binaries are not built")

    @staticmethod
    def compile(source: Path, guest: Path) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/unmasked-fibonacci-prefix-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ],
            check=False,
            capture_output=True,
            timeout=260,
        )

    def test_original_three_trip_c_reaches_normative_vm(self) -> None:
        original = SOURCE.read_text()
        self.assertIn("i < 12U", original)
        expected = original_oracle(3)
        self.assertEqual(expected, bytes.fromhex("02595f"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "original-fibonacci-three.c"
            source.write_text(original.replace("i < 12U", "i < 3U"))
            guest = Path(folder) / "original-fibonacci-three.malbolge"
            result = self.compile(source, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                execution = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(execution.returncode, 0, execution.stderr)
                self.assertEqual(execution.stdout, expected)
                self.assertRegex(
                    execution.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                )

    def test_undefined_selected_c_expression_never_publishes(self) -> None:
        original = SOURCE.read_text()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "undefined-fibonacci-three.c"
            source.write_text(
                original.replace("i < 12U", "i < 3U").replace(
                    "next ^ 0x5AU", "next / 0U"
                )
            )
            guest = Path(folder) / "undefined-fibonacci-three.malbolge"
            result = self.compile(source, guest)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"Unsupported", result.stderr)
            self.assertFalse(guest.exists())

    def test_original_twelve_trip_c_reaches_normative_vm(self) -> None:
        expected = original_oracle(12)
        self.assertEqual(expected, bytes.fromhex("02595f08574f226d0390b323"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            guest = Path(folder) / "original-fibonacci-twelve.malbolge"
            result = self.compile(SOURCE, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                execution = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(execution.returncode, 0, execution.stderr)
                self.assertEqual(execution.stdout, expected)
                self.assertRegex(
                    execution.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                )
