# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - LicenseRef-Proprietary
# Confidential:
#   - true
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - Actual pinned source C to three different guest Malbolge bytes.
# - Must-Not:
#   - Mock Clang, synthesize guest bytes in Python or bypass VM checks.
# - Allows:
#   - Inputs: C calls, pinned frontend, backend and normative real VM.
#   - Outputs: exact source-derived guest stdout/steps; rejected artifacts.
#   - Side effects: project-local isolated source/artifact fixtures only.
# - Split-When:
#   - General C byte sequence integration supersedes finite literal triples.
# - Merge-When:
#   - Source integration owns full arbitrary byte write sequences.
# - Summary:
#   - Full C->IR->MCTR->Malbolge->VM three-byte proofs.
# - Description:
#   - Tests exact three independently observed guest arithmetic outputs.
# - Usage:
#   - python3.14 -B -m unittest tests.test_c2malbolge_distinct_literal_triplet -v
# - Defaults:
#   - Reject unproved mixed source outputs without publishing an artifact.

"""Real source-to-guest triple byte output, no host-side substitution."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import final, override

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
GUEST_INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
BIN_ROOT = Path(
    os.environ.get("MALBOLGE_TRIPLE_BIN_ROOT", str(ROOT / ".cache/rust/target/debug"))
)
ADAPTER = BIN_ROOT / "c2malbolge_json"
LAYOUT = BIN_ROOT / "malbolge_layout"
VM = BIN_ROOT / "malbolge"


@final
class DistinctLiteralTripleSourceTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        tools = (FRONTEND, ADAPTER, LAYOUT, VM)
        if (
            not GUEST_INCLUDE.is_dir()
            or not RESOURCE.is_dir()
            or any(not path.is_file() or not os.access(path, os.X_OK) for path in tools)
        ):
            if "MALBOLGE_TRIPLE_BIN_ROOT" in os.environ:
                self.fail("explicit pinned compiler/VM binary unavailable")
            self.skipTest("pinned compiler and guest VM required")

    def compile(
        self, directory: Path, name: str, statements: str
    ) -> tuple[subprocess.CompletedProcess[bytes], Path]:
        source = directory / f"{name}.c"
        guest = directory / f"{name}.malbolge"
        _ = source.write_text(
            "#include <stdio.h>\nvoid emit(void) { " + statements + " }\n",
            encoding="ascii",
        )
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(DRIVER),
                "--frontend",
                str(FRONTEND),
                "--json-adapter",
                str(ADAPTER),
                "--layout-backend",
                str(LAYOUT),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                f"fixtures/{name}.c",
                "--output",
                str(guest),
                "--capsule",
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=160,
        )
        return result, guest

    def test_three_distinct_c_literals_execute_in_real_vm(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as name:
            directory = Path(name)
            for stem, statements, expected, steps in (
                ("z-percent-h", "putchar('Z'); putchar('%'); putchar('H');", b"Z%H", 8),
                ("q-period-o", "putchar('Q'); putchar('.'); putchar('O');", b"Q.O", 9),
                ("y-hyphen-p", "putchar('Y'); putchar('-'); putchar('P');", b"Y-P", 10),
            ):
                with self.subTest(name=stem):
                    compiled, artifact = self.compile(directory, stem, statements)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(artifact.is_file())
                    guest = subprocess.run(
                        [str(VM), str(artifact), "--report-steps"],
                        capture_output=True,
                        check=False,
                        timeout=60,
                    )
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(guest.stdout, expected)
                    self.assertEqual(
                        guest.stderr,
                        f"malbolge-steps-v1:{steps}\n".encode(),
                    )

    def test_unproved_triplets_never_publish(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as name:
            directory = Path(name)
            for stem, statements in (
                ("wrong-third", "putchar('Q'); putchar('.'); putchar('Z');"),
                ("wrong-middle", "putchar('Y'); putchar('/'); putchar('P');"),
                ("not-triple", "putchar('Z'); putchar('%');"),
                ("extra", "putchar('Q'); putchar('.'); putchar('O'); putchar('!');"),
            ):
                with self.subTest(name=stem):
                    compiled, artifact = self.compile(directory, stem, statements)
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(artifact.exists())


if __name__ == "__main__":
    _ = unittest.main()
