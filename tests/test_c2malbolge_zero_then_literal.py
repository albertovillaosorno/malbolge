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
#   - Real pinned C input to zero-then-printable Malbolge VM output evidence.
# - Must-Not:
#   - Substitute synthetic frontend JSON or host-side C execution.
# - Allows:
#   - Inputs: exact source-bound constant putchar calls and pinned compiler.
#   - Outputs: real capsule, guest bytes/steps or nonpublication.
#   - Side effects: temporary project-local C and guest fixtures only.
# - Split-When:
#   - General mixed constant compilation subsumes this closed source pair.
# - Merge-When:
#   - A full compiled-C integration suite owns distinct-byte output programs.
# - Summary:
#   - Two distinct source C bytes execute in order on the normative guest VM.
# - Description:
#   - Source -> Clang -> JSON -> canonical MCTI/MCTR -> VM, not a mock.
# - Usage:
#   - MALBOLGE_ZERO_LITERAL_BIN_ROOT=/path/to/target/debug python3 -m unittest
#     tests.test_c2malbolge_zero_then_literal -v
# - Defaults:
#   - Skip only when the pinned toolchain is unavailable.

"""Real source C mixed literal byte programs under the normative guest VM."""

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
RUST = Path(
    os.environ.get(
        "MALBOLGE_ZERO_LITERAL_BIN_ROOT", str(ROOT / ".cache/rust/target/debug")
    )
)
ADAPTER = RUST / "c2malbolge_json"
LAYOUT = RUST / "malbolge_layout"
VM = RUST / "malbolge"


@final
class ZeroThenLiteralNativeTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        tools = (FRONTEND, ADAPTER, LAYOUT, VM)
        if (
            not GUEST_INCLUDE.is_dir()
            or not RESOURCE.is_dir()
            or any(not path.is_file() or not os.access(path, os.X_OK) for path in tools)
        ):
            if "MALBOLGE_ZERO_LITERAL_BIN_ROOT" in os.environ:
                self.fail("explicit zero-then-literal tool binaries are unavailable")
            self.skipTest("pinned native Clang and compiled guest binaries required")

    def compile_source(
        self, directory: Path, name: str, statements: str
    ) -> tuple[subprocess.CompletedProcess[bytes], Path]:
        source = directory / f"{name}.c"
        target = directory / f"{name}.malbolge"
        _ = source.write_text(
            "#include <stdio.h>\nvoid emit(void) { " + statements + " }\n",
            encoding="ascii",
        )
        process = subprocess.run(
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
                str(target),
                "--capsule",
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=90,
        )
        return process, target

    def test_real_c_zero_then_distinct_printable_guest(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            directory = Path(temporary)
            for byte, padding, source in (
                (b"Z", 0, "putchar(0); putchar('Z');"),
                (b"P", 2, "putchar((0)); putchar(80);"),
                (b"T", 6, "putchar(0); putchar(+84);"),
                (b"S", 17, "putchar(-0); putchar(0x53);"),
            ):
                with self.subTest(output=byte):
                    result, target = self.compile_source(
                        directory, byte.decode(), source
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
                    self.assertEqual(guest.stdout, b"\x00" + byte)
                    self.assertEqual(
                        guest.stderr,
                        f"malbolge-steps-v1:{padding + 5}\n".encode(),
                    )

    def test_other_byte_transitions_do_not_publish(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            directory = Path(temporary)
            for name, statements in (
                ("unwitnessed", "putchar(0); putchar('A');"),
                ("reverse", "putchar('Z'); putchar(0);"),
                ("third", "putchar(0); putchar('Z'); putchar('Z');"),
                ("zero-prefix-double", "putchar(0); putchar(0); putchar('Z');"),
                ("unproved-arithmetic", "putchar(0); putchar('Z' + 0);"),
            ):
                with self.subTest(name=name):
                    result, target = self.compile_source(directory, name, statements)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_old_repeated_zero_path_unchanged(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            directory = Path(temporary)
            result, target = self.compile_source(
                directory, "repeated-zero", "putchar(0); putchar(0);"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            guest = subprocess.run(
                [str(VM), str(target), "--report-steps"],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(guest.returncode, 0, guest.stderr)
            self.assertEqual(guest.stdout, b"\x00\x00")
            self.assertEqual(guest.stderr, b"malbolge-steps-v1:3\n")


if __name__ == "__main__":
    _ = unittest.main()
