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
#   - Real C-to-Malbolge four-distinct-byte source/output regression.
# - Must-Not:
#   - Replace the pinned Clang frontend or the real guest VM with a host oracle.
# - Allows:
#   - Inputs: bounded literal-output C and built repository compiler binaries.
#   - Outputs: real guest bytes and exact VM step receipts; absent rejected output.
#   - Side effects: isolated project-local temporary files only.
# - Split-When:
#   - General C byte stream code generation subsumes finite quadruple witnesses.
# - Merge-When:
#   - Public compiler tests own the same four-byte source/output boundary.
# - Summary:
#   - Four independent guest CrazyData outputs implement exact T=4> C source.
# - Description:
#   - Proves publication through the pinned frontend and normative guest VM.
# - Usage:
#   - python3.14 -B -m unittest tests.test_c2malbolge_distinct_literal_quad -v
# - Defaults:
#   - No other four-output sequence or partial-prefix source is admitted.

"""Real pinned C frontend to four distinct guest-computed Malbolge bytes."""

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
    os.environ.get("MALBOLGE_QUAD_BIN_ROOT", str(ROOT / ".cache/rust/target/debug"))
)
ADAPTER = BIN_ROOT / "c2malbolge_json"
LAYOUT = BIN_ROOT / "malbolge_layout"
VM = BIN_ROOT / "malbolge"


@final
class DistinctLiteralQuadSourceTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        tools = (FRONTEND, ADAPTER, LAYOUT, VM)
        if (
            not GUEST_INCLUDE.is_dir()
            or not RESOURCE.is_dir()
            or any(not path.is_file() or not os.access(path, os.X_OK) for path in tools)
        ):
            if "MALBOLGE_QUAD_BIN_ROOT" in os.environ:
                self.fail("explicit pinned compiler/VM binaries unavailable")
            self.skipTest("pinned compiler and normative guest VM required")

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
            timeout=180,
        )
        return result, guest

    def test_four_distinct_c_literals_execute_in_real_vm(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as name:
            directory = Path(name)
            compiled, artifact = self.compile(
                directory,
                "four-guest-bytes",
                "putchar('T'); putchar('='); putchar('4'); putchar('>');",
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(artifact.is_file())
            guest = subprocess.run(
                [str(VM), str(artifact), "--report-steps"],
                capture_output=True,
                check=False,
                timeout=60,
            )
            self.assertEqual(guest.returncode, 0, guest.stderr)
            self.assertEqual(guest.stdout, b"T=4>")
            self.assertEqual(guest.stderr, b"malbolge-steps-v1:21\n")

    def test_unsupported_quadruples_and_prefixes_never_publish(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as name:
            directory = Path(name)
            for stem, statements in (
                (
                    "bad-fourth",
                    "putchar('T'); putchar('='); putchar('4'); putchar('?');",
                ),
                ("missing-fourth", "putchar('T'); putchar('='); putchar('4');"),
                ("missing-third", "putchar('T'); putchar('=');"),
                (
                    "extra",
                    "putchar('T'); putchar('='); putchar('4'); putchar('>'); putchar('!');",
                ),
                (
                    "arithmetic",
                    "putchar('T'); putchar('='); putchar('4' + 0); putchar('>');",
                ),
            ):
                with self.subTest(name=stem):
                    compiled, artifact = self.compile(directory, stem, statements)
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(artifact.exists())


if __name__ == "__main__":
    _ = unittest.main()
