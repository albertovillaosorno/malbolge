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
#   - Signed EOF publication in one-write counted-loop C23 branches.
# - Must-Not:
#   - Infer EOF correctness from successful-input VM output alone.
# - Allows:
#   - Inputs: five binary vectors and one bounded complete C source.
#   - Outputs: O0/O2 native parity or typed refusal without guest artifact.
#   - Side effects: bounded native compiler and guest subprocesses.
# - Split-When:
#   - General signed EOF conversion supersedes this refusal witness.
# - Merge-When:
#   - The P2 mutable-checksum proof includes bounded counted-loop output.
# - Summary:
#   - A single output inside a counter-only branch can observe signed EOF.

"""C23 signed EOF is observable even from one counted-loop output."""

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
SOURCE: Final = """#include <stdio.h>
void emit(void) {
    for (unsigned i = 0U; i < 3U; ++i) {
        int current = getchar();
        if (i == 1U) {
            putchar(current);
        }
    }
}
"""
SAMPLES: Final = (
    ("empty", b""),
    ("first-only", b"A"),
    ("second-nul", b"A\x00"),
    ("second-high", b"A\xff"),
    ("complete", b"A\x80Z"),
)


@final
class SingleC23LoopEofPublicationTests(unittest.TestCase):
    def test_single_counter_branch_output_is_eof_safe_or_refused(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as tmp:
            folder = Path(tmp)
            source = folder / "program.c"
            _ = source.write_text(SOURCE, encoding="utf-8")
            wrapper = folder / "main.c"
            _ = wrapper.write_text(
                f'#include "{source}"\nint main(void) {{ emit(); return 0; }}\n',
                encoding="utf-8",
            )
            expected = {
                name: bytes((data[1],)) if len(data) > 1 else b"\xff"
                for name, data in SAMPLES
            }
            env = os.environ.copy()
            llvm_lib = str(ROOT / ".dependencies/llvm/22.1.8/lib")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                part for part in (llvm_lib, env.get("LD_LIBRARY_PATH", "")) if part
            )
            for optimization in ("-O0", "-O2"):
                binary = folder / f"native-{optimization[2:]}"
                native = subprocess.run(
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
                    timeout=20,
                )
                self.assertEqual(native.returncode, 0, native.stderr)
                for name, data in SAMPLES:
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
            target = folder / "output.malbolge"
            compiled = subprocess.run(
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
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=70,
            )
            if compiled.returncode != 0:
                self.assertIn(b"Unsupported", compiled.stderr)
                self.assertFalse(target.exists(), "refused C published guest bytes")
                return
            self.assertTrue(target.is_file())
            for name, data in SAMPLES:
                with self.subTest(guest_input=name):
                    guest = subprocess.run(
                        [str(VM), str(target), "--input-stdin", "--max-steps", "1000"],
                        input=data,
                        capture_output=True,
                        check=False,
                        timeout=20,
                    )
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(guest.stdout, expected[name])


if __name__ == "__main__":
    _ = unittest.main()
