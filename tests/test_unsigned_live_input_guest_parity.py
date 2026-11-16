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
#   - Live-byte guest VM parity for source-proven unsigned C predicates.
# - Must-Not:
#   - Replace guest execution with host stdout or claim EOF semantics.
# - Allows:
#   - Inputs: pinned C compiler tools and deterministic five/four-byte streams.
#   - Outputs: actual guest stdout against independent bounded C oracles.
#   - Side effects: ignored temporary files and local compiler subprocesses.
# - Split-When:
#   - General runtime C arithmetic admits arbitrary dynamic branches.
# - Merge-When:
#   - Shared guest compiler tests supply the same independent input oracle.
# - Summary:
#   - Recompile C and replay real Malbolge over seeded unsigned boundaries.

"""Prove finite unsigned C predicates with actual guest byte input/output."""

from __future__ import annotations

import hashlib
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import final

ROOT = Path(__file__).resolve().parents[1]
CASES = (
    ("unsigned_modulo_live_input", 5, 13),
    ("unsigned_wrapping_predicate_live_input", 4, 10),
)
NATIVE_TOOL_ROOT = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin"
FRONTEND = NATIVE_TOOL_ROOT / "malbolge-c-frontend"
ADAPTER = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT = ROOT / ".cache/rust/target/debug/malbolge_layout"
VM = ROOT / ".cache/rust/target/debug/malbolge"
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
GUEST_INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
SOURCES = ROOT / "tests/compiler/c-frontend/accepted"
GOLDENS = ROOT / "tests/compiler/c-frontend/golden"


def independent_c_oracle(stem: str, data: bytes) -> bytes:
    """Only successful getchar bytes; C unsigned operations use 32 bits."""
    output = bytearray()
    for counter, byte in enumerate(data, start=1):
        if stem == "unsigned_modulo_live_input":
            copies = 2 if counter % 2 == 0 else 1
        else:
            # C's subtraction converts to u32 before the > 99U comparison.
            copies = 2 if (counter - 2) % (1 << 32) > 99 else 1
        output.extend((byte,) * copies)
    return bytes(output)


def cases_for_length(length: int) -> list[bytes]:
    rng = random.Random(0x26B017 + length)
    boundaries = [
        bytes(range(65, 65 + length)),
        bytes((0x00, 0xFF, 0x80, 0x01, 0x7F)[:length]),
        bytes([0x00] * length),
        bytes([0xFF] * length),
        bytes([0x80] * length),
    ]
    return boundaries + [rng.randbytes(length) for _ in range(24)]


@final
class UnsignedLiveGuestParityTests(unittest.TestCase):
    def test_golden_source_identity(self) -> None:
        for stem, _, _ in CASES:
            with self.subTest(stem=stem):
                source = SOURCES / f"{stem}.c"
                golden = GOLDENS / f"{stem}.json"
                parsed = json.loads(golden.read_text(encoding="utf-8"))
                self.assertEqual(parsed["source"]["id"], source.name)
                self.assertEqual(
                    parsed["source"]["sha256"],
                    hashlib.sha256(source.read_bytes()).hexdigest(),
                )
                self.assertEqual(parsed["clang"]["version"], "22.1.8")

    def test_seeded_guest_parity(self) -> None:
        prerequisites = (FRONTEND, ADAPTER, LAYOUT, VM)
        if not all(path.is_file() for path in prerequisites):
            self.skipTest("repository-pinned C and guest executables missing")
        if not GUEST_INCLUDE.is_dir() or not RESOURCE.is_dir():
            self.skipTest("repository-pinned C frontend resource dirs missing")

        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for stem, count, expected_steps in CASES:
                with self.subTest(stem=stem):
                    guest = Path(directory) / f"{stem}.malbolge"
                    compiled = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            str(SOURCES / f"{stem}.c"),
                            "--output",
                            str(guest),
                        ],
                        capture_output=True,
                        check=False,
                        timeout=120,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(guest.is_file())
                    for data in cases_for_length(count):
                        with self.subTest(stdin=data.hex()):
                            result = subprocess.run(
                                [
                                    str(VM),
                                    str(guest),
                                    "--input-stdin",
                                    "--report-steps",
                                ],
                                input=data,
                                capture_output=True,
                                check=False,
                                timeout=30,
                            )
                            vm_status = result.returncode
                            self.assertEqual(vm_status, 0, msg=result.stderr)
                            self.assertEqual(
                                result.stdout, independent_c_oracle(stem, data)
                            )
                            expected_report = (
                                f"malbolge-steps-v1:{expected_steps}\n".encode()
                            )
                            self.assertEqual(result.stderr, expected_report)


if __name__ == "__main__":
    unittest.main()
