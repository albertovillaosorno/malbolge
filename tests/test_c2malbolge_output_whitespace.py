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
#   - Pinned native C whitespace through compiler and normative guest VM.
# - Must-Not:
#   - Substitute host putchar output or synthetic AST for source compilation.
# - Allows:
#   - Inputs: bounded source calls and pinned compiler tools.
#   - Outputs: exact guest output bytes, steps and rejection receipts.
#   - Side effects: ignored, isolated C source and capsule files only.
# - Split-When:
#   - General compiler integration replaces bounded whitespace handling.
# - Merge-When:
#   - A broad source-to-guest whitespace compatibility suite is established.
# - Summary:
#   - Ordinary spaced C calls retain the same executable guest semantics.
# - Description:
#   - Exercises the complete checked source-to-Malbolge VM pipeline.
# - Usage:
#   - MALBOLGE_WHITESPACE_BIN_ROOT=/path/to/debug python3.14 -B -m unittest
#     tests.test_c2malbolge_output_whitespace -v
# - Defaults:
#   - Skip only when the pinned native toolchain is unavailable.

"""Real source spacing reaches real verified guest Malbolge byte output."""

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
    os.environ.get(
        "MALBOLGE_WHITESPACE_BIN_ROOT", str(ROOT / ".cache/rust/target/debug")
    )
)
ADAPTER = BIN_ROOT / "c2malbolge_json"
LAYOUT = BIN_ROOT / "malbolge_layout"
VM = BIN_ROOT / "malbolge"


@final
class WhitespaceCSourcePipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        executables = (FRONTEND, ADAPTER, LAYOUT, VM)
        if (
            not GUEST_INCLUDE.is_dir()
            or not RESOURCE.is_dir()
            or any(
                not path.is_file() or not os.access(path, os.X_OK)
                for path in executables
            )
        ):
            if "MALBOLGE_WHITESPACE_BIN_ROOT" in os.environ:
                self.fail("explicit pinned compiler or VM binary unavailable")
            self.skipTest("pinned C frontend, layout and guest VM required")

    def compile(self, source: Path, output: Path) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
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
                source.name,
                "--output",
                str(output),
                "--capsule",
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=160,
        )

    def test_whitespace_variants_execute_normative_guest_bytes(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            directory = Path(folder)
            for name, statements, expected, steps in (
                ("callee-gap", "putchar (65);", b"A", 31),
                ("argument-gap", "putchar( 65 );", b"A", 31),
                ("nested-gap", "putchar( ( 65 ) );", b"A", 31),
                ("unary-gap", "putchar( - (191) );", b"A", 31),
                (
                    "mixed-gap",
                    "putchar( 0 ); putchar ( 90 );",
                    b"\x00Z",
                    5,
                ),
                (
                    "distinct-gap",
                    "putchar ( 'Q' ); putchar ( '.' );",
                    b"Q.",
                    8,
                ),
            ):
                with self.subTest(name=name):
                    source = directory / f"{name}.c"
                    output = directory / f"{name}.malbolge"
                    _ = source.write_text(
                        "#include <stdio.h>\nvoid emit(void) { " + statements + " }\n",
                        encoding="ascii",
                    )
                    compiled = self.compile(source, output)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(output.is_file())
                    executed = subprocess.run(
                        [str(VM), str(output), "--report-steps"],
                        capture_output=True,
                        check=False,
                        timeout=60,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, expected)
                    self.assertEqual(
                        executed.stderr,
                        f"malbolge-steps-v1:{steps}\n".encode("ascii"),
                    )

    def test_arithmetic_or_extra_unary_never_publish(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            directory = Path(folder)
            for name, statement in (
                ("arithmetic", "putchar ( 65 + 0 );"),
                ("double-unary", "putchar( -(-191) );"),
            ):
                with self.subTest(name=name):
                    source = directory / f"{name}.c"
                    output = directory / f"{name}.malbolge"
                    _ = source.write_text(
                        "#include <stdio.h>\nvoid emit(void) { " + statement + " }\n",
                        encoding="ascii",
                    )
                    compiled = self.compile(source, output)
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(output.exists())


if __name__ == "__main__":
    _ = unittest.main()
