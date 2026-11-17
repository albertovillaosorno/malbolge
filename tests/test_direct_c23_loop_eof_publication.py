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
#   - C23 EOF output parity for a frozen direct counted-loop byte stream.
# - Must-Not:
#   - Publish a successful-byte-only guest as complete signed getchar C.
# - Allows:
#   - Inputs: five binary stdin streams and a source-pinned C23 loop.
#   - Outputs: native O0/O2 parity or typed refusal without guest artifact.
#   - Side effects: isolated native compiler, guest compiler and VM processes.
# - Split-When:
#   - General signed EOF conversion replaces bounded loop refusal.
# - Merge-When:
#   - The full mutable EOF checksum proves arbitrary guest stdin exhaustion.
# - Summary:
#   - Bounded for-loop unrolling cannot assume getchar always returns a byte.

"""A direct counted-loop putchar(getchar()) must preserve C23 EOF."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Final, final

ROOT: Final = Path(__file__).resolve().parents[1]
SOURCE: Final = ROOT / "tests/compiler/c-frontend/accepted/input_unsigned_loop.c"
CLANG: Final = ROOT / ".dependencies/llvm/22.1.8/bin/clang"
DRIVER: Final = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
VM: Final = ROOT / ".cache/rust/target/debug/malbolge"
SAMPLES: Final = (b"", b"A", b"\x00\xff", b"\x05\x80\xff", b"\x00\xff\x80A")


@final
class DirectC23LoopEofPublicationTests(unittest.TestCase):
    def test_direct_loop_matches_native_or_refuses_publication(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            folder = Path(directory)
            wrapper = folder / "main.c"
            _ = wrapper.write_text(
                f'#include "{SOURCE}"\nint main(void) {{ emit(); return 0; }}\n',
                encoding="utf-8",
            )
            expected = {
                data: bytes(
                    data[index] if index < len(data) else 0xFF for index in range(4)
                )
                for data in SAMPLES
            }
            env = os.environ.copy()
            library = str(ROOT / ".dependencies/llvm/22.1.8/lib")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                part for part in (library, env.get("LD_LIBRARY_PATH", "")) if part
            )
            for optimization in ("-O0", "-O2"):
                binary = folder / f"native-{optimization[2:]}"
                compiled = subprocess.run(
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
                    capture_output=True,
                    check=False,
                    timeout=20,
                    env=env,
                )
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                for data in SAMPLES:
                    with self.subTest(optimization=optimization, input=data):
                        native = subprocess.run(
                            [str(binary)],
                            input=data,
                            capture_output=True,
                            check=False,
                            timeout=10,
                        )
                        self.assertEqual(native.returncode, 0, native.stderr)
                        self.assertEqual(native.stdout, expected[data])
            target = folder / "output.malbolge"
            guest_compilation = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--capsule",
                    "--max-wall-seconds",
                    "60",
                    "--output",
                    str(target),
                    str(SOURCE),
                ],
                capture_output=True,
                check=False,
                timeout=70,
            )
            if guest_compilation.returncode != 0:
                self.assertIn(
                    b"normalized frontend rejected: Unsupported",
                    guest_compilation.stderr,
                )
                self.assertFalse(target.exists(), "refusal published guest code")
                return
            self.assertTrue(target.is_file())
            for data in SAMPLES:
                with self.subTest(guest_input=data):
                    executed = subprocess.run(
                        [str(VM), str(target), "--input-stdin", "--max-steps", "1000"],
                        input=data,
                        capture_output=True,
                        check=False,
                        timeout=20,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, expected[data])


if __name__ == "__main__":
    _ = unittest.main()
