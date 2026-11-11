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
#   - Real pinned-Clang parenthesized literal C to normative Malbolge effects.
# - Must-Not:
#   - Mock source JSON, execute host C, or bypass target VM verification.
# - Allows:
#   - Inputs: bounded C putchar constants and exact pinned compiler tools.
#   - Outputs: verified single-byte guest output or rejected C source.
#   - Side effects: temporary sources and capsules inside repository .temp.
# - Split-When:
#   - General expression lowering supersedes bounded nested argument handling.
# - Merge-When:
#   - One public end-to-end suite owns all C literal argument variants.
# - Summary:
#   - Nested parentheses around a literal survive Clang-to-Malbolge lowering.
# - Description:
#   - C source and the generated capsule execute with the actual target VM.
# - Usage:
#   - MALBOLGE_PAREN_ADAPTER=/path/to/c2malbolge_json python3.14 -B -m unittest
#     tests.test_c2malbolge_parenthesized_output -v
# - Defaults:
#   - Use repository compiler tools and skip if they are not provisioned.

"""Real C parentheses and signed/unsigned literals reach verified guest output."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import final, override

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
FRONTEND_NAME = "malbolge-c-frontend.exe" if os.name == "nt" else "malbolge-c-frontend"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin" / FRONTEND_NAME
GUEST_INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
RUST = ROOT / ".cache/rust/target/debug"
RUST_SUFFIX = ".exe" if os.name == "nt" else ""
VM = RUST / f"malbolge{RUST_SUFFIX}"
LAYOUT = RUST / f"malbolge_layout{RUST_SUFFIX}"
ADAPTER = Path(
    os.environ.get(
        "MALBOLGE_PAREN_ADAPTER", str(RUST / f"c2malbolge_json{RUST_SUFFIX}")
    )
)


@final
class ParenthesizedCCompilerTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if (
            not GUEST_INCLUDE.is_dir()
            or not RESOURCE.is_dir()
            or any(
                not path.is_file() or not os.access(path, os.X_OK)
                for path in (FRONTEND, ADAPTER, LAYOUT, VM)
            )
        ):
            self.skipTest("pinned C compiler and normative guest VM required")

    def compile_source(
        self, directory: Path, name: str, statements: str
    ) -> tuple[subprocess.CompletedProcess[bytes], Path]:
        source = directory / f"{name}.c"
        target = directory / f"{name}.malbolge"
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
                source.name,
                "--output",
                str(target),
                "--capsule",
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=120,
        )
        return result, target

    def test_parenthesized_signed_and_unsigned_literals_emit_guest_a(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            directory = Path(temporary)
            for name, argument in (
                ("triple", "(((65)))"),
                ("signed", "((-191))"),
                ("unsigned", "((65u))"),
                ("signed-triple", "(((+65)))"),
                ("outer-positive", "+((65))"),
                ("outer-negative", "-((191))"),
                ("mixed-negative", "(-(191))"),
            ):
                with self.subTest(argument=argument):
                    result, target = self.compile_source(
                        directory, name, f"putchar({argument});"
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertTrue(target.is_file())
                    guest = subprocess.run(
                        [str(VM), str(target), "--report-steps"],
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(guest.stdout, b"A")
                    self.assertEqual(guest.stderr, b"malbolge-steps-v1:31\n")

    def test_mixed_wrapper_depths_keep_two_guest_calls_ordered(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            directory = Path(temporary)
            result, target = self.compile_source(
                directory, "two-wrappers", "putchar((65)); putchar(((65)));"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(target.is_file())
            guest = subprocess.run(
                [str(VM), str(target), "--report-steps"],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(guest.returncode, 0, guest.stderr)
            self.assertEqual(guest.stdout, b"AA")
            self.assertEqual(guest.stderr, b"malbolge-steps-v1:27\n")

    def test_later_invalid_or_mismatched_call_never_publishes(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            directory = Path(temporary)
            for name, statements in (
                ("too-deep-later", "putchar(65); putchar(((((65)))));"),
                ("mixed-bytes", "putchar((65)); putchar(((66)));"),
            ):
                with self.subTest(name=name):
                    result, target = self.compile_source(directory, name, statements)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_unadmitted_argument_expressions_never_publish(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            directory = Path(temporary)
            for name, argument in (
                ("four-level", "((((65))))"),
                ("two-signs", "-(+65)"),
                ("unary-arithmetic", "-(65 + 0)"),
                ("arithmetic", "65 + 0"),
            ):
                with self.subTest(argument=argument):
                    result, target = self.compile_source(
                        directory, name, f"putchar({argument});"
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())
