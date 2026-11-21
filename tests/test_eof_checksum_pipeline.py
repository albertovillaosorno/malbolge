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
#   - Independent native-C controls and future real guest acceptance of P2 EOF.
# - Must-Not:
#   - Treat an unsupported compiler result or a host process as guest success.
# - Allows:
#   - Inputs: one SHA-pinned stateful C source and five finite binary streams.
#   - Outputs: O0/O2 oracle parity or precise compiler refusal without artifact.
#   - Side effects: bounded child compilers and isolated temporary artifacts.
# - Split-When:
#   - General P3 EOF and streaming acceptance subsumes this one exact program.
# - Merge-When:
#   - The tracked P2 whole-program regression has one shared native oracle.
# - Summary:
#   - A full mutable EOF loop must reach the normative guest or fail closed.
# - Description:
#   - Five binary vectors independently check the C23 UBSan oracle and guest
#     publication boundary without using host execution as a target witness.
# - Usage:
#   - Run the source-controlled P2 checksum unittest with pinned Python.
# - Defaults:
#   - Fail closed on any unexpected compiler error or output artifact.

"""P2 EOF-checksum gate: independently check C, then the actual guest VM."""

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
SOURCE: Final = ROOT / "tests/compiler/c-frontend/accepted/mutable_eof_checksum.c"
SHA256: Final = "9ae147a9d0e824bafb9322ee4787cdc8a7f45cb84c3f8691ad74f9eef32553c7"
CLANG: Final = ROOT / ".dependencies/llvm/22.1.8/bin/clang"
DRIVER: Final = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
ADAPTER: Final = ROOT / ".cache/rust/target/debug/c2malbolge_json"
NORMALIZED: Final = ROOT / (
    "tests/compiler/c-frontend/golden/mutable_eof_checksum_current.json"
)
VM: Final = ROOT / ".cache/rust/target/debug/malbolge"
# Freeze one byte-stream witness for each required semantic boundary.
VECTORS: Final = (
    ("empty", b""),
    ("nul", b"\x00"),
    ("high-byte", b"\xff"),
    ("mixed", b"\x01\x00\x80\xfe"),
    ("truncated-eof", b"\x05\x00\x81"),
)
# All ceilings apply to each subprocess, not only the whole test invocation.
COMPILER_SECONDS: Final = 75
VM_SECONDS: Final = 15
NATIVE_SECONDS: Final = 10
VM_MAX_STEPS: Final = 100_000


def independent_checksum(stream: bytes) -> bytes:
    """Compute the declared C23 unsigned checksum without invoking the C code."""
    checksum = 0
    for value in stream:
        if value & 1:
            checksum ^= value
        else:
            checksum += value
        checksum = (checksum + 3) & 255
    return bytes((checksum,))


@final
class MutableEofChecksumTests(unittest.TestCase):
    def test_source_identity_and_binary_witness(self) -> None:
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(), SHA256)
        self.assertEqual(len(VECTORS), 5)
        self.assertEqual(len({name for name, _ in VECTORS}), 5)
        self.assertEqual(independent_checksum(b""), b"\x00")
        self.assertEqual(independent_checksum(b"\x00"), b"\x03")
        self.assertEqual(independent_checksum(b"\xff"), b"\x02")

    def test_prelink_does_not_invoke_or_require_backend(self) -> None:
        """No executable linker may receive unresolved checksum state."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            path = Path(directory)
            output = path / "unlinked.malbolge"
            backend = path / "missing-layout-backend"
            self.assertFalse(backend.exists())
            admitted = subprocess.run(
                [
                    str(ADAPTER),
                    "--layout-backend",
                    str(backend),
                    "--output",
                    str(output),
                    "--source",
                    str(SOURCE),
                ],
                input=NORMALIZED.read_bytes(),
                capture_output=True,
                check=False,
                timeout=COMPILER_SECONDS,
            )
            self.assertNotEqual(admitted.returncode, 0)
            self.assertIn(b"dynamic EOF checksum CFG is unlinked", admitted.stderr)
            self.assertIn(
                b"source-backed prelink has 7 blocks, 19 operations, "
                b"4 phi edges, 6 phi moves, and 43 reserved guest words",
                admitted.stderr,
            )
            self.assertIn(b"minimum 71 guest code cells", admitted.stderr)
            self.assertFalse(output.exists())

    def test_complete_compiler_and_guest_or_explicit_refusal(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            path = Path(directory)
            # Native C23 is a separate executable with distinct -O0/-O2
            # UBSan runs. It is never an input to the guest compiler.
            wrapper = path / "main.c"
            _ = wrapper.write_text(
                f'#include "{SOURCE}"\nint main(void) {{ emit(); return 0; }}\n',
                encoding="utf-8",
            )
            expected = {name: independent_checksum(data) for name, data in VECTORS}
            env = os.environ.copy()
            llvm_lib = str(ROOT / ".dependencies/llvm/22.1.8/lib")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                part for part in (llvm_lib, env.get("LD_LIBRARY_PATH", "")) if part
            )
            for optimization in ("-O0", "-O2"):
                binary = path / f"native-{optimization[2:]}"
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
                    timeout=COMPILER_SECONDS,
                )
                self.assertEqual(
                    built.returncode, 0, built.stderr.decode(errors="replace")
                )
                for name, data in VECTORS:
                    with self.subTest(optimization=optimization, input=name):
                        run = subprocess.run(
                            [str(binary)],
                            input=data,
                            capture_output=True,
                            check=False,
                            timeout=NATIVE_SECONDS,
                        )
                        self.assertEqual(run.returncode, 0, run.stderr)
                        self.assertEqual(run.stdout, expected[name])

            target = path / "checksum.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--capsule",
                    "--max-wall-seconds",
                    str(COMPILER_SECONDS),
                    "--output",
                    str(target),
                    str(SOURCE),
                ],
                capture_output=True,
                check=False,
                timeout=COMPILER_SECONDS,
            )
            if compiled.returncode != 0:
                # An explicit target-lowering refusal is an active P2 blocker, not
                # equivalence evidence. Any different failure must be triaged.
                self.assertIn(
                    (
                        b"target lowering rejected: dynamic EOF checksum CFG "
                        b"is "
                        b"unlinked; source-backed prelink has 7 blocks, "
                        b"19 operations, 4 phi edges, 6 phi moves, and "
                        b"43 reserved guest words"
                    ),
                    compiled.stderr,
                )
                self.assertIn(b"minimum 71 guest code cells", compiled.stderr)
                self.assertIn(b"missing physical guest operations", compiled.stderr)
                self.assertFalse(
                    target.exists(), "unsupported compiler published a guest"
                )
                return
            self.assertTrue(target.is_file(), "compiler succeeded without a guest")
            for name, data in VECTORS:
                with self.subTest(guest_input=name):
                    guest = subprocess.run(
                        [
                            str(VM),
                            str(target),
                            "--input-stdin",
                            "--report-steps",
                            "--max-steps",
                            str(VM_MAX_STEPS),
                        ],
                        input=data,
                        capture_output=True,
                        check=False,
                        timeout=VM_SECONDS,
                    )
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(guest.stdout, expected[name])
                    self.assertIn(b"malbolge-steps-v1:", guest.stderr)


if __name__ == "__main__":
    _ = unittest.main()
