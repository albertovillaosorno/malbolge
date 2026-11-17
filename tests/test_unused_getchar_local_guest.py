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
#   - Real C23 same-line signed local overwrites with unobserved values.
# - Must-Not:
#   - Project EOF as a successful byte or omit an observable local read.
# - Allows:
#   - Inputs: source-checked local assignments and finite binary stdin.
#   - Outputs: real guest reads or typed refusal without guest publication.
#   - Side effects: pinned Clang, compiler and VM in temporary directories.
# - Split-When:
#   - General mutable guest storage supersedes unobserved local overwrites.
# - Merge-When:
#   - P2 guest EOF parity handles all source-C local lifetimes.
# - Summary:
#   - Mutating an unobserved local must still perform every signed read.

"""Native C and real guest agreement for unobserved signed local updates."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Final, final

ROOT: Final = Path(__file__).resolve().parents[1]
CLANG: Final = ROOT / ".dependencies/llvm/22.1.8/bin/clang"
DRIVER: Final = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
VM: Final = ROOT / ".cache/rust/target/debug/malbolge"
VECTORS: Final = (b"", b"\x00", b"\xff", b"\x80\x01\x00", b"\xff\x01\xfe\x00")
# The 15-trit VM requires a large real memory image per subprocess.
GUEST_VECTORS: Final = (b"", b"\xff")
# The read count is also the count of actual VM input instructions.
ACCEPTED: Final = (
    ("same-line-reassignment", "int value = getchar(); value = getchar();", 2),
    (
        "repeated-same-line-reassignment",
        "int value = getchar(); value = getchar(); value = getchar();",
        3,
    ),
    (
        "interleaved-local-reassignment",
        "int first = getchar(); int second = getchar(); first = getchar();",
        3,
    ),
    (
        "same-line-with-return",
        "int value = getchar(); value = getchar(); return;",
        2,
    ),
)


def source_for(body: str) -> str:
    return f"#include <stdio.h>\nvoid emit(void) {{\n    {body}\n}}\n"


def native_binary(directory: Path, source: Path, optimization: str) -> Path:
    wrapper = directory / "main.c"
    _ = wrapper.write_text(
        f'#include "{source.name}"\nint main(void) {{ emit(); return 0; }}\n',
        encoding="utf-8",
    )
    binary = directory / f"native-{optimization[2:]}"
    env = os.environ.copy()
    llvm_lib = str(ROOT / ".dependencies/llvm/22.1.8/lib")
    env["LD_LIBRARY_PATH"] = os.pathsep.join(
        part for part in (llvm_lib, env.get("LD_LIBRARY_PATH", "")) if part
    )
    built = subprocess.run(
        [
            str(CLANG),
            "-std=c23",
            optimization,
            "-Wall",
            "-Wextra",
            "-Werror",
            "-Wno-unused-variable",
            "-Wno-unused-but-set-variable",
            "-fsanitize=undefined",
            "-fno-sanitize-recover=all",
            str(wrapper),
            "-o",
            str(binary),
        ],
        capture_output=True,
        check=False,
        env=env,
        timeout=10,
    )
    if built.returncode:
        raise AssertionError(built.stderr.decode(errors="replace"))
    return binary


@final
class UnobservedSignedLocalTests(unittest.TestCase):
    def test_same_line_overwrites_execute_real_guest_reads(self) -> None:
        self.assertTrue(CLANG.is_file())
        self.assertTrue(VM.is_file())
        for name, body, reads in ACCEPTED:
            with (
                self.subTest(source=name),
                tempfile.TemporaryDirectory(dir=ROOT / ".temp") as raw,
            ):
                directory = Path(raw)
                source = directory / "sample.c"
                _ = source.write_text(source_for(body), encoding="utf-8")
                for optimization in ("-O0", "-O2"):
                    native = native_binary(directory, source, optimization)
                    for data in VECTORS:
                        result = subprocess.run(
                            [str(native)],
                            input=data,
                            capture_output=True,
                            check=False,
                            timeout=10,
                        )
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(result.stdout, b"")
                guest_file = directory / "sample.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--capsule",
                        "--max-wall-seconds",
                        "30",
                        "--output",
                        str(guest_file),
                        str(source),
                    ],
                    capture_output=True,
                    check=False,
                    timeout=35,
                )
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                self.assertTrue(guest_file.is_file())
                for data in GUEST_VECTORS:
                    with self.subTest(source=name, stdin=data):
                        guest = subprocess.run(
                            [
                                str(VM),
                                str(guest_file),
                                "--input-stdin",
                                "--report-steps",
                                "--max-steps",
                                "100",
                            ],
                            input=data,
                            capture_output=True,
                            check=False,
                            timeout=25,
                        )
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        self.assertEqual(guest.stdout, b"")
                        self.assertIn(
                            f"malbolge-steps-v1:{reads + 1}".encode(),
                            guest.stderr,
                        )

    def test_observable_signed_eof_local_must_refuse(self) -> None:
        for body in (
            "int value = getchar(); value = getchar(); putchar(value);",
            "int value = getchar(); value = getchar(); putchar(value); return;",
        ):
            with (
                self.subTest(body=body),
                tempfile.TemporaryDirectory(dir=ROOT / ".temp") as raw,
            ):
                directory = Path(raw)
                source = directory / "sample.c"
                _ = source.write_text(source_for(body), encoding="utf-8")
                target = directory / "guest.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--capsule",
                        "--max-wall-seconds",
                        "30",
                        "--output",
                        str(target),
                        str(source),
                    ],
                    capture_output=True,
                    check=False,
                    timeout=35,
                )
                self.assertNotEqual(compiled.returncode, 0)
                self.assertIn(b"Unsupported", compiled.stderr)
                self.assertFalse(target.exists())
                for optimization in ("-O0", "-O2"):
                    native = native_binary(directory, source, optimization)
                    for data, expected in ((b"", b"\xff"), (b"\x00\x80", b"\x80")):
                        result = subprocess.run(
                            [str(native)],
                            input=data,
                            capture_output=True,
                            check=False,
                            timeout=10,
                        )
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(result.stdout, expected)


if __name__ == "__main__":
    _ = unittest.main()
