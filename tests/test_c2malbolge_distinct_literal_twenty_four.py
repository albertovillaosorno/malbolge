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
#   - Real C-to-guest twenty-four-distinct-byte binary output regression.
# - Must-Not:
#   - Substitute host C execution or source-string output for guest arithmetic.
# - Allows:
#   - Inputs: pinned C frontend and independently built compiler/VM binaries.
#   - Outputs: exact binary guest stdout, steps and refused publications.
#   - Side effects: isolated project-local temporary files only.
# - Split-When:
#   - General guest byte-stream lowering replaces finite twenty-four-byte witnesses.
# - Merge-When:
#   - Public compiler tests own this same C-to-guest boundary.
# - Summary:
#   - Twenty-one CrazyData and three RotateData emit twenty-four distinct guest bytes.
# - Description:
#   - Verifies capsule/raw parity and rejects incomplete or forged C traces.
# - Usage:
#   - python3 -B -m unittest tests.test_c2malbolge_distinct_literal_twenty_four -v
# - Defaults:
#   - No other twenty-four-byte source trace is supported by this witness.

"""Pinned Clang C-to-Malbolge pipeline for twenty-four guest-computed binary bytes."""

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
    os.environ.get(
        "MALBOLGE_TWENTY_FOUR_BIN_ROOT", str(ROOT / ".cache/rust/target/debug")
    )
)
ADAPTER = BIN_ROOT / "c2malbolge_json"
LAYOUT = BIN_ROOT / "malbolge_layout"
VM = BIN_ROOT / "malbolge"

EXPECTED = bytes(
    [
        62,
        11,
        44,
        18,
        54,
        1,
        61,
        149,
        15,
        157,
        23,
        139,
        33,
        147,
        146,
        32,
        148,
        14,
        155,
        24,
        138,
        28,
        47,
        35,
    ]
)

SOURCE = (
    "putchar(62); putchar(11); putchar(44); putchar(18); "
    "putchar(54); putchar(1); putchar(61); putchar(149); "
    "putchar(15); putchar(157); putchar(23); putchar(139); "
    "putchar(33); putchar(147); putchar(146); putchar(32); "
    "putchar(148); putchar(14); putchar(155); putchar(24); "
    "putchar(138); putchar(28); putchar(47); putchar(35); "
)


@final
class TwentyFourDistinctGuestLiteralTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        tools = (FRONTEND, ADAPTER, LAYOUT, VM)
        if (
            not GUEST_INCLUDE.is_dir()
            or not RESOURCE.is_dir()
            or any(not path.is_file() or not os.access(path, os.X_OK) for path in tools)
        ):
            if "MALBOLGE_TWENTY_FOUR_BIN_ROOT" in os.environ:
                self.fail("explicit pinned compiler or VM binary unavailable")
            self.skipTest("pinned compiler and normative VM required")

    def compile(
        self, directory: Path, stem: str, source: str, *, capsule: bool = True
    ) -> tuple[subprocess.CompletedProcess[bytes], Path]:
        file = directory / f"{stem}.c"
        guest = directory / f"{stem}.malbolge"
        _ = file.write_text(
            "#include <stdio.h>\nvoid emit(void) { " + source + " }\n",
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

    def test_twenty_four_distinct_c_bytes_run_under_real_vm_raw_and_capsule(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp:
            directory = Path(temp)
            for capsule in (False, True):
                with self.subTest(capsule=capsule):
                    name = "twenty-four-capsule" if capsule else "twenty-four-raw"
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
                    self.assertEqual(result.stderr, b"malbolge-steps-v1:72\n")

    def test_existing_two_byte_q_period_prefix_keeps_its_guest_witness(self) -> None:
        # The earlier two-byte Q. source retains its separately verified path.
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp:
            directory = Path(temp)
            compiled, artifact = self.compile(
                directory, "existing-q-period", "putchar(81); putchar(46);"
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            result = subprocess.run(
                [str(VM), str(artifact), "--report-steps"],
                capture_output=True,
                check=False,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, b"Q.")
            self.assertEqual(result.stderr, b"malbolge-steps-v1:8\n")

    def test_unproved_twenty_four_byte_values_and_short_prefixes_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp:
            directory = Path(temp)
            invalid = [
                (f"prefix-{count}", " ".join(SOURCE.split()[:count]))
                for count in range(2, 24)
            ]
            invalid.extend(
                [
                    (
                        "wrong-twenty-fourth",
                        SOURCE.replace("putchar(35);", "putchar(36);"),
                    ),
                    ("wrong-second", SOURCE.replace("putchar(11);", "putchar(12);")),
                    (
                        "duplicate-eighth",
                        SOURCE.replace("putchar(149);", "putchar(62);"),
                    ),
                    (
                        "reordered-third",
                        SOURCE.replace(
                            "putchar(44); putchar(18);",
                            "putchar(18); putchar(44);",
                        ),
                    ),
                    ("arithmetic", SOURCE.replace("putchar(11);", "putchar(10 + 1);")),
                    ("extra", SOURCE + " putchar(99);"),
                ]
            )
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
