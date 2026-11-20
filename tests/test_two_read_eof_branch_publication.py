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
#   - Native/guest C23 two-read EOF-conditional source publication parity.
# - Must-Not:
#   - Replace the signed EOF branches with host-selected output bytes.
# - Allows:
#   - Inputs: frozen source, native C23 oracles, and binary stdin vectors.
#   - Outputs: real VM stdout and exact input-dependent halt boundaries.
#   - Side effects: bounded children in temporary directories.
# - Split-When:
#   - General guest C23 conditional compiler replaces the closed grammar.
# - Merge-When:
#   - P2 mutable checksum covers this exact signed EOF control boundary.
# - Summary:
#   - Two real guest inputs must control the second EOF/byte output arm.

"""Source-checked C23 branches through physical second-byte EOF guest code."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Final, final

ROOT: Final = Path(__file__).resolve().parents[1]
SOURCE: Final = ROOT / "tests/compiler/c-frontend/accepted/two_read_eof_branch.c"
NORMALIZED: Final = (
    ROOT / "tests/compiler/c-frontend/golden/two_read_eof_branch_current.json"
)
SOURCE_SHA: Final = "163a96c1724e0848a0a56bc9d6b69b04a45aabc29de58e83642325c6ffa418c3"
CLANG: Final = ROOT / ".dependencies/llvm/22.1.8/bin/clang"
FRONTEND: Final = (
    ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
)
ADAPTER: Final = ROOT / ".cache/rust/target/debug/c2malbolge_json"
DRIVER: Final = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
VM: Final = ROOT / ".cache/rust/target/debug/malbolge"
VECTORS: Final = (
    ("empty", b"", b"\x6a\x1e", 119),
    ("first-only", b"\x00", b"\x00\x1e", 119),
    ("first-high-only", b"\xff", b"\xff\x1e", 119),
    ("second-nul", b"\x81\x00", b"\x81\x9a", 175),
    ("second-high", b"\x00\xff", b"\x00\x9a", 175),
    ("unread-trailing", b"\x05\x80\x77", b"\x05\x9a", 175),
)


def environment() -> dict[str, str]:
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = os.pathsep.join(
        item
        for item in (
            str(ROOT / ".dependencies/llvm/22.1.8/lib"),
            env.get("LD_LIBRARY_PATH", ""),
        )
        if item
    )
    return env


@final
class TwoReadEofBranchPublicationTests(unittest.TestCase):
    def test_two_reads_and_real_second_eof_branch(self) -> None:
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(), SOURCE_SHA)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            temp = Path(directory)
            wrapper = temp / "main.c"
            wrapper.write_text(
                f'#include "{SOURCE}"\nint main(void) {{ emit(); return 0; }}\n',
                encoding="utf-8",
            )
            for optimization in ("-O0", "-O2"):
                binary = temp / f"native-{optimization[2:]}"
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
                    env=environment(),
                    check=False,
                    timeout=20,
                )
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                for label, stdin, expected, _steps in VECTORS:
                    with self.subTest(native=optimization, stream=label):
                        native = subprocess.run(
                            [str(binary)],
                            input=stdin,
                            capture_output=True,
                            check=False,
                            timeout=10,
                        )
                        self.assertEqual(native.returncode, 0, native.stderr)
                        self.assertEqual(native.stdout, expected)

            target = temp / "conditional.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--capsule",
                    "--max-wall-seconds",
                    "80",
                    "--output",
                    str(target),
                    str(SOURCE),
                ],
                capture_output=True,
                env=environment(),
                check=False,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(target.is_file())
            for label, stdin, expected, steps in VECTORS:
                with self.subTest(guest=label):
                    guest = subprocess.run(
                        [
                            str(VM),
                            str(target),
                            "--input-stdin",
                            "--max-steps",
                            "500",
                            "--report-steps",
                        ],
                        input=stdin,
                        capture_output=True,
                        check=False,
                        timeout=15,
                    )
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(guest.stdout, expected)
                    self.assertIn(f"malbolge-steps-v1:{steps}".encode(), guest.stderr)

    def test_forged_second_input_and_changed_source_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            temp = Path(directory)
            bad = json.loads(NORMALIZED.read_bytes())
            bad["nodes"][22]["reference"] = "external:putchar"
            payload = json.dumps(bad, separators=(",", ":")).encode()
            output = temp / "forged.malbolge"
            missing_backend = temp / "nonexistent-backend"
            result = subprocess.run(
                [
                    str(ADAPTER),
                    "--layout-backend",
                    str(missing_backend),
                    "--output",
                    str(output),
                    "--source",
                    str(SOURCE),
                ],
                input=payload,
                capture_output=True,
                check=False,
                timeout=20,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"normalized frontend rejected", result.stderr)
            self.assertFalse(output.exists())
            altered = temp / "altered.c"
            altered.write_bytes(
                SOURCE.read_bytes().replace(b"putchar(154)", b"putchar(153)")
            )
            target = temp / "altered.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--capsule",
                    "--max-wall-seconds",
                    "45",
                    "--output",
                    str(target),
                    str(altered),
                ],
                capture_output=True,
                check=False,
                timeout=55,
            )
            self.assertNotEqual(compiled.returncode, 0)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
