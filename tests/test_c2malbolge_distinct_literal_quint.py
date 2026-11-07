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
#   - Real C-to-Malbolge five-distinct-byte binary output regression.
# - Must-Not:
#   - Substitute host C execution for the pinned Clang and normative guest VM.
# - Allows:
#   - Inputs: bounded literal-output C and built repository compiler binaries.
#   - Outputs: exact binary guest stdout and step receipts; rejected artifacts.
#   - Side effects: isolated project-local temporary files only.
# - Split-When:
#   - General guest byte-stream synthesis supersedes finite quintuple witnesses.
# - Merge-When:
#   - Public compiler tests own this same source/guest boundary.
# - Summary:
#   - Five separate guest CrazyData writes emit Q, quote, ESC, 7, 9.
# - Description:
#   - Verifies the actual pinned source-to-current-VM route and prefix refusal.
# - Usage:
#   - python3.14 -B -m unittest tests.test_c2malbolge_distinct_literal_quint -v
# - Defaults:
#   - Other five-byte traces and incomplete prefixes remain unsupported.

"""Real pinned C frontend to five distinct guest-computed binary output bytes."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import final, override

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
GUEST_INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
BIN_ROOT = Path(
    os.environ.get("MALBOLGE_QUINT_BIN_ROOT", str(ROOT / ".cache/rust/target/debug"))
)
ADAPTER = BIN_ROOT / "c2malbolge_json"
LAYOUT = BIN_ROOT / "malbolge_layout"
VM = BIN_ROOT / "malbolge"

OUTPUT = b'Q"\x1b79'
SOURCE = "putchar('Q'); putchar('\\\"'); putchar(27); putchar('7'); putchar('9');"
ZERO_PREFIX_OUTPUT = b"\x00T=4>"
ZERO_PREFIX_SOURCE = (
    "putchar(0); putchar('T'); putchar('='); putchar('4'); putchar('>');"
)


@final
class DistinctLiteralQuintSourceTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        tools = (FRONTEND, ADAPTER, LAYOUT, VM)
        if (
            not GUEST_INCLUDE.is_dir()
            or not RESOURCE.is_dir()
            or any(not path.is_file() or not os.access(path, os.X_OK) for path in tools)
        ):
            if "MALBOLGE_QUINT_BIN_ROOT" in os.environ:
                self.fail("explicit pinned compiler/VM binaries unavailable")
            self.skipTest("pinned compiler and normative guest VM required")

    def compile(
        self, directory: Path, name: str, statements: str, *, capsule: bool = True
    ) -> tuple[subprocess.CompletedProcess[bytes], Path]:
        source = directory / f"{name}.c"
        guest = directory / f"{name}.malbolge"
        _ = source.write_text(
            "#include <stdio.h>\nvoid emit(void) { " + statements + " }\n",
            encoding="ascii",
        )
        result = subprocess.run(
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
                f"fixtures/{name}.c",
                "--output",
                str(guest),
                *(["--capsule"] if capsule else []),
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=180,
        )
        return result, guest

    def test_five_distinct_c_literals_execute_in_real_vm(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as name:
            directory = Path(name)
            compiled, artifact = self.compile(directory, "five-guest-bytes", SOURCE)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(artifact.is_file())
            guest = subprocess.run(
                [str(VM), str(artifact), "--report-steps"],
                capture_output=True,
                check=False,
                timeout=60,
            )
            self.assertEqual(guest.returncode, 0, guest.stderr)
            self.assertEqual(guest.stdout, OUTPUT)
            self.assertEqual(guest.stderr, b"malbolge-steps-v1:23\n")

    def test_zero_prefixed_five_source_effects_execute_in_guest(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as name:
            directory = Path(name)
            compiled, artifact = self.compile(
                directory, "zero-prefixed-five", ZERO_PREFIX_SOURCE
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(artifact.is_file())
            for stdin in (b"", b"\xff\x00\x80"):
                guest = subprocess.run(
                    [str(VM), str(artifact), "--report-steps"],
                    input=stdin,
                    capture_output=True,
                    check=False,
                    timeout=60,
                )
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(guest.stdout, ZERO_PREFIX_OUTPUT)
                self.assertRegex(guest.stderr, rb"^malbolge-steps-v1:[0-9]+\n$")

    def test_nonzero_prefix_of_five_source_effects_refuses(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as name:
            compiled, artifact = self.compile(
                Path(name),
                "nonzero-prefix-five",
                ZERO_PREFIX_SOURCE.replace("putchar(0)", "putchar(1)"),
            )
            self.assertNotEqual(compiled.returncode, 0)
            self.assertFalse(artifact.exists())

    def test_raw_profile_matches_capsule_binary_guest_output(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as name:
            directory = Path(name)
            compiled, artifact = self.compile(
                directory, "five-guest-raw", SOURCE, capsule=False
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(artifact.is_file())
            guest = subprocess.run(
                [
                    str(VM),
                    str(artifact),
                    "--raw-profile",
                    "malbolge-2026",
                    "--report-steps",
                ],
                capture_output=True,
                check=False,
                timeout=60,
            )
            self.assertEqual(guest.returncode, 0, guest.stderr)
            self.assertEqual(guest.stdout, OUTPUT)
            self.assertEqual(guest.stderr, b"malbolge-steps-v1:23\n")

    def test_preexisting_target_refuses_clobber(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as name:
            directory = Path(name)
            artifact = directory / "preexisting.malbolge"
            _ = artifact.write_bytes(b"previous-owner-binary\x00")
            compiled, target = self.compile(directory, "preexisting", SOURCE)
            self.assertEqual(target, artifact)
            self.assertNotEqual(compiled.returncode, 0)
            self.assertEqual(artifact.read_bytes(), b"previous-owner-binary\x00")

    def test_unproved_five_byte_traces_and_prefixes_never_publish(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as name:
            directory = Path(name)
            for stem, statements in (
                (
                    "missing-fifth",
                    "putchar('Q'); putchar('\\\"'); putchar(27); putchar('7');",
                ),
                ("missing-fourth", "putchar('Q'); putchar('\\\"'); putchar(27);"),
                ("missing-third", "putchar('Q'); putchar('\\\"');"),
                ("bad-fifth", SOURCE.replace("putchar('9')", "putchar('8')")),
                ("bad-escape", SOURCE.replace("putchar(27)", "putchar(26)")),
                ("extra", SOURCE + " putchar('!');"),
                ("arithmetic", SOURCE.replace("putchar(27)", "putchar(26 + 1)")),
            ):
                with self.subTest(name=stem):
                    compiled, artifact = self.compile(directory, stem, statements)
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(artifact.exists())


if __name__ == "__main__":
    _ = unittest.main()
