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
#   - Real C ignored putchar results through verified guest VM execution.
# - Must-Not:
#   - Accept host-evaluated literals or discard unsupported C effects.
# - Allows:
#   - Inputs: pinned Clang explicit (void)putchar calls and known witnesses.
#   - Outputs: exact guest bytes and fail-closed compiler statuses.
#   - Side effects: isolated ignored temporary C and capsule files only.
# - Split-When:
#   - General C statement lowering includes arbitrary discarded calls.
# - Merge-When:
#   - Native compiler end-to-end tests own all explicit no-use output calls.
# - Summary:
#   - (void)putchar(N) still reaches the normative Malbolge output device.
# - Description:
#   - No mocks: native C frontend, typed adapter, layout and VM are invoked.
# - Usage:
#   - MALBOLGE_WHITESPACE_BIN_ROOT=/path/to/debug python3.14 -B -m unittest
#     tests.test_c2malbolge_void_cast_output -v
# - Defaults:
#   - Missing pinned compiler binaries skip unless explicitly configured.

"""Explicit discard of putchar's result still executes guest byte output."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import final, override

from tests.test_c2malbolge_output_whitespace import (
    ADAPTER,
    DRIVER,
    FRONTEND,
    GUEST_INCLUDE,
    LAYOUT,
    RESOURCE,
    ROOT,
    VM,
)


@final
class CDiscardedOutputTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        binaries = (FRONTEND, ADAPTER, LAYOUT, VM)
        if (
            not GUEST_INCLUDE.is_dir()
            or not RESOURCE.is_dir()
            or any(
                not path.is_file() or not os.access(path, os.X_OK) for path in binaries
            )
        ):
            if "MALBOLGE_WHITESPACE_BIN_ROOT" in os.environ:
                self.fail("explicit pinned compiler or VM binary unavailable")
            self.skipTest("pinned C frontend, layout and guest VM required")

    def compile(self, source: Path, output: Path) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(DRIVER),
                "--frontend",
                str(FRONTEND),
                "--json-adapter",
                str(ADAPTER),
                "--layout-backend",
                str(LAYOUT),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                source.name,
                "--output",
                str(output),
                "--capsule",
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=160,
        )

    def test_casted_putchar_emits_real_guest_bytes(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            directory = Path(folder)
            for name, statements, expected, steps in (
                ("cast-a", "(void)putchar(65);", b"A", 31),
                ("spaced-cast-a", "(void) putchar(65);", b"A", 31),
                ("mixed-zero-z", "(void)putchar(0); putchar(90);", b"\x00Z", 5),
            ):
                with self.subTest(name=name):
                    source = directory / f"{name}.c"
                    output = directory / f"{name}.malbolge"
                    _ = source.write_text(
                        "#include <stdio.h>\nvoid emit(void) { " + statements + " }\n",
                        encoding="ascii",
                    )
                    compiled = self.compile(source, output)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    executed = subprocess.run(
                        [str(VM), str(output), "--report-steps"],
                        capture_output=True,
                        check=False,
                        timeout=60,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, expected)
                    self.assertEqual(
                        executed.stderr,
                        f"malbolge-steps-v1:{steps}\n".encode("ascii"),
                    )

    def test_nested_void_cast_and_arithmetic_reject_without_guest(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            directory = Path(folder)
            for name, statement in (
                ("double-discard", "(void)(void)putchar(65);"),
                ("arithmetic", "(void)putchar(65 + 0);"),
            ):
                with self.subTest(name=name):
                    source = directory / f"{name}.c"
                    output = directory / f"{name}.malbolge"
                    _ = source.write_text(
                        "#include <stdio.h>\nvoid emit(void) { " + statement + " }\n",
                        encoding="ascii",
                    )
                    compiled = self.compile(source, output)
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(output.exists())


if __name__ == "__main__":
    _ = unittest.main()
