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
#   - Pinned C23 unsigned bitwise guard parity against actual Malbolge.
# - Must-Not:
#   - Replace guest execution with host stdout or trust Clang output alone.
# - Allows:
#   - Inputs: source-authenticated &, ^, | guards and four guest input bytes.
#   - Outputs: an independently computed twelve-byte trace per input vector.
#   - Side effects: ignored temporary capsules and isolated guest VM runs.
# - Split-When:
#   - General runtime C bitwise semantics replace static induction selection.
# - Merge-When:
#   - Source-time induction parity uses a shared seeded full-program matrix.
# - Summary:
#   - Validate source-time bitwise selection without predicting guest bytes.

"""Real Malbolge guest parity for source-authenticated unsigned bitwise C."""

from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TypedDict, cast, final

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests/compiler/c-frontend/accepted/unsigned_bitwise_truth_live_input.c"
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
CLANG = ROOT / ".dependencies/llvm/22.1.8/bin/clang"
RUST_BIN = ROOT / ".cache/rust/target/debug"
VM = RUST_BIN / "malbolge"


def oracle(data: bytes) -> bytes:
    """C loop index, not guest byte value, selects each output count."""
    return b"".join(
        bytes((byte,)) * (1 + bool(index & 1) + bool(index ^ 2) + bool(index))
        for index, byte in enumerate(data)
    )


class _ClangIdentity(TypedDict):
    version: str


class _SourceIdentity(TypedDict):
    id: str
    sha256: str


class _GoldenIdentity(TypedDict):
    clang: _ClangIdentity
    source: _SourceIdentity


@final
class UnsignedBitwiseTruthGuestParityTests(unittest.TestCase):
    def test_pinned_clang_golden_matches_source(self) -> None:
        golden = (
            ROOT
            / "tests/compiler/c-frontend/golden/unsigned_bitwise_truth_live_input.json"
        )
        parsed = cast(_GoldenIdentity, json.loads(golden.read_text(encoding="utf-8")))
        self.assertEqual(parsed["clang"]["version"], "22.1.8")
        self.assertEqual(parsed["source"]["id"], "unsigned-bitwise-truth-v1")
        self.assertEqual(
            parsed["source"]["sha256"],
            hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        )

    def test_complete_c_program_on_actual_guest_vm(self) -> None:
        required = (
            FRONTEND,
            RUST_BIN / "c2malbolge_json",
            RUST_BIN / "malbolge_layout",
            VM,
        )
        if not all(path.is_file() for path in required) or not RESOURCE.is_dir():
            self.skipTest("pinned C frontend, layout, VM, and runtime required")

        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            directory = Path(temporary)
            capsule = directory / "bitwise-truth.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--capsule",
                    "--output",
                    str(capsule),
                    str(SOURCE),
                ],
                capture_output=True,
                check=False,
                timeout=120,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(capsule.is_file())

            native: list[Path] = []
            if CLANG.is_file():
                wrapper = directory / "native-oracle.c"
                _ = wrapper.write_text(
                    f'#include "{SOURCE}"\nint main(void) {{ emit(); return 0; }}\n',
                    encoding="utf-8",
                )
                for optimization in ("-O0", "-O2"):
                    executable = directory / f"native-{optimization[2:]}"
                    built = subprocess.run(
                        [
                            str(CLANG),
                            "-std=c23",
                            optimization,
                            "-fsanitize=undefined",
                            "-fno-sanitize-recover=all",
                            str(wrapper),
                            "-o",
                            str(executable),
                        ],
                        env={
                            **os.environ,
                            "LD_LIBRARY_PATH": os.pathsep.join(
                                part
                                for part in (
                                    str(ROOT / ".dependencies/llvm/22.1.8/lib"),
                                    os.environ.get("LD_LIBRARY_PATH", ""),
                                )
                                if part
                            ),
                        },
                        capture_output=True,
                        check=False,
                        timeout=50,
                    )
                    self.assertEqual(built.returncode, 0, built.stderr)
                    native.append(executable)

            seeded = random.Random(0xB17B175E)
            inputs = [
                b"ABCD",
                b"\x00\xff\x80\x01",
                b"\xff\xff\xff\xff",
                b"\x00\x00\x00\x00",
                b"\n\x00\xfe\xff",
            ]
            inputs.extend(
                bytes(seeded.getrandbits(8) for _ in range(4)) for _ in range(8)
            )

            def run_guest(data: bytes) -> subprocess.CompletedProcess[bytes]:
                return subprocess.run(
                    [str(VM), str(capsule), "--input-stdin", "--report-steps"],
                    input=data,
                    capture_output=True,
                    check=False,
                    timeout=45,
                )

            with ThreadPoolExecutor(max_workers=4) as executor:
                for data, executed in zip(
                    inputs, executor.map(run_guest, inputs), strict=True
                ):
                    with self.subTest(input=data.hex()):
                        expected = oracle(data)
                        self.assertEqual(executed.returncode, 0, executed.stderr)
                        self.assertEqual(executed.stdout, expected)
                        self.assertEqual(executed.stderr, b"malbolge-steps-v1:17\n")
                        for executable in native:
                            reproduced = subprocess.run(
                                [str(executable)],
                                input=data,
                                capture_output=True,
                                check=False,
                                timeout=10,
                            )
                            self.assertEqual(
                                reproduced.returncode, 0, reproduced.stderr
                            )
                            self.assertEqual(reproduced.stdout, expected)


if __name__ == "__main__":
    _ = unittest.main()
