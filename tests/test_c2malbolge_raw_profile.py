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
#   - Real C compilation to unframed current-profile guest VM execution.
# - Must-Not:
#   - Substitute a host C run or infer raw profile identity from source bytes.
# - Allows:
#   - Inputs: pinned Clang, verified compiler stages, raw and capsule modes.
#   - Outputs: exact guest bytes and normative VM step receipts.
#   - Side effects: temporary project-local compiled C and guest files only.
# - Split-When:
#   - A general C runtime subsumes the bounded witnessed byte pairs.
# - Merge-When:
#   - One integration suite covers raw-profile public VM handoff.
# - Summary:
#   - C-to-raw and C-to-capsule builds execute the same guest effects.
# - Description:
#   - Verifies compiled raw output under explicit profile selection, not C.
# - Usage:
#   - MALBOLGE_RAW_PROFILE_BIN_ROOT=/path/to/debug python3.14 -B -m unittest
#     tests.test_c2malbolge_raw_profile -v
# - Defaults:
#   - Skip only when the pinned native toolchain is unavailable.

"""Source C -> verified raw Malbolge -> explicitly selected public guest VM."""

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
        "MALBOLGE_RAW_PROFILE_BIN_ROOT", str(ROOT / ".cache/rust/target/debug")
    )
)
ADAPTER = BIN_ROOT / "c2malbolge_json"
LAYOUT = BIN_ROOT / "malbolge_layout"
VM = BIN_ROOT / "malbolge"
EXAMPLE_Q = ROOT / "src/interface/command-line/composition/examples/emit-qp.c"
EXAMPLE_ZPH = ROOT / "src/interface/command-line/composition/examples/emit-zph.c"
EXAMPLE_T4 = ROOT / "src/interface/command-line/composition/examples/emit-t4.c"


@final
class RawProfileNativePipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        tools = (FRONTEND, ADAPTER, LAYOUT, VM)
        if (
            not GUEST_INCLUDE.is_dir()
            or not RESOURCE.is_dir()
            or any(not item.is_file() or not os.access(item, os.X_OK) for item in tools)
        ):
            if "MALBOLGE_RAW_PROFILE_BIN_ROOT" in os.environ:
                self.fail("explicit pinned frontend, layout or VM tools unavailable")
            self.skipTest("pinned Clang and compiled compiler/VM binaries required")

    def compile_c(
        self, source: Path, output: Path, *, capsule: bool
    ) -> subprocess.CompletedProcess[bytes]:
        command = [
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
            f"fixtures/{source.name}",
            "--output",
            str(output),
        ]
        if capsule:
            command.append("--capsule")
        command.append(str(source))
        return subprocess.run(command, capture_output=True, check=False, timeout=150)

    def run_guest(
        self, output: Path, *, raw: bool
    ) -> subprocess.CompletedProcess[bytes]:
        command = [str(VM), str(output), "--report-steps"]
        if raw:
            command.extend(["--raw-profile", "malbolge-2026"])
        return subprocess.run(command, capture_output=True, check=False, timeout=60)

    def test_source_bound_raw_matches_capsule_under_normative_vm(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory_name:
            directory = Path(directory_name)
            for name, source_text, expected, steps in (
                ("zero-z", "putchar(0); putchar('Z');", b"\x00Z", 5),
                ("checked-in-qp", None, b"Q.", 8),
                ("checked-in-zph", None, b"Z%H", 8),
                (
                    "q-period-o",
                    "putchar('Q'); putchar('.'); putchar('O');",
                    b"Q.O",
                    9,
                ),
                (
                    "y-hyphen-p",
                    "putchar('Y'); putchar('-'); putchar('P');",
                    b"Y-P",
                    10,
                ),
                (
                    "t-quote-o",
                    "putchar('T'); putchar(34); putchar('O');",
                    b'T"O',
                    12,
                ),
                (
                    "t-quote-q",
                    "putchar('T'); putchar(34); putchar('Q');",
                    b'T"Q',
                    14,
                ),
            ):
                with self.subTest(name=name):
                    source = directory / f"{name}.c"
                    if name == "checked-in-zph":
                        source = EXAMPLE_ZPH
                    elif source_text is None:
                        source = EXAMPLE_Q
                    else:
                        _ = source.write_text(
                            "#include <stdio.h>\nvoid emit(void) { "
                            + source_text
                            + " }\n",
                            encoding="ascii",
                        )
                    outputs: list[subprocess.CompletedProcess[bytes]] = []
                    for capsule in (False, True):
                        mode = "capsule" if capsule else "raw"
                        guest_file = directory / f"{name}-{mode}.malbolge"
                        built = self.compile_c(source, guest_file, capsule=capsule)
                        self.assertEqual(built.returncode, 0, built.stderr)
                        self.assertTrue(guest_file.is_file())
                        if not capsule:
                            self.assertTrue(
                                all(
                                    33 <= byte <= 126
                                    for byte in guest_file.read_bytes()
                                )
                            )
                        executed = self.run_guest(guest_file, raw=not capsule)
                        self.assertEqual(executed.returncode, 0, executed.stderr)
                        self.assertEqual(executed.stdout, expected)
                        self.assertEqual(
                            executed.stderr,
                            f"malbolge-steps-v1:{steps}\n".encode("ascii"),
                        )
                        outputs.append(executed)
                    self.assertEqual(outputs[0].stdout, outputs[1].stdout)
                    self.assertEqual(outputs[0].stderr, outputs[1].stderr)

    def test_four_distinct_guest_bytes_raw_match_capsule(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory_name:
            directory = Path(directory_name)
            outputs: list[subprocess.CompletedProcess[bytes]] = []
            for capsule in (False, True):
                mode = "capsule" if capsule else "raw"
                guest_file = directory / f"four-distinct-{mode}.malbolge"
                built = self.compile_c(EXAMPLE_T4, guest_file, capsule=capsule)
                self.assertEqual(built.returncode, 0, built.stderr)
                self.assertTrue(guest_file.is_file())
                if not capsule:
                    self.assertTrue(
                        all(33 <= byte <= 126 for byte in guest_file.read_bytes())
                    )
                executed = self.run_guest(guest_file, raw=not capsule)
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, b"T=4>")
                self.assertEqual(executed.stderr, b"malbolge-steps-v1:21\n")
                outputs.append(executed)
            self.assertEqual(outputs[0].stdout, outputs[1].stdout)
            self.assertEqual(outputs[0].stderr, outputs[1].stderr)


if __name__ == "__main__":
    _ = unittest.main()
