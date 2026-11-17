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
#   - Native-C and real-guest EOF parity for signed local getchar aliases.
# - Must-Not:
#   - Conflate profile EOF residue with C unsigned-char conversion.
# - Allows:
#   - Inputs: four frozen local C23 forms and four binary stdin vectors.
#   - Outputs: native/guest parity or typed refusal without guest publication.
#   - Side effects: bounded isolated compiler and VM processes.
# - Split-When:
#   - General C local EOF branching gains a guest runtime implementation.
# - Merge-When:
#   - The complete P2 mutable EOF checksum proves local-state semantics.
# - Summary:
#   - Unconditional local aliases cannot turn signed EOF into guest 0x6a.

"""Signed getchar locals must not silently publish incorrect EOF echoes."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Final, final

ROOT: Final = Path(__file__).resolve().parents[1]
DRIVER: Final = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
CLANG: Final = ROOT / ".dependencies/llvm/22.1.8/bin/clang"
FRONTEND: Final = (
    ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
)
ADAPTER: Final = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT: Final = ROOT / ".cache/rust/target/debug/malbolge_layout"
VM: Final = ROOT / ".cache/rust/target/debug/malbolge"
SHAPES: Final = (
    ("direct-local", "int current = getchar();\n    putchar(current);", 1),
    (
        "discard-after-output",
        "int current = getchar();\n    putchar(current);\n    getchar();",
        1,
    ),
    (
        "copied-local",
        "int current = getchar();\n    int saved = current;\n    putchar(saved);",
        1,
    ),
    (
        "repeated-local",
        "int current = getchar();\n    putchar(current);\n    putchar(current);",
        2,
    ),
)
VECTORS: Final = (
    ("eof", b"", 255),
    ("nul", b"\x00", 0),
    ("high", b"\xff", 255),
    ("truncated", b"\x05\x80", 5),
)


@final
class SignedGetcharLocalPublicationTests(unittest.TestCase):
    def test_native_and_guest_or_typed_refusal(self) -> None:
        if not all(
            binary.is_file() for binary in (CLANG, FRONTEND, ADAPTER, LAYOUT, VM)
        ):
            self.skipTest("pinned Clang/frontend/adapter/layout/VM required")
        env = os.environ.copy()
        llvm_lib = str(ROOT / ".dependencies/llvm/22.1.8/lib")
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            part for part in (llvm_lib, env.get("LD_LIBRARY_PATH", "")) if part
        )
        for label, body, writes in SHAPES:
            with (
                self.subTest(shape=label),
                tempfile.TemporaryDirectory(dir=ROOT / ".temp") as raw,
            ):
                directory = Path(raw)
                source = directory / "local.c"
                _ = source.write_text(
                    f"#include <stdio.h>\nvoid emit(void) {{\n    {body}\n}}\n",
                    encoding="utf-8",
                )
                wrapper = directory / "main.c"
                _ = wrapper.write_text(
                    '#include "local.c"\nint main(void) { emit(); return 0; }\n',
                    encoding="utf-8",
                )
                expected = {
                    name: bytes((value,)) * writes for name, _, value in VECTORS
                }
                for optimization in ("-O0", "-O2"):
                    binary = directory / f"native-{optimization[2:]}"
                    built = subprocess.run(
                        [
                            str(CLANG),
                            "-std=c23",
                            optimization,
                            "-Wall",
                            "-Wextra",
                            "-Werror",
                            "-fsanitize=undefined",
                            "-fno-sanitize-recover=all",
                            str(wrapper),
                            "-o",
                            str(binary),
                        ],
                        env=env,
                        capture_output=True,
                        check=False,
                        timeout=15,
                    )
                    self.assertEqual(built.returncode, 0, built.stderr)
                    for name, data, _ in VECTORS:
                        with self.subTest(optimization=optimization, input=name):
                            run = subprocess.run(
                                [str(binary)],
                                input=data,
                                capture_output=True,
                                check=False,
                                timeout=10,
                            )
                            self.assertEqual(run.returncode, 0, run.stderr)
                            self.assertEqual(run.stdout, expected[name])

                target = directory / "local.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--capsule",
                        "--max-wall-seconds",
                        "65",
                        "--output",
                        str(target),
                        str(source),
                    ],
                    capture_output=True,
                    check=False,
                    timeout=70,
                )
                if compiled.returncode != 0:
                    self.assertIn(
                        b"normalized frontend rejected: Unsupported",
                        compiled.stderr,
                    )
                    self.assertFalse(target.exists())
                    continue
                self.assertTrue(target.is_file())
                for name, data, _ in VECTORS:
                    with self.subTest(guest_input=name):
                        guest = subprocess.run(
                            [
                                str(VM),
                                str(target),
                                "--input-stdin",
                                "--report-steps",
                                "--max-steps",
                                "1000",
                            ],
                            input=data,
                            capture_output=True,
                            check=False,
                            timeout=15,
                        )
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        self.assertEqual(guest.stdout, expected[name])
                        self.assertIn(b"malbolge-steps-v1:", guest.stderr)


if __name__ == "__main__":
    _ = unittest.main()
