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
#   - End-to-end unary signed putchar C source through pinned native Clang.
# - Must-Not:
#   - Mock normalized JSON, execute C on host, or bypass the normative guest VM.
# - Allows:
#   - Inputs: exact pinned frontend, Rust adapter, layout, and VM executables.
#   - Outputs: checked signed low-byte guest stdout and no-publication failures.
#   - Side effects: temporary source and guest artifacts in repository .temp.
# - Split-When:
#   - General C expression lowering supersedes the single-unary source shape.
# - Merge-When:
#   - The source-to-guest regression suite owns all signed literal cases.
# - Summary:
#   - A signed C unary expression actually emits a verified Malbolge byte.
# - Description:
#   - The pinned Clang source JSON and real VM execute, never host C output.
# - Usage:
#   - python3.14 -B -m unittest tests.test_c2malbolge_signed_unary -v
# - Defaults:
#   - MALBOLGE_UNARY_ADAPTER can select an isolated candidate Rust binary.

"""Real pinned Clang signed source effects reach the normative Malbolge VM."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import final, override

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
GUEST_INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
RUST = ROOT / ".cache/rust/target/debug"
VM = RUST / "malbolge"
LAYOUT = RUST / "malbolge_layout"
ADAPTER = Path(os.environ.get("MALBOLGE_UNARY_ADAPTER", str(RUST / "c2malbolge_json")))


@final
class SignedUnaryCompilerTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        executables = (FRONTEND, VM, LAYOUT, ADAPTER)
        if (
            not RESOURCE.is_dir()
            or not GUEST_INCLUDE.is_dir()
            or any(
                not path.is_file() or not os.access(path, os.X_OK)
                for path in executables
            )
        ):
            self.skipTest("pinned C frontend, JSON adapter, layout and VM are required")

    def compile_source(
        self, work: Path, statements: str, name: str
    ) -> tuple[subprocess.CompletedProcess[bytes], Path]:
        source = work / f"{name}.c"
        target = work / f"{name}.malbolge"
        _ = source.write_text(
            "#include <stdio.h>\nvoid emit(void) { " + statements + " }\n",
            encoding="ascii",
        )
        result = subprocess.run(
            [
                "python3.14",
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

    def test_signed_unary_c_literals_emit_actual_guest_bytes(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            work = Path(temporary)
            cases = (
                ("positive", "putchar(+65);", b"A"),
                ("negative", "putchar(-191);", b"A"),
                ("negative-parenthesized", "putchar(-(191));", b"A"),
                ("negative-parenthesized-zero", "putchar(-(0));", b"\x00"),
                ("positive-double-parenthesized-zero", "putchar(+((0)));", b"\x00"),
                (
                    "signed-and-plain-same-byte",
                    "putchar(-(191)); putchar(65);",
                    b"AA",
                ),
                ("fifteen-negative-one", "putchar(-1);" * 15, b"\xff" * 15),
            )
            for name, source, expected in cases:
                with self.subTest(name=name):
                    compiled, target = self.compile_source(work, source, name)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(target.is_file())
                    executed = subprocess.run(
                        [str(VM), str(target), "--report-steps"],
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, expected)
                    self.assertTrue(
                        executed.stderr.startswith(b"malbolge-steps-v1:"),
                        executed.stderr,
                    )

    def test_unimplemented_unary_arithmetic_never_publishes_guest(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            work = Path(temporary)
            for name, source in (
                ("bitwise", "putchar(~65);"),
                ("nested-unary", "putchar(-( +1 ));"),
            ):
                with self.subTest(name=name):
                    result, target = self.compile_source(work, source, name)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())
