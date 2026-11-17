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
#   - Native C23 EOF parity or typed refusal for direct loop-local output.
# - Must-Not:
#   - Interpret successful-byte guest parity as signed EOF equivalence.
# - Allows:
#   - Inputs: one/two bounded loops and five binary stdin samples.
#   - Outputs: independent C23 oracles and guest parity or no publication.
#   - Side effects: pinned native compilers and isolated temporary artifacts.
# - Split-When:
#   - Guest signed EOF conversion supports arbitrary runtime C output.
# - Merge-When:
#   - The complete mutable EOF checksum subsumes this P2 boundary.
# - Summary:
#   - A signed C loop-local cannot silently emit raw Malbolge EOF residue.

"""Test counted C23 signed getchar locals against actual guest output."""

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
VECTORS: Final = (b"", b"\x00", b"\xff", b"\x01\x80", b"\x00\xff\x81")


def source_for_trips(trips: int) -> str:
    """Keep original C source geometry required by the pinned frontend."""
    return (
        "#include <stdio.h>\n"
        "void emit(void) {\n"
        f"    for (unsigned i = 0U; i < {trips}U; ++i) {{\n"
        "        int current = getchar();\n"
        "        putchar(current);\n"
        "    }\n"
        "}\n"
    )


@final
class CountedLoopSignedLocalEofTests(unittest.TestCase):
    def test_native_c23_eof_and_compiler_no_mispublication(self) -> None:
        if not all(path.is_file() for path in (CLANG, DRIVER, VM)):
            self.skipTest("pinned compiler and guest VM required")
        env = os.environ.copy()
        llvm_lib = str(ROOT / ".dependencies/llvm/22.1.8/lib")
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            part for part in (llvm_lib, env.get("LD_LIBRARY_PATH", "")) if part
        )
        for trips in (1, 2):
            with (
                self.subTest(trips=trips),
                tempfile.TemporaryDirectory(dir=ROOT / ".temp") as raw,
            ):
                folder = Path(raw)
                source = folder / "signed-loop-local.c"
                _ = source.write_text(source_for_trips(trips), encoding="utf-8")
                wrapper = folder / "main.c"
                _ = wrapper.write_text(
                    f'#include "{source}"\nint main(void) {{ emit(); return 0; }}\n',
                    encoding="utf-8",
                )
                for opt in ("-O0", "-O2"):
                    native = folder / f"native-{opt[2:]}"
                    compiled = subprocess.run(
                        [
                            str(CLANG),
                            "-std=c23",
                            opt,
                            "-Wall",
                            "-Wextra",
                            "-Werror",
                            "-fsanitize=undefined",
                            "-fno-sanitize-recover=all",
                            str(wrapper),
                            "-o",
                            str(native),
                        ],
                        env=env,
                        capture_output=True,
                        check=False,
                        timeout=15,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    for data in VECTORS:
                        expected = bytes(
                            data[i] if i < len(data) else 255 for i in range(trips)
                        )
                        run = subprocess.run(
                            [str(native)],
                            input=data,
                            capture_output=True,
                            check=False,
                            timeout=10,
                        )
                        self.assertEqual(run.returncode, 0, run.stderr)
                        self.assertEqual(run.stdout, expected)
                target = folder / "guest.malbolge"
                guest_compile = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--capsule",
                        "--max-wall-seconds",
                        "70",
                        "--output",
                        str(target),
                        str(source),
                    ],
                    capture_output=True,
                    check=False,
                    timeout=75,
                )
                if guest_compile.returncode != 0:
                    self.assertIn(b"Unsupported", guest_compile.stderr)
                    self.assertFalse(target.exists())
                    continue
                self.assertTrue(target.is_file())
                for data in VECTORS:
                    expected = bytes(
                        data[i] if i < len(data) else 255 for i in range(trips)
                    )
                    run = subprocess.run(
                        [str(VM), str(target), "--input-stdin", "--max-steps", "1000"],
                        input=data,
                        capture_output=True,
                        check=False,
                        timeout=15,
                    )
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(run.stdout, expected)


if __name__ == "__main__":
    _ = unittest.main()
