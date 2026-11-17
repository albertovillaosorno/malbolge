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
#   - Independent C23 and guest VM agreement for discarded signed read + byte.
# - Must-Not:
#   - Treat EOF as successful u8, skip true guest I/O, or publish tampered C.
# - Allows:
#   - Inputs: frozen C source, short binary streams and negative source drift.
#   - Outputs: observed C/guest bytes and artifact-free failed admissions.
#   - Side effects: bounded isolated compiler, native executable and VM runs.
# - Split-When:
#   - General source-control-flow input arithmetic subsumes this exact slice.
# - Merge-When:
#   - Complete mutable EOF checksum publishes with a single guest runtime.
# - Summary:
#   - C23 and genuine emitted guest both read once and emit the same byte.

"""End-to-end signed input followed by a source-independent guest byte."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Final, final

ROOT: Final = Path(__file__).resolve().parents[1]
SOURCE: Final = ROOT / "tests/compiler/c-frontend/accepted/discarded_input_literal.c"
SOURCE_DIGEST: Final = "f373b8001a6dce14987295a995ad96cae160a15d9090f01ed876249730f935be"
DRIVER: Final = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
ADAPTER: Final = ROOT / ".cache/rust/target/debug/c2malbolge_json"
FRONTEND: Final = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
VM: Final = ROOT / ".cache/rust/target/debug/malbolge"
CLANG: Final = ROOT / ".dependencies/llvm/22.1.8/bin/clang"
VECTORS: Final = (b"", b"\x00", b"\xff", b"\x00\x80\xff")


@final
class SignedInputLiteralPublicationTests(unittest.TestCase):
    def test_source_identity_and_source_checked_rejection(self) -> None:
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(), SOURCE_DIGEST)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as raw:
            directory = Path(raw)
            env = os.environ.copy()
            env["LD_LIBRARY_PATH"] = str(ROOT / ".dependencies/llvm/22.1.8/lib")
            result = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include", str(ROOT / "src/runtime/guest-c-library/contract/include"),
                    "--resource-dir", str(ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"),
                    "--source-id", "fixtures/signed-input-literal.c", str(SOURCE),
                ],
                capture_output=True, check=True, env=env, timeout=15,
            )
            changed_source = directory / "changed.c"
            changed_source.write_bytes(SOURCE.read_bytes().replace(b"putchar(11)", b"putchar(12)"))
            output = directory / "disallowed.malbolge"
            check = subprocess.run(
                [
                    str(ADAPTER), "--layout-backend", "/bin/false",
                    "--output", str(output), "--source", str(changed_source),
                ],
                input=result.stdout, capture_output=True, timeout=15,
            )
            self.assertNotEqual(check.returncode, 0)
            self.assertIn(b"normalized frontend rejected", check.stderr)
            self.assertFalse(output.exists())
            # A forged extra side effect in the normalized tree cannot pass.
            tampered = result.stdout.replace(b'"external:getchar"', b'"external:putchar"', 1)
            self.assertNotEqual(tampered, result.stdout)
            check = subprocess.run(
                [
                    str(ADAPTER), "--layout-backend", "/bin/false",
                    "--output", str(output), "--source", str(SOURCE),
                ],
                input=tampered, capture_output=True, timeout=15,
            )
            self.assertNotEqual(check.returncode, 0)
            self.assertIn(b"normalized frontend rejected", check.stderr)
            self.assertFalse(output.exists())

    def test_native_c23_and_real_guest_binary_parity(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as raw:
            directory = Path(raw)
            wrapper = directory / "main.c"
            wrapper.write_text(
                f'#include "{SOURCE}"\nint main(void) {{ emit(); return 0; }}\n',
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["LD_LIBRARY_PATH"] = str(ROOT / ".dependencies/llvm/22.1.8/lib")
            for optimization in ("-O0", "-O2"):
                native = directory / f"native-{optimization[2:]}"
                subprocess.run(
                    [str(CLANG), "-std=c23", optimization, str(wrapper), "-o", str(native)],
                    check=True, capture_output=True, timeout=15, env=env,
                )
                for stream in VECTORS:
                    observed = subprocess.run(
                        [str(native)], input=stream, capture_output=True, timeout=10,
                    )
                    self.assertEqual(observed.returncode, 0)
                    self.assertEqual(observed.stdout, b"\x0b")
            guest = directory / "mixed.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable, "-B", str(DRIVER),
                    "--repository-tools", "--capsule", "--max-wall-seconds", "160",
                    "--output", str(guest), str(SOURCE),
                ],
                capture_output=True, timeout=180,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr.decode(errors="replace"))
            self.assertTrue(guest.exists())
            self.assertIn(b"5 VM steps", compiled.stderr)
            for stream in VECTORS:
                observed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--max-steps", "25"],
                    input=stream, capture_output=True, timeout=20,
                )
                self.assertEqual(observed.returncode, 0, observed.stderr.decode(errors="replace"))
                self.assertEqual(observed.stdout, b"\x0b")


if __name__ == "__main__":
    unittest.main()
