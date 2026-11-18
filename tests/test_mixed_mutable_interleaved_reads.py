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
#   - Real source-to-guest execution of interleaved constant updates and reads.
# - Must-Not:
#   - Fake guest output, skip signed reads or accept dynamic source operands.
# - Allows:
#   - Inputs: one SHA-pinned C23 source, five binary streams, source mutations.
#   - Outputs: native -O0/-O2 parity, real guest traces or typed refusal.
#   - Side effects: bounded isolated compiler and VM child processes.
# - Split-When:
#   - Generic guest-side mutable C covers the same source-language behavior.
# - Merge-When:
#   - The full P2 mutable EOF checksum acceptance supersedes this source.
# - Summary:
#   - Prove source order, genuine EOF-preserving reads and independent output.

"""Verify interleaved signed guest reads and source-ordered constant state."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Final, cast, final

ROOT: Final = Path(__file__).resolve().parents[1]
SOURCE: Final = (
    ROOT / "tests/compiler/c-frontend/accepted/mixed_mutable_interleaved_reads.c"
)
SHA256: Final = "5b394b2594d443796dbe4469b7e5b9e7a4561678349b9b961cfc3459c6fbc908"
FRONTEND: Final = (
    ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
)
CLANG: Final = ROOT / ".dependencies/llvm/22.1.8/bin/clang"
ADAPTER: Final = ROOT / ".cache/rust/target/debug/c2malbolge_json"
VM: Final = ROOT / ".cache/rust/target/debug/malbolge"
DRIVER: Final = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
GUEST_INCLUDE: Final = ROOT / "src/runtime/guest-c-library/contract/include"
RESOURCE_DIR: Final = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
VECTORS: Final = (
    ("empty", b""),
    ("nul", b"\x00"),
    ("high", b"\xff"),
    ("mixed", b"\x00\x80\xff"),
    ("truncated-eof", b"\x05\x00\x81"),
)
EXPECTED: Final = b"\x0b"


def llvm_environment() -> dict[str, str]:
    env = os.environ.copy()
    llvm_lib = str(ROOT / ".dependencies/llvm/22.1.8/lib")
    env["LD_LIBRARY_PATH"] = os.pathsep.join(
        part for part in (llvm_lib, env.get("LD_LIBRARY_PATH", "")) if part
    )
    return env


def frontend(source: Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            str(FRONTEND),
            "--guest-include",
            str(GUEST_INCLUDE),
            "--resource-dir",
            str(RESOURCE_DIR),
            "--source-id",
            "tests/interleaved-mutable-v1",
            str(source),
        ],
        capture_output=True,
        check=False,
        env=llvm_environment(),
        timeout=15,
    )


@final
class MixedMutableInterleavedReadsTests(unittest.TestCase):
    def test_source_native_and_typed_refusal_boundary(self) -> None:
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(), SHA256)
        self.assertTrue(all(p.is_file() for p in (CLANG, FRONTEND, ADAPTER, VM)))
        original = SOURCE.read_bytes()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as raw:
            directory = Path(raw)
            wrapper = directory / "main.c"
            _ = wrapper.write_text(
                f'#include "{SOURCE}"\nint main(void) {{ emit(); return 0; }}\n',
                encoding="utf-8",
            )
            for optimization in ("-O0", "-O2"):
                native = directory / f"native-{optimization[2:]}"
                built = subprocess.run(
                    [
                        str(CLANG),
                        "-std=c23",
                        optimization,
                        "-Wall",
                        "-Wextra",
                        "-Werror",
                        "-Wno-unused-variable",
                        "-fsanitize=undefined",
                        "-fno-sanitize-recover=all",
                        str(wrapper),
                        "-o",
                        str(native),
                    ],
                    capture_output=True,
                    check=False,
                    env=llvm_environment(),
                    timeout=20,
                )
                self.assertEqual(built.returncode, 0, built.stderr)
                for name, data in VECTORS:
                    with self.subTest(optimization=optimization, name=name):
                        run = subprocess.run(
                            [str(native)],
                            input=data,
                            capture_output=True,
                            check=False,
                            timeout=10,
                        )
                        self.assertEqual(run.returncode, 0, run.stderr)
                        self.assertEqual(run.stdout, EXPECTED)

            normalized = frontend(SOURCE)
            self.assertEqual(normalized.returncode, 0, normalized.stderr)
            no_guest = directory / "no-guest.malbolge"
            accepted = subprocess.run(
                [
                    str(ADAPTER),
                    "--layout-backend",
                    "/bin/false",
                    "--output",
                    str(no_guest),
                    "--source",
                    str(SOURCE),
                ],
                input=normalized.stdout,
                capture_output=True,
                check=False,
                timeout=15,
            )
            self.assertNotEqual(accepted.returncode, 0)
            self.assertIn(b"layout backend exited unsuccessfully", accepted.stderr)
            self.assertFalse(no_guest.exists())

            changes = (
                (b"checksum ^= 7U;", b"checksum *= 7U;"),
                (b"checksum ^= 7U;", b"checksum ^= (unsigned)second;"),
                (b"checksum ^= 7U;", b"checksum ^= (unsigned)first;"),
                (b"putchar((int)checksum);", b"putchar((int)second);"),
                (
                    b"int second = getchar();",
                    b"int second = getchar();\n    int third = getchar();",
                ),
                (b"int second = getchar();", b"int second = 3;"),
                (b"checksum += 5U;", b"checksum += 5U;\n    checksum += 1U;"),
            )
            for index, (before, after) in enumerate(changes):
                with self.subTest(mutation=index):
                    self.assertEqual(original.count(before), 1)
                    altered = directory / "changed.c"
                    _ = altered.write_bytes(original.replace(before, after))
                    normalized_altered = frontend(altered)
                    self.assertEqual(
                        normalized_altered.returncode, 0, normalized_altered.stderr
                    )
                    output = directory / f"refused-{index}.malbolge"
                    rejected = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            "/bin/false",
                            "--output",
                            str(output),
                            "--source",
                            str(altered),
                        ],
                        input=normalized_altered.stdout,
                        capture_output=True,
                        check=False,
                        timeout=15,
                    )
                    self.assertNotEqual(rejected.returncode, 0)
                    self.assertIn(b"Unsupported", rejected.stderr)
                    self.assertNotIn(b"layout backend", rejected.stderr)
                    self.assertFalse(output.exists())

            forged = cast(dict[str, object], json.loads(normalized.stdout))
            nodes = cast(list[dict[str, object]], forged["nodes"])
            read = next(
                node
                for node in nodes
                if node["id"] == 16 and node["reference"] == "external:getchar"
            )
            read["reference"] = "external:putchar"
            corrupted = subprocess.run(
                [
                    str(ADAPTER),
                    "--layout-backend",
                    "/bin/false",
                    "--output",
                    str(no_guest),
                    "--source",
                    str(SOURCE),
                ],
                input=json.dumps(forged).encode(),
                capture_output=True,
                check=False,
                timeout=15,
            )
            self.assertNotEqual(corrupted.returncode, 0)
            self.assertIn(b"Unsupported", corrupted.stderr)
            self.assertNotIn(b"layout backend", corrupted.stderr)
            self.assertFalse(no_guest.exists())

    def test_complete_source_executes_two_reads_on_real_guest(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as raw:
            target = Path(raw) / "interleaved.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--capsule",
                    "--max-wall-seconds",
                    "180",
                    "--output",
                    str(target),
                    str(SOURCE),
                ],
                capture_output=True,
                check=False,
                timeout=190,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(target.is_file())
            self.assertEqual(len(target.read_bytes()), 1095)
            for name, data in VECTORS:
                with self.subTest(name=name):
                    guest = subprocess.run(
                        [str(VM), str(target), "--report-steps", "--max-steps", "1000"],
                        input=data,
                        capture_output=True,
                        check=False,
                        timeout=15,
                    )
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(guest.stdout, EXPECTED)
                    self.assertIn(b"malbolge-steps-v1:6", guest.stderr)


if __name__ == "__main__":
    _ = unittest.main()
