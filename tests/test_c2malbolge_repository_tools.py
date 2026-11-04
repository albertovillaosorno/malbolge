# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - LicenseRef-Proprietary
# Confidential:
#   - true
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - Explicit repository-pinned compiler tool selection and executable guest proof.
# - Must-Not:
#   - Replace pinned Clang with stub JSON or pretend to bootstrap absent tools.
# - Allows:
#   - Inputs: bounded native C file and repository-pinned built toolchain.
#   - Outputs: actual current-profile capsule and guest VM stdout/step evidence.
#   - Side effects: ignored .temp fixtures only.
# - Split-When:
#   - A supported installer takes over the local compiler build lifecycle.
# - Merge-When:
#   - The native source compiler CLI owns a full turnkey integration suite.
# - Summary:
#   - A single opt-in flag can compile C with the already built pinned toolchain.
# - Description:
#   - Invalid option combinations refuse before any frontend process launch.
# - Usage:
#   - python3.14 -B -m unittest tests.test_c2malbolge_repository_tools -v
# - Defaults:
#   - Skip real guest execution if actual pinned executables are unprovisioned.

"""Repository-pinned tools are an opt-in to real C-to-guest compilation."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import final

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
NATIVE = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin"
NATIVE_NAME = "malbolge-c-frontend.exe" if os.name == "nt" else "malbolge-c-frontend"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
RUST = ROOT / ".cache/rust/target/debug"
RUST_SUFFIX = ".exe" if os.name == "nt" else ""
SOURCE = b"void noop(void) { return; }\n"


@final
class RepositoryToolCompilerTests(unittest.TestCase):
    def _command(self, source: Path, target: Path, *extra: str) -> list[str]:
        return [
            sys.executable,
            "-B",
            str(DRIVER),
            "--repository-tools",
            "--output",
            str(target),
            *extra,
            str(source),
        ]

    def _real_binaries(self) -> Path:
        guest = RUST / f"malbolge{RUST_SUFFIX}"
        binaries = (
            NATIVE / NATIVE_NAME,
            RUST / f"c2malbolge_json{RUST_SUFFIX}",
            RUST / f"malbolge_layout{RUST_SUFFIX}",
            guest,
        )
        if not RESOURCE.is_dir() or not all(
            path.is_file() and os.access(path, os.X_OK) for path in binaries
        ):
            self.skipTest("actual repository-pinned compiler/VM tools not provisioned")
        return guest

    def test_missing_explicit_tools_cannot_fall_through_to_repository_mode(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            root = Path(temporary)
            source, target = root / "noop.c", root / "noop.malbolge"
            _ = source.write_bytes(SOURCE)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--output",
                    str(target),
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=10,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn(b"explicit compiler tools required", completed.stderr)
            self.assertFalse(target.exists())

    def test_repository_mode_rejects_mixed_explicit_capabilities(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            root = Path(temporary)
            source, target = root / "noop.c", root / "noop.malbolge"
            _ = source.write_bytes(SOURCE)
            for option in (
                "--frontend",
                "--json-adapter",
                "--layout-backend",
                "--guest-include",
                "--resource-dir",
            ):
                with self.subTest(option=option):
                    completed = subprocess.run(
                        self._command(source, target, option, str(root)),
                        capture_output=True,
                        check=False,
                        timeout=10,
                    )
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertIn(b"cannot be mixed", completed.stderr)
                    self.assertFalse(target.exists())

    def test_native_source_basename_compiles_and_runs_real_capsule(self) -> None:
        vm = self._real_binaries()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            root = Path(temporary)
            source, target = root / "not-in-the-repo.c", root / "result.malbolge"
            _ = source.write_bytes(SOURCE)
            command = self._command(source, target, "--capsule")
            compiled = subprocess.run(
                command, capture_output=True, check=False, timeout=120
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertGreater(target.stat().st_size, len(SOURCE))
            executed = subprocess.run(
                [str(vm), str(target), "--report-steps"],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, b"")
            self.assertEqual(executed.stderr, b"malbolge-steps-v1:2\n")

            original_artifact = target.read_bytes()
            repeat = subprocess.run(
                command, capture_output=True, check=False, timeout=10
            )
            self.assertNotEqual(repeat.returncode, 0)
            self.assertIn(b"no-clobber", repeat.stderr)
            self.assertEqual(target.read_bytes(), original_artifact)

    def test_pinned_two_zero_calls_emit_ordered_guest_nul_bytes(self) -> None:
        vm = self._real_binaries()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            source = Path(temporary) / "two-zeros.c"
            target = Path(temporary) / "two-zeros.malbolge"
            _ = source.write_bytes(
                b"#include <stdio.h>\nvoid emit(void) { putchar(0); putchar(0); return; }\n"
            )
            compiled = subprocess.run(
                self._command(source, target, "--capsule"),
                capture_output=True,
                check=False,
                timeout=120,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = subprocess.run(
                [str(vm), str(target), "--report-steps"],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, b"\x00\x00")
            self.assertEqual(executed.stderr, b"malbolge-steps-v1:3\n")

    def test_native_zero_output_emits_real_nul_and_nonzero_is_rejected(self) -> None:
        vm = self._real_binaries()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            directory = Path(temporary)
            good = directory / "emit.c"
            target = directory / "emit.malbolge"
            _ = good.write_bytes(
                b"#include <stdio.h>\nvoid emit(void) { putchar(0); return; }\n"
            )
            compiled = subprocess.run(
                self._command(good, target, "--capsule"),
                capture_output=True,
                check=False,
                timeout=120,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = subprocess.run(
                [str(vm), str(target), "--report-steps"],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, b"\x00")
            self.assertEqual(executed.stderr, b"malbolge-steps-v1:2\n")

            bad = directory / "not-supported.c"
            rejected_target = directory / "not-supported.malbolge"
            _ = bad.write_bytes(
                b"#include <stdio.h>\nvoid emit(void) { putchar(1); return; }\n"
            )
            rejected = subprocess.run(
                self._command(bad, rejected_target, "--capsule"),
                capture_output=True,
                check=False,
                timeout=120,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn(b"normalized frontend rejected", rejected.stderr)
            self.assertFalse(rejected_target.exists())


if __name__ == "__main__":
    _ = unittest.main()
