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

import subprocess
import sys
import tempfile
import unittest
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
    def test_complete_c_program_refuses_unconverted_signed_eof(self) -> None:
        """Unsigned loop induction does not imply that getchar succeeds."""
        required = (
            FRONTEND,
            RUST_BIN / "c2malbolge_json",
            RUST_BIN / "malbolge_layout",
        )
        if not all(path.is_file() for path in required) or not RESOURCE.is_dir():
            self.skipTest("pinned compiler tools required")

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
                timeout=60,
            )
            self.assertNotEqual(compiled.returncode, 0)
            self.assertIn(b"Unsupported", compiled.stderr)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    _ = unittest.main()
