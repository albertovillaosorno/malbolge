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
#   - Real C-to-guest twelve-distinct-byte binary output regression.
# - Must-Not:
#   - Substitute host C execution or source-string output for guest arithmetic.
# - Allows:
#   - Inputs: pinned C frontend and independently built compiler/VM binaries.
#   - Outputs: exact binary guest stdout, steps and refused publications.
#   - Side effects: isolated project-local temporary files only.
# - Split-When:
#   - General guest byte-stream lowering replaces finite twelve-byte witnesses.
# - Merge-When:
#   - Public compiler tests own this same C-to-guest boundary.
# - Summary:
#   - Eleven CrazyData and one RotateData write emit twelve distinct guest bytes.
# - Description:
#   - Verifies capsule/raw parity and rejects incomplete or forged C traces.
# - Usage:
#   - python3 -B -m unittest tests.test_c2malbolge_distinct_literal_twelve -v
# - Defaults:
#   - Only independently verified twelve-byte guest traces are supported.

"""Pinned Clang C-to-Malbolge pipeline for twelve guest-computed binary bytes."""

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
    os.environ.get("MALBOLGE_TWELVE_BIN_ROOT", str(ROOT / ".cache/rust/target/debug"))
)
ADAPTER = BIN_ROOT / "c2malbolge_json"
LAYOUT = BIN_ROOT / "malbolge_layout"
VM = BIN_ROOT / "malbolge"

EXPECTED = bytes(
    [0x51, 0x37, 0x34, 0x38, 0xFB, 0xCE, 0x9F, 0x98, 0xB8, 0xB4, 0x83, 0xCD]
)
ALTERNATE = bytes([81, 55, 52, 56, 80, 139, 207, 185, 178, 186, 206, 157])
ALTERNATE_SOURCE = " ".join(f"putchar({value});" for value in ALTERNATE)
INTERLEAVED = bytes([62, 9, 13, 13, 40, 46, 19, 61, 10, 46, 10, 61])
INTERLEAVED_SOURCE = " ".join(f"putchar({value});" for value in INTERLEAVED)
WIDER_TERMINAL = bytes([181, 79, 66, 61, 51, 8, 80, 35, 180, 77, 93, 49])
WIDER_TERMINAL_SOURCE = " ".join(f"putchar({value});" for value in WIDER_TERMINAL)
SOURCE = (
    "putchar(81); putchar(55); putchar(52); putchar(56); "
    "putchar(251); putchar(206); putchar(159); putchar(152); "
    "putchar(184); putchar(180); putchar(131); putchar(205);"
)


@final
class TwelveDistinctGuestLiteralTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        tools = (FRONTEND, ADAPTER, LAYOUT, VM)
        if (
            not GUEST_INCLUDE.is_dir()
            or not RESOURCE.is_dir()
            or any(not path.is_file() or not os.access(path, os.X_OK) for path in tools)
        ):
            if "MALBOLGE_TWELVE_BIN_ROOT" in os.environ:
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

    def test_twelve_distinct_c_bytes_run_under_real_vm_raw_and_capsule(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp:
            directory = Path(temp)
            for capsule in (False, True):
                with self.subTest(capsule=capsule):
                    name = "twelve-capsule" if capsule else "twelve-raw"
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
                    self.assertEqual(result.stderr, b"malbolge-steps-v1:27\n")

    def test_nonfixture_twelve_byte_guest_output_is_independently_replayed(self) -> None:
        # The oracle comes from an independently encoded twelve-write VM
        # program: one rotation at output six, rather than the fixed witness's
        # rotation at output five. The source adapter must prove each call.
        self.assertNotEqual(ALTERNATE, EXPECTED)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp:
            directory = Path(temp)
            compiled, artifact = self.compile(
                directory, "twelve-nonfixture", ALTERNATE_SOURCE
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(artifact.is_file())
            for stdin in (b"", b"\x00\xff\x80"):
                with self.subTest(stdin=stdin):
                    result = subprocess.run(
                        [str(VM), str(artifact), "--report-steps"],
                        input=stdin,
                        capture_output=True,
                        check=False,
                        timeout=60,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, ALTERNATE)
                    self.assertEqual(result.stderr, b"malbolge-steps-v1:27\n")
            altered = ALTERNATE_SOURCE + " putchar(1);"
            refused, absent = self.compile(directory, "extra-output", altered)
            self.assertNotEqual(refused.returncode, 0)
            self.assertFalse(absent.exists())

    def test_interleaved_repeated_outputs_are_executed_by_guest(self) -> None:
        # The fourth C output repeats the third distinct SSA definition's
        # value, without introducing another guest arithmetic write. The
        # original single-write-per-output grammar refused this full source.
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp:
            directory = Path(temp)
            compiled, artifact = self.compile(
                directory, "interleaved-twelve", INTERLEAVED_SOURCE
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(artifact.is_file())
            for guest_input in (b"", b"\x00\xff\x80"):
                with self.subTest(stdin=guest_input):
                    result = subprocess.run(
                        [str(VM), str(artifact), "--input-stdin", "--report-steps"],
                        input=guest_input,
                        capture_output=True,
                        check=False,
                        timeout=60,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, INTERLEAVED)
                    self.assertEqual(result.stderr, b"malbolge-steps-v1:34\n")
            extra, absent = self.compile(
                directory, "interleaved-extra", INTERLEAVED_SOURCE + " putchar(1);"
            )
            self.assertNotEqual(extra.returncode, 0)
            self.assertFalse(absent.exists())

    def test_wider_terminal_guest_stream_from_actual_c(self) -> None:
        # This stream comes from a 39-cell relocated VM program with
        # interleaved no-op data strides. The original 36-cell search cannot
        # recover its output, but the independently verified wider geometry
        # must publish a real guest rather than synthesize host stdout.
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp:
            directory = Path(temp)
            compiled, artifact = self.compile(
                directory, "wider-guest", WIDER_TERMINAL_SOURCE
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(artifact.is_file())
            for stdin in (b"", b"\xff\x00\x80"):
                with self.subTest(stdin=stdin):
                    executed = subprocess.run(
                        [str(VM), str(artifact), "--input-stdin", "--report-steps"],
                        input=stdin,
                        capture_output=True,
                        check=False,
                        timeout=60,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, WIDER_TERMINAL)
                    self.assertEqual(executed.stderr, b"malbolge-steps-v1:39\n")
            refused, absent = self.compile(
                directory,
                "wider-guest-extra",
                WIDER_TERMINAL_SOURCE + " putchar(1);",
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertFalse(absent.exists())

    def test_unproved_twelve_byte_values_and_short_prefixes_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp:
            directory = Path(temp)
            invalid = [
                (f"prefix-{count}", " ".join(SOURCE.split()[:count]))
                for count in range(2, 12)
            ]
            invalid.extend(
                [
                    (
                        "wrong-twelfth",
                        SOURCE.replace("putchar(205);", "putchar(204);"),
                    ),
                    ("wrong-second", SOURCE.replace("putchar(55);", "putchar(54);")),
                    (
                        "duplicate-eighth",
                        SOURCE.replace("putchar(152);", "putchar(159);"),
                    ),
                    (
                        "reordered-third",
                        SOURCE.replace(
                            "putchar(52); putchar(56);",
                            "putchar(56); putchar(52);",
                        ),
                    ),
                    ("arithmetic", SOURCE.replace("putchar(55);", "putchar(54 + 1);")),
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
