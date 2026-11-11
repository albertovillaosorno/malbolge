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
#   - Real C-to-guest forty-six-distinct-byte binary output regression.
# - Must-Not:
#   - Substitute host C execution or source-string output for guest arithmetic.
# - Allows:
#   - Inputs: pinned C frontend and independently built compiler/VM binaries.
#   - Outputs: exact binary guest stdout, steps and refused publications.
#   - Side effects: isolated project-local temporary files only.
# - Split-When:
#   - General guest byte-stream lowering replaces finite forty-six-byte witnesses.
# - Merge-When:
#   - Public compiler tests own this same C-to-guest boundary.
# - Summary:
#   - Forty CrazyData and six RotateData emit 46 distinct guest bytes.
# - Description:
#   - Verifies capsule/raw parity and rejects incomplete or forged C traces.
# - Usage:
#   - python3 -B -m unittest tests.test_c2malbolge_distinct_literal_forty_six -v
# - Defaults:
#   - No other forty-six-byte source trace is supported by this witness.

"""Pinned Clang C-to-Malbolge pipeline for forty-six guest bytes."""

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
        "MALBOLGE_FORTY_SIX_BIN_ROOT", str(ROOT / ".cache/rust/target/debug")
    )
)
ADAPTER = BIN_ROOT / "c2malbolge_json"
LAYOUT = BIN_ROOT / "malbolge_layout"
VM = BIN_ROOT / "malbolge"

EXPECTED = bytes(
    [
        84,
        34,
        79,
        35,
        83,
        30,
        9,
        8,
        226,
        171,
        221,
        126,
        192,
        125,
        186,
        129,
        188,
        123,
        42,
        16,
        48,
        14,
        47,
        17,
        45,
        163,
        255,
        167,
        0,
        162,
        1,
        166,
        252,
        207,
        165,
        206,
        159,
        210,
        161,
        204,
        144,
        227,
        174,
        225,
        173,
        228,
    ]
)

SOURCE = "".join(f"putchar({value}); " for value in EXPECTED)


@final
class FortySixDistinctGuestLiteralTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        tools = (FRONTEND, ADAPTER, LAYOUT, VM)
        if (
            not GUEST_INCLUDE.is_dir()
            or not RESOURCE.is_dir()
            or any(not path.is_file() or not os.access(path, os.X_OK) for path in tools)
        ):
            if "MALBOLGE_FORTY_SIX_BIN_ROOT" in os.environ:
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

    def test_forty_six_distinct_c_bytes_run_under_real_vm_raw_and_capsule(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp:
            directory = Path(temp)
            for capsule in (False, True):
                with self.subTest(capsule=capsule):
                    name = "forty-six-capsule" if capsule else "forty-six-raw"
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
                    self.assertEqual(result.stderr, b"malbolge-steps-v1:106\n")

    def test_existing_forty_five_byte_program_remains_unchanged(self) -> None:
        previous = bytes(
            [
                81,
                62,
                53,
                56,
                84,
                31,
                78,
                135,
                209,
                165,
                153,
                9,
                8,
                199,
                198,
                194,
                145,
                225,
                167,
                172,
                152,
                219,
                155,
                160,
                183,
                191,
                124,
                181,
                44,
                203,
                18,
                180,
                248,
                202,
                14,
                149,
                45,
                171,
                51,
                61,
                57,
                5,
                83,
                35,
                27,
            ]
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp:
            directory = Path(temp)
            original = "".join(f"putchar({value}); " for value in previous)
            compiled, artifact = self.compile(
                directory, "existing-forty-five", original
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            result = subprocess.run(
                [str(VM), str(artifact), "--report-steps"],
                capture_output=True,
                check=False,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, previous)
            self.assertEqual(result.stderr, b"malbolge-steps-v1:105\n")

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

    def test_unproved_forty_six_byte_values_and_short_prefixes_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp:
            directory = Path(temp)
            invalid = [
                (f"prefix-{count}", " ".join(SOURCE.split()[:count]))
                for count in range(2, 46)
            ]
            invalid.extend(
                [
                    (
                        "wrong-last-byte",
                        SOURCE.replace("putchar(228);", "putchar(229);"),
                    ),
                    ("wrong-second", SOURCE.replace("putchar(34);", "putchar(33);")),
                    (
                        "duplicate-eighth",
                        SOURCE.replace("putchar(8);", "putchar(84);"),
                    ),
                    (
                        "reordered-third",
                        SOURCE.replace(
                            "putchar(79); putchar(35);",
                            "putchar(35); putchar(79);",
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
