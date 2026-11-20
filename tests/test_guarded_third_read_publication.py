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
#   - Source-C third read conditional on a second, real signed EOF input.
# - Must-Not:
#   - Replace the guarded read with host-selected effects or a fake EOF.
# - Allows:
#   - Inputs: pinned C23 source/Clang AST and finite binary streams.
#   - Outputs: native/guest stdout, finite halts, and forgery rejection.
#   - Side effects: isolated bounded compiler and VM processes.
# - Split-When:
#   - General signed EOF CFG linking supersedes closed source admission.
# - Merge-When:
#   - Full mutable checksum passes guest C23 parity.
# - Summary:
#   - Physically reads a third byte only after a successful second read.

"""Source-locked conditional third input executes inside the normative VM."""

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
SOURCE: Final = ROOT / "tests/compiler/c-frontend/accepted/guarded_third_read.c"
NORMALIZED: Final = (
    ROOT / "tests/compiler/c-frontend/golden/guarded_third_read_current.json"
)
SOURCE_SHA: Final = "65c93f567b3460dfaa2588a1a4355312abfc469fa519b1d3bc697319a26ecd14"
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
    ("first-high", b"\xff", b"\xff\x1e", 119),
    ("second-nul-third-eof", b"\x81\x00", b"\x81\x9a", 175),
    ("second-high-third-byte", b"\x00\xff\x80", b"\x00\x9a", 175),
    ("second-31", b"\x03\x1f\x80", b"\x03\x9a", 175),
    ("second-255", b"\x03\xff\x80", b"\x03\x9a", 175),
    ("third-nul-suffix", b"\x05\x80\x00\xff", b"\x05\x9a", 175),
    ("first-high-second-high", b"\xff\xff\x01", b"\xff\x9a", 175),
)


def environment() -> dict[str, str]:
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = os.pathsep.join(
        part
        for part in (
            str(ROOT / ".dependencies/llvm/22.1.8/lib"),
            env.get("LD_LIBRARY_PATH", ""),
        )
        if part
    )
    return env


@final
class GuardedThirdReadPublicationTests(unittest.TestCase):
    def test_native_c23_and_real_guest_parity(self) -> None:
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(), SOURCE_SHA)
        normalized = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(ROOT / "src/runtime/guest-c-library/contract/include"),
                "--resource-dir",
                str(ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"),
                "--source-id",
                SOURCE.name,
                str(SOURCE),
            ],
            capture_output=True,
            check=False,
            env=environment(),
            timeout=20,
        )
        self.assertEqual(normalized.returncode, 0, normalized.stderr)
        self.assertEqual(
            json.loads(normalized.stdout), json.loads(NORMALIZED.read_bytes())
        )
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
                    check=False,
                    env=environment(),
                    timeout=20,
                )
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                for label, stdin, expected, _steps in VECTORS:
                    with self.subTest(native=optimization, input=label):
                        native = subprocess.run(
                            [str(binary)],
                            input=stdin,
                            capture_output=True,
                            check=False,
                            timeout=10,
                        )
                        self.assertEqual(native.returncode, 0, native.stderr)
                        self.assertEqual(native.stdout, expected)
            target = temp / "guarded.malbolge"
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
                check=False,
                env=environment(),
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

    def test_forged_third_read_and_changed_source_never_publish(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            temp = Path(directory)
            forged = json.loads(NORMALIZED.read_bytes())
            self.assertEqual(forged["nodes"][42]["reference"], "external:getchar")
            forged["nodes"][42]["reference"] = "external:putchar"
            output = temp / "forged.malbolge"
            adapter = subprocess.run(
                [
                    str(ADAPTER),
                    "--layout-backend",
                    str(temp / "missing-layout"),
                    "--output",
                    str(output),
                    "--source",
                    str(SOURCE),
                ],
                input=json.dumps(forged).encode(),
                capture_output=True,
                check=False,
                timeout=20,
            )
            self.assertNotEqual(adapter.returncode, 0)
            self.assertIn(b"normalized frontend rejected", adapter.stderr)
            self.assertFalse(output.exists())
            altered = temp / "altered.c"
            altered.write_bytes(
                SOURCE.read_bytes().replace(
                    b"getchar();\n    }", b"getchar(), getchar();\n    }"
                )
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
