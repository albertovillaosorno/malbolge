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
#   - Real C-to-guest forty-three-distinct-byte binary output regression.
# - Must-Not:
#   - Substitute host C execution or source-string output for guest arithmetic.
# - Allows:
#   - Inputs: pinned C frontend and independently built compiler/VM binaries.
#   - Outputs: exact binary guest stdout, steps and refused publications.
#   - Side effects: isolated project-local temporary files only.
# - Split-When:
#   - General guest byte-stream lowering replaces finite forty-three-byte witnesses.
# - Merge-When:
#   - Public compiler tests own this same C-to-guest boundary.
# - Summary:
#   - Thirty-nine CrazyData and four RotateData emit 43 distinct guest bytes.
# - Description:
#   - Verifies capsule/raw parity and rejects incomplete or forged C traces.
# - Usage:
#   - python3 -B -m unittest tests.test_c2malbolge_distinct_literal_forty_three -v
# - Defaults:
#   - No other forty-three-byte source trace is supported by this witness.

"""Pinned Clang C-to-Malbolge pipeline for forty-three guest bytes."""

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
        "MALBOLGE_FORTY_THREE_BIN_ROOT", str(ROOT / ".cache/rust/target/debug")
    )
)
ADAPTER = BIN_ROOT / "c2malbolge_json"
LAYOUT = BIN_ROOT / "malbolge_layout"
VM = BIN_ROOT / "malbolge"

EXPECTED = bytes(
    [
        81,
        46,
        79,
        29,
        26,
        47,
        27,
        28,
        36,
        38,
        17,
        167,
        5,
        184,
        252,
        182,
        64,
        45,
        73,
        52,
        56,
        62,
        146,
        228,
        164,
        226,
        174,
        218,
        172,
        8,
        213,
        171,
        221,
        162,
        222,
        170,
        11,
        217,
        156,
        227,
        163,
        210,
        173,
    ]
)

SOURCE = "".join(f"putchar({value}); " for value in EXPECTED)


@final
class FortyThreeDistinctGuestLiteralTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        tools = (FRONTEND, ADAPTER, LAYOUT, VM)
        if (
            not GUEST_INCLUDE.is_dir()
            or not RESOURCE.is_dir()
            or any(not path.is_file() or not os.access(path, os.X_OK) for path in tools)
        ):
            if "MALBOLGE_FORTY_THREE_BIN_ROOT" in os.environ:
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

    def test_forty_three_distinct_c_bytes_run_under_real_vm_raw_and_capsule(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp:
            directory = Path(temp)
            for capsule in (False, True):
                with self.subTest(capsule=capsule):
                    name = "forty-three-capsule" if capsule else "forty-three-raw"
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
                    self.assertEqual(result.stderr, b"malbolge-steps-v1:100\n")

    def test_existing_forty_two_byte_program_remains_unchanged(self) -> None:
        previous = bytes(
            [
                168,
                7,
                187,
                2,
                182,
                12,
                177,
                48,
                13,
                60,
                17,
                44,
                20,
                57,
                166,
                70,
                66,
                68,
                47,
                80,
                54,
                9,
                212,
                172,
                225,
                158,
                226,
                171,
                11,
                214,
                156,
                227,
                160,
                210,
                173,
                147,
                224,
                159,
                228,
                170,
                213,
                174,
            ]
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp:
            directory = Path(temp)
            original = "".join(f"putchar({value}); " for value in previous)
            compiled, artifact = self.compile(directory, "existing-forty-two", original)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            result = subprocess.run(
                [str(VM), str(artifact), "--report-steps"],
                capture_output=True,
                check=False,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, previous)
            self.assertEqual(result.stderr, b"malbolge-steps-v1:97\n")

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

    def test_unproved_forty_three_byte_values_and_short_prefixes_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp:
            directory = Path(temp)
            invalid = [
                (f"prefix-{count}", " ".join(SOURCE.split()[:count]))
                for count in range(3, 43)
            ]
            invalid.extend(
                [
                    (
                        "wrong-last-byte",
                        SOURCE.replace("putchar(173);", "putchar(175);"),
                    ),
                    ("wrong-second", SOURCE.replace("putchar(46);", "putchar(47);")),
                    (
                        "duplicate-eighth",
                        SOURCE.replace("putchar(29);", "putchar(81);"),
                    ),
                    (
                        "reordered-third",
                        SOURCE.replace(
                            "putchar(79); putchar(29);",
                            "putchar(29); putchar(79);",
                        ),
                    ),
                    (
                        "arithmetic",
                        SOURCE.replace("putchar(79);", "putchar(78 + 1);"),
                    ),
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
