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
#   - Real C-to-guest six-distinct-byte binary output regression.
# - Must-Not:
#   - Substitute host C execution or source-string output for guest arithmetic.
# - Allows:
#   - Inputs: pinned C frontend and independently built compiler/VM binaries.
#   - Outputs: exact binary guest stdout, steps and refused publications.
#   - Side effects: isolated project-local temporary files only.
# - Split-When:
#   - General guest byte-stream lowering replaces finite six-byte witnesses.
# - Merge-When:
#   - Public compiler tests own this same C-to-guest boundary.
# - Summary:
#   - Six separate guest CrazyData writes emit Q, FS, O, GS, P, ESC.
# - Description:
#   - Verifies capsule/raw parity and rejects incomplete or forged C traces.
# - Usage:
#   - python3 -B -m unittest tests.test_c2malbolge_distinct_literal_six -v
# - Defaults:
#   - No other six-byte source trace is supported by this witness.

"""Pinned Clang C-to-Malbolge pipeline for six guest-computed binary bytes."""

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
    os.environ.get("MALBOLGE_SIX_BIN_ROOT", str(ROOT / ".cache/rust/target/debug"))
)
ADAPTER = BIN_ROOT / "c2malbolge_json"
LAYOUT = BIN_ROOT / "malbolge_layout"
VM = BIN_ROOT / "malbolge"

EXPECTED = bytes([0x51, 0x1C, 0x4F, 0x1D, 0x50, 0x1B])
SOURCE = "putchar(81); putchar(28); putchar(79); putchar(29); putchar(80); putchar(27);"


@final
class SixDistinctGuestLiteralTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        tools = (FRONTEND, ADAPTER, LAYOUT, VM)
        if (
            not GUEST_INCLUDE.is_dir()
            or not RESOURCE.is_dir()
            or any(not path.is_file() or not os.access(path, os.X_OK) for path in tools)
        ):
            if "MALBOLGE_SIX_BIN_ROOT" in os.environ:
                self.fail("explicit pinned compiler or VM binary unavailable")
            self.skipTest("pinned compiler and normative VM required")

    def compile(
        self,
        directory: Path,
        stem: str,
        source: str,
        *,
        capsule: bool = True,
        complete_source: bool = False,
    ) -> tuple[subprocess.CompletedProcess[bytes], Path]:
        file = directory / f"{stem}.c"
        guest = directory / f"{stem}.malbolge"
        _ = file.write_text(
            source if complete_source else "#include <stdio.h>\nvoid emit(void) { " + source + " }\n",
            encoding="utf-8",
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
                f"fixtures/{stem}.c",
                "--output",
                str(guest),
                *(["--capsule"] if capsule else []),
                str(file),
            ],
            capture_output=True,
            check=False,
            timeout=180,
        )
        return result, guest

    def test_six_distinct_c_bytes_run_under_real_vm_raw_and_capsule(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp:
            directory = Path(temp)
            for capsule in (False, True):
                with self.subTest(capsule=capsule):
                    name = "six-capsule" if capsule else "six-raw"
                    compiled, artifact = self.compile(
                        directory, name, SOURCE, capsule=capsule
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(artifact.is_file())
                    runner = [str(VM), str(artifact)]
                    if not capsule:
                        runner.extend(["--raw-profile", "malbolge-2026"])
                    runner.append("--report-steps")
                    result = subprocess.run(
                        runner,
                        capture_output=True,
                        check=False,
                        timeout=60,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, EXPECTED)
                    self.assertEqual(result.stderr, b"malbolge-steps-v1:15\n")

    def test_two_trip_conditional_source_outputs_six_guest_bytes(self) -> None:
        tracked = (
            ROOT
            / "tests/compiler/c-frontend/accepted/local_zero_prefix_six_stream.c"
        ).read_text(encoding="utf-8")
        expected = bytes([0, 81, 34, 27, 55, 57])
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp:
            directory = Path(temp)
            compiled, artifact = self.compile(
                directory, "six-stateful", tracked, complete_source=True
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(artifact.is_file())
            for stdin in (b"", b"\x00\x80\xff"):
                with self.subTest(stdin=stdin):
                    result = subprocess.run(
                        [str(VM), str(artifact), "--report-steps"],
                        input=stdin,
                        capture_output=True,
                        check=False,
                        timeout=60,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, expected)
                    self.assertEqual(result.stderr, b"malbolge-steps-v1:23\n")
            # An extra call in the selected branch changes the effect count
            # and must fail before any seven-byte artifact is published.
            altered = tracked.replace(
                "            putchar((int)b);",
                "            putchar((int)b); putchar((int)b);",
                1,
            )
            self.assertNotEqual(altered, tracked)
            rejected, output = self.compile(
                directory, "six-extra-call", altered, complete_source=True
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertFalse(output.exists())

    def test_nonzero_leading_two_trip_c_loop_emits_binary_guest_stream(self) -> None:
        tracked = (
            ROOT
            / "tests/compiler/c-frontend/accepted/local_nonzero_prefix_six_stream.c"
        ).read_text(encoding="utf-8")
        # Independent unsigned-C state trace: 53,54,53 then 0,80,27.
        expected = bytes([53, 54, 53, 0, 80, 27])
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp:
            directory = Path(temp)
            compiled, artifact = self.compile(
                directory, "six-nonzero", tracked, complete_source=True
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(artifact.is_file())
            for stdin in (b"", b"\x00\x80\xff"):
                with self.subTest(stdin=stdin):
                    result = subprocess.run(
                        [str(VM), str(artifact), "--report-steps"],
                        input=stdin,
                        capture_output=True,
                        check=False,
                        timeout=60,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, expected)
                    self.assertEqual(result.stderr, b"malbolge-steps-v1:19\n")
            # Source admission, not a byte oracle, must reject unproved C.
            invalid = tracked.replace(
                "            putchar((int)b);",
                "            putchar((int)b); putchar((int)b);",
                1,
            )
            self.assertNotEqual(invalid, tracked)
            rejected, absent = self.compile(
                directory, "six-unproved-arithmetic", invalid, complete_source=True
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertFalse(absent.exists())

    def test_unproved_six_byte_effects_refuse_without_artifacts(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp:
            directory = Path(temp)
            # Different literal values and repeated bytes are legitimate
            # search candidates now. Reject only unproved source effects.
            invalid = [
                ("extra", SOURCE + " putchar(55);"),
                ("input", SOURCE.replace("putchar(28);", "putchar(getchar());")),
                ("invalid-call", SOURCE.replace("putchar(28);", "putchar(28, 29);")),
            ]
            for name, source in invalid:
                with self.subTest(name=name):
                    compiled, artifact = self.compile(directory, name, source)
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(artifact.exists())

    def test_existing_output_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp:
            directory = Path(temp)
            artifact = directory / "occupied.malbolge"
            _ = artifact.write_bytes(b"prior-owner\x00")
            compiled, actual = self.compile(directory, "occupied", SOURCE)
            self.assertEqual(actual, artifact)
            self.assertNotEqual(compiled.returncode, 0)
            self.assertEqual(artifact.read_bytes(), b"prior-owner\x00")


if __name__ == "__main__":
    _ = unittest.main()
