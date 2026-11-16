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
#   - Native C-to-Malbolge guest parity for unsigned scalar induction truth.
# - Must-Not:
#   - Substitute a host echo, synthetic JSON or guest input default.
# - Allows:
#   - Inputs: pinned frontend, adapter, backend and isolated input vectors.
#   - Outputs: exact four-read/seven-write VM parity and instruction counts.
#   - Side effects: temporary test artifacts under the ignored .temp root.
# - Split-When:
#   - An all-source guest stream oracle owns this counter grammar.
# - Merge-When:
#   - End-to-end compiler parity suites share the same pinned tool harness.
# - Summary:
#   - Unsigned scalar branch truth must preserve actual guest byte provenance.

"""Source-authenticated unsigned counter truth through the real guest VM."""

from __future__ import annotations

import random
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import final

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
ACCEPTED_DIR = ROOT / "tests/compiler/c-frontend/accepted"
FRONTEND_DIR = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin"
SOURCE = ACCEPTED_DIR / "unsigned_scalar_truth_live_input.c"
FRONTEND = FRONTEND_DIR / "malbolge-c-frontend"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
RUST_BIN = ROOT / ".cache/rust/target/debug"
VM = RUST_BIN / "malbolge"


@final
class UnsignedScalarTruthGuestParityTests(unittest.TestCase):
    def test_complete_c_program_preserves_guest_input(self) -> None:
        required = (
            FRONTEND,
            RUST_BIN / "c2malbolge_json",
            RUST_BIN / "malbolge_layout",
            VM,
        )
        binaries_present = all(path.is_file() for path in required)
        if not binaries_present or not RESOURCE.is_dir():
            self.skipTest("pinned compiler and VM executables required")

        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as root:
            target = Path(root) / "unsigned-scalar-truth.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--capsule",
                    "--output",
                    str(target),
                    str(SOURCE),
                ],
                capture_output=True,
                check=False,
                timeout=120,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(target.is_file())

            seeded = random.Random(0xBAD5CA1A)
            inputs = [
                b"ABCD",
                b"\x00\xff\x80\x01",
                b"\n\x00\xfe\xff",
                b"\xff\xff\xff\xff",
                b"\x00\x00\x00\x00",
            ]
            inputs.extend(
                bytes(seeded.getrandbits(8) for _ in range(4)) for _ in range(8)
            )

            # Each normative VM process has independent memory and stdin.
            # Bounded parallel replay avoids serial loader initialization.
            def run_guest(data: bytes) -> subprocess.CompletedProcess[bytes]:
                return subprocess.run(
                    [str(VM), str(target), "--input-stdin", "--report-steps"],
                    input=data,
                    capture_output=True,
                    check=False,
                    timeout=40,
                )

            expected_steps = b"malbolge-steps-v1:12\n"
            with ThreadPoolExecutor(max_workers=4) as executor:
                for data, executed in zip(
                    inputs, executor.map(run_guest, inputs), strict=True
                ):
                    with self.subTest(input=data.hex()):
                        expected = data[:1] + b"".join(
                            bytes((value, value)) for value in data[1:]
                        )
                        self.assertFalse(executed.returncode, executed.stderr)
                        self.assertEqual(executed.stdout, expected)
                        self.assertEqual(executed.stderr, expected_steps)


if __name__ == "__main__":
    _ = unittest.main()
