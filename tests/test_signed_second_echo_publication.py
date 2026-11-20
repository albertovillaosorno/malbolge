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
#   - Source-C signed second getchar/putchar guest EOF publication parity.
# - Must-Not:
#   - Replace signed EOF with a byte-only fixture or infer guest output on host.
# - Allows:
#   - Inputs: independent native C23 and same compiled source, binary stdin.
#   - Outputs: signed EOF-to-u8 parity and rejection of altered C effect traces.
#   - Side effects: bounded subprocesses in temporary filesystem.
# - Split-When:
#   - General C23 signed I/O compilation subsumes this bounded closed grammar.
# - Merge-When:
#   - The P2 mutable checksum guest implements genuine EOF-dependent control.
# - Summary:
#   - Independent Clang and guest agree on two real reads and EOF conversion.

"""C23 signed double-read publication, not the still-unlinked EOF checksum."""

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
SOURCE: Final = "#include <stdio.h>\nvoid emit(void) { getchar(); putchar(getchar()); }\n"
VECTORS: Final = (
    ("empty", b"", b"\xff"),
    ("first-only", b"\x00", b"\xff"),
    ("nul", b"\x81\x00", b"\x00"),
    ("high-byte", b"\x00\xff", b"\xff"),
    ("trailing", b"\xff\x80\x00", b"\x80"),
)


@final
class SignedSecondEchoPublicationTests(unittest.TestCase):
    def test_source_c23_native_and_normative_guest(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            path = Path(directory)
            source = path / "source.c"
            source.write_text(SOURCE, encoding="utf-8")
            wrapper = path / "entry.c"
            wrapper.write_text('#include "source.c"\nint main(void) { emit(); return 0; }\n', encoding="utf-8")
            env = os.environ.copy()
            llvm_lib = str(ROOT / ".dependencies/llvm/22.1.8/lib")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                item for item in (llvm_lib, env.get("LD_LIBRARY_PATH", "")) if item
            )
            for optimization in ("-O0", "-O2"):
                binary = path / f"native-{optimization[2:]}"
                compiled = subprocess.run(
                    [str(CLANG), "-std=c23", optimization, "-Wall", "-Wextra", "-Werror",
                     "-fsanitize=undefined", "-fno-sanitize-recover=all",
                     str(wrapper), "-o", str(binary)],
                    capture_output=True, env=env, check=False, timeout=20,
                )
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                for label, stdin, expected in VECTORS:
                    with self.subTest(oracle=optimization, stream=label):
                        run = subprocess.run([str(binary)], input=stdin, capture_output=True,
                                             check=False, timeout=15)
                        self.assertEqual(run.returncode, 0, run.stderr)
                        self.assertEqual(run.stdout, expected)

            target = path / "second.malbolge"
            compiler = subprocess.run(
                [sys.executable, "-B", str(DRIVER), "--repository-tools", "--capsule",
                 "--max-wall-seconds", "75", "--output", str(target), str(source)],
                capture_output=True, check=False, timeout=85,
            )
            self.assertEqual(compiler.returncode, 0, compiler.stderr)
            self.assertTrue(target.is_file())
            for label, stdin, expected in VECTORS:
                with self.subTest(guest=label):
                    guest = subprocess.run(
                        [str(VM), str(target), "--input-stdin", "--max-steps", "1000",
                         "--report-steps"],
                        input=stdin, capture_output=True, check=False, timeout=15,
                    )
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(guest.stdout, expected)
                    self.assertIn(b"malbolge-steps-v1:81", guest.stderr)

    def test_extra_input_is_not_silently_dropped(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            path = Path(directory)
            source = path / "extra.c"
            source.write_text(
                SOURCE.replace("getchar(); putchar", "getchar(); getchar(); putchar"),
                encoding="utf-8",
            )
            target = path / "untrusted.malbolge"
            compiler = subprocess.run(
                [sys.executable, "-B", str(DRIVER), "--repository-tools", "--capsule",
                 "--max-wall-seconds", "30", "--output", str(target), str(source)],
                capture_output=True, check=False, timeout=40,
            )
            self.assertNotEqual(compiler.returncode, 0)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
