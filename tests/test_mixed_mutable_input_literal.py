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
#   - Source-checked mutable unsigned output after one signed input effect.
# - Must-Not:
#   - Count host C output as guest execution or accept unchecked source edits.
# - Allows:
#   - Inputs: one frozen source, binary/EOF streams and negative mutations.
#   - Outputs: native C23 parity and canonical typed admission/refusal.
#   - Side effects: isolated pinned Clang/compiler/VM subprocesses.
# - Split-When:
#   - General stateful C IR includes this example in a common matrix.
# - Merge-When:
#   - Complete mutable EOF checksum proves the same I/O and storage boundary.
# - Summary:
#   - Source proof admits mixed effects before backend guest verification.

"""Source-prove a mixed signed input effect and constant-propagated C update."""

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
SOURCE: Final = (
    ROOT / "tests/compiler/c-frontend/accepted/mixed_mutable_input_literal.c"
)
CLANG: Final = ROOT / ".dependencies/llvm/22.1.8/bin/clang"
FRONTEND: Final = (
    ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
)
ADAPTER: Final = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT: Final = ROOT / ".cache/rust/target/debug/malbolge_layout"
VM: Final = ROOT / ".cache/rust/target/debug/malbolge"
DRIVER: Final = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
VECTORS: Final = (b"", b"\x00", b"\xff", b"\x00\x80\xff", b"\x05\x00\x81")
EXPECTED_BYTE: Final = b"\x0b"


def run_compiler(source: Path, target: Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            sys.executable,
            "-B",
            str(DRIVER),
            "--repository-tools",
            "--capsule",
            "--max-wall-seconds",
            "40",
            "--output",
            str(target),
            str(source),
        ],
        capture_output=True,
        check=False,
        timeout=45,
    )


@final
class MixedMutableInputLiteralTests(unittest.TestCase):
    def test_native_and_authenticated_typed_projection(self) -> None:
        self.assertEqual(
            hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            "b52c90cad6e21b07663724aab0c5651a21ecbd3b95aa8e6134e21fc0dfcd8d18",
        )
        self.assertTrue(
            all(path.is_file() for path in (CLANG, FRONTEND, ADAPTER, LAYOUT, VM))
        )
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
                binary = directory / f"native-{optimization[2:]}"
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
                        str(binary),
                    ],
                    env=env,
                    capture_output=True,
                    check=False,
                    timeout=15,
                )
                self.assertEqual(built.returncode, 0, built.stderr)
                for data in VECTORS:
                    with self.subTest(optimization=optimization, data=data):
                        run = subprocess.run(
                            [str(binary)],
                            input=data,
                            capture_output=True,
                            check=False,
                            timeout=10,
                        )
                        self.assertEqual(run.returncode, 0, run.stderr)
                        self.assertEqual(run.stdout, EXPECTED_BYTE)
            frontend = subprocess.run(
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
                env=env,
                capture_output=True,
                check=False,
                timeout=15,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            target = directory / "unpublished.malbolge"
            # The injected backend is deliberately unavailable. Reaching it
            # proves source authentication and canonical typed-IR admission,
            # not an executable guest artifact.
            projection = subprocess.run(
                [
                    str(ADAPTER),
                    "--layout-backend",
                    "/bin/false",
                    "--output",
                    str(target),
                    "--source",
                    str(SOURCE),
                ],
                input=frontend.stdout,
                capture_output=True,
                check=False,
                timeout=15,
            )
            self.assertNotEqual(projection.returncode, 0)
            self.assertIn(b"layout backend exited unsuccessfully", projection.stderr)
            self.assertFalse(target.exists())

    def test_source_mutations_never_publish(self) -> None:
        original = SOURCE.read_bytes()
        for label, old, new in (
            ("initial-value", b"checksum = 0U;", b"checksum = 1U;"),
            ("second-effect", b"checksum += 11U;", b"checksum ^= 11U;"),
            ("read-binding", b"current = getchar()", b"current = putchar(1)"),
            ("output-binding", b"putchar((int)checksum)", b"putchar((int)current)"),
        ):
            with (
                self.subTest(label=label),
                tempfile.TemporaryDirectory(dir=ROOT / ".temp") as raw,
            ):
                directory = Path(raw)
                changed = original.replace(old, new)
                self.assertNotEqual(changed, original)
                source = directory / "changed.c"
                source.write_bytes(changed)
                target = directory / "wrong.malbolge"
                result = run_compiler(source, target)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    b"normalized frontend rejected: Unsupported", result.stderr
                )
                self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
