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
#   - Installed Unix compiler and VM shims resolve their repository tool paths.
# - Must-Not:
#   - Replace a native C frontend or guest VM with a stub for semantic evidence.
# - Allows:
#   - Inputs: isolated symlink fixtures and repository-pinned native binaries.
#   - Outputs: actual compiled guest output and shim installation checks.
#   - Side effects: ignored temporary files, never repository build outputs.
# - Split-When:
#   - A supported compiler installer gains independent platform packaging.
# - Merge-When:
#   - Installer and command-line integration tests share one entrypoint suite.
# - Summary:
#   - Installed commands must work outside the repository's scripts directory.
# - Description:
#   - Fake VM binary tests only symlink resolution; real VM verifies C behavior.
# - Usage:
#   - python3.14 -B -m unittest tests.test_c2malbolge_unix_entrypoint -v
# - Defaults:
#   - Real guest test skips if the pinned native toolchain is not built.

"""Installed Unix compiler and VM shims preserve end-to-end execution."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import final, override

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "src/interface/command-line/composition/scripts"
INSTALL = SCRIPTS / "install-unix.sh"
VM_SHIM = SCRIPTS / "malbolge"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
RUST_BIN = ROOT / ".cache/rust/target/debug"


@unittest.skipIf(os.name == "nt", "Unix symlink installation only")
@final
class UnixCompilerEntrypointTests(unittest.TestCase):
    @override
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self.directory = Path()
        self.install_dir = Path()

    @override
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / ".temp")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.install_dir = self.directory / "installed commands"

    def install(self) -> None:
        completed = subprocess.run(
            [str(INSTALL), str(self.install_dir)],
            capture_output=True,
            check=False,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_installed_vm_link_executes_binary_next_to_original_script(self) -> None:
        script_dir = self.directory / "copied tool" / "scripts"
        executable = script_dir / "bin" / "malbolge"
        _ = executable.parent.mkdir(parents=True)
        script = script_dir / "malbolge"
        _ = shutil.copy2(VM_SHIM, script)
        _ = executable.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n', encoding="ascii")
        executable.chmod(0o700)
        self.install_dir.mkdir()
        link = self.install_dir / "malbolge"
        # Installed links may use relative targets rather than absolute ones.
        _ = link.symlink_to(Path("../copied tool/scripts/malbolge"))
        completed = subprocess.run(
            [str(link), "program.malbolge", "--report-steps"],
            capture_output=True,
            check=False,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, b"program.malbolge\n--report-steps\n")

    def test_repository_vm_refuses_missing_binary_without_release_fallback(
        self,
    ) -> None:
        script_dir = self.directory / "copied tool" / "scripts"
        binary = script_dir / "bin" / "malbolge"
        binary.parent.mkdir(parents=True)
        shim = script_dir / "malbolge"
        _ = shutil.copy2(VM_SHIM, shim)
        _ = binary.write_text('#!/bin/sh\nprintf "fallback\n"\n', encoding="ascii")
        binary.chmod(0o700)
        completed = subprocess.run(
            [str(shim), "--repository-tools", "program.malbolge"],
            capture_output=True,
            check=False,
            timeout=10,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(b"repository VM binary is not built", completed.stderr)
        self.assertNotIn(b"fallback", completed.stdout)

    def test_installer_links_both_vm_and_compiler_commands(self) -> None:
        self.install()
        for name in ("malbolge", "c2malbolge"):
            with self.subTest(name=name):
                link = self.install_dir / name
                self.assertTrue(link.is_symlink())
                self.assertEqual(link.resolve(), (SCRIPTS / name).resolve())

    def test_installed_compiler_help_reaches_actual_driver(self) -> None:
        self.install()
        completed = subprocess.run(
            [str(self.install_dir / "c2malbolge"), "--help"],
            capture_output=True,
            check=False,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn(b"--repository-tools", completed.stdout)
        self.assertIn(b"--output", completed.stdout)

    def _assert_installed_guest_output(
        self, source_bytes: bytes, expected_stdout: bytes, expected_steps: bytes | None
    ) -> None:
        binaries = (
            FRONTEND,
            RUST_BIN / "c2malbolge_json",
            RUST_BIN / "malbolge_layout",
            RUST_BIN / "malbolge",
        )
        if not RESOURCE.is_dir() or not all(
            path.is_file() and os.access(path, os.X_OK) for path in binaries
        ):
            self.skipTest("repository-pinned C toolchain and VM not built")
        self.install()
        source = self.directory / "emit.c"
        target = self.directory / "emit.malbolge"
        _ = source.write_bytes(source_bytes)
        compiled = subprocess.run(
            [
                str(self.install_dir / "c2malbolge"),
                "--repository-tools",
                "--capsule",
                "--output",
                str(target),
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=120,
        )
        self.assertEqual(compiled.returncode, 0, compiled.stderr)
        self.assertTrue(target.is_file())
        # Run through the *installed* VM shim using the same repository tool
        # family. The package-local release VM can be older than this compiler.
        executed = subprocess.run(
            [
                str(self.install_dir / "malbolge"),
                "--repository-tools",
                str(target),
                "--report-steps",
            ],
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(executed.returncode, 0, executed.stderr)
        self.assertEqual(executed.stdout, expected_stdout)
        if expected_steps is None:
            self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
        else:
            self.assertEqual(executed.stderr, expected_steps)

    def test_installed_compiler_emits_executable_guest_output(self) -> None:
        self._assert_installed_guest_output(
            b"#include <stdio.h>\nvoid emit(void) { putchar(0); putchar(0); return; }\n",
            b"\x00\x00",
            b"malbolge-steps-v1:3\n",
        )

    def test_installed_compiler_emits_witnessed_ascii_output(self) -> None:
        self._assert_installed_guest_output(
            b"#include <stdio.h>\nvoid emit(void) { putchar(65); putchar(65); return; }\n",
            b"AA",
            None,
        )


if __name__ == "__main__":
    _ = unittest.main()
