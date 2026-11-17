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
#   - Reproduction of bounded source-C signed EOF output on a real guest.
# - Must-Not:
#   - Accept full-input parity as proof of missing C23 EOF conversion.
# - Allows:
#   - Inputs: one frozen 4-read source and empty/truncated/full byte streams.
#   - Outputs: parity or typed refusal; currently a known expected failure.
#   - Side effects: pinned Clang, compiler and VM in an isolated temp folder.
# - Split-When:
#   - General executable signed EOF output conversion becomes available.
# - Merge-When:
#   - Full P2 mutable EOF checksum proves the same public C23 boundary.
# - Summary:
#   - Guest EOF residue must never stand in for signed C putchar(-1).

"""Preserve the actual four-read C23 signed EOF miscompile until repaired."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Final, final

ROOT: Final = Path(__file__).resolve().parents[1]
SOURCE: Final = (
    ROOT / "tests/compiler/c-frontend/accepted/unsigned_conditional_live_input.c"
)
DRIVER: Final = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
CLANG: Final = ROOT / ".dependencies/llvm/22.1.8/bin/clang"
FRONTEND: Final = (
    ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
)
ADAPTER: Final = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT: Final = ROOT / ".cache/rust/target/debug/malbolge_layout"
VM: Final = ROOT / ".cache/rust/target/debug/malbolge"
SAMPLES: Final = (b"", b"A", b"\x00\xff", b"\x05\x80\xff", b"\x00\xff\x80A")


@final
class BoundedC23EofPublicationTests(unittest.TestCase):
    @unittest.expectedFailure
    def test_four_read_guest_matches_native_c23_or_explicit_refusal(self) -> None:
        # Expected failure is intentional pending a *general* signed EOF
        # output conversion. A future fix produces an unexpected success,
        # requiring this marker to be removed rather than silently skipped.
        if not all(
            path.is_file()
            for path in (SOURCE, DRIVER, CLANG, FRONTEND, ADAPTER, LAYOUT, VM)
        ):
            self.skipTest("pinned C23 compiler and guest VM required")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as raw:
            folder = Path(raw)
            wrapper = folder / "main.c"
            _ = wrapper.write_text(
                f'#include "{SOURCE}"\nint main(void) {{ emit(); return 0; }}\n',
                encoding="utf-8",
            )
            env = os.environ.copy()
            llvm_lib = str(ROOT / ".dependencies/llvm/22.1.8/lib")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                part for part in (llvm_lib, env.get("LD_LIBRARY_PATH", "")) if part
            )
            oracle: dict[bytes, bytes] = {}
            for optimization in ("-O0", "-O2"):
                native = folder / f"native-{optimization[2:]}"
                compiled_native = subprocess.run(
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
                        str(native),
                    ],
                    env=env,
                    capture_output=True,
                    check=False,
                    timeout=15,
                )
                self.assertEqual(compiled_native.returncode, 0, compiled_native.stderr)
                for data in SAMPLES:
                    run = subprocess.run(
                        [str(native)],
                        input=data,
                        capture_output=True,
                        check=False,
                        timeout=10,
                    )
                    self.assertEqual(run.returncode, 0, run.stderr)
                    expected = bytes(
                        data[index] if index < len(data) else 255
                        for index in (0, 1, 2, 2, 3)
                    )
                    self.assertEqual(run.stdout, expected)
                    self.assertEqual(oracle.setdefault(data, run.stdout), run.stdout)
            target = folder / "output.malbolge"
            compiled_guest = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--capsule",
                    "--max-wall-seconds",
                    "75",
                    "--output",
                    str(target),
                    str(SOURCE),
                ],
                capture_output=True,
                check=False,
                timeout=85,
            )
            if compiled_guest.returncode != 0:
                self.assertIn(b"Unsupported", compiled_guest.stderr)
                self.assertFalse(target.exists())
                return
            self.assertTrue(target.is_file())
            for data in SAMPLES:
                with self.subTest(input=data):
                    run = subprocess.run(
                        [str(VM), str(target), "--input-stdin", "--max-steps", "1000"],
                        input=data,
                        capture_output=True,
                        check=False,
                        timeout=20,
                    )
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(run.stdout, oracle[data])
