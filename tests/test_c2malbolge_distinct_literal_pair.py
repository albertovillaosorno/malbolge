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
#   - Exact two distinct nonzero C bytes through the real guest VM pipeline.
# - Must-Not:
#   - Mock Clang, fabricate typed IR, or replace guest writes with host output.
# - Allows:
#   - Inputs: pinned Clang and isolated candidate compiler binaries.
#   - Outputs: stdout and exact steps from the independent Malbolge runner.
#   - Side effects: isolated project-local source and capsule fixtures only.
# - Split-When:
#   - Full arbitrary byte-pair synthesis supersedes the closed witnesses.
# - Merge-When:
#   - The public native compiler suite owns distinct guest byte transitions.
# - Summary:
#   - Real source C emits differing ASCII bytes through two guest crazy steps.
# - Description:
#   - Tests witnessed source calls plus fail-closed unsupported transitions.
# - Usage:
#   - MALBOLGE_DISTINCT_PAIR_BIN_ROOT=/path/to/debug python3 -m unittest
#     tests.test_c2malbolge_distinct_literal_pair -v
# - Defaults:
#   - No host-side substitution or publication on rejected source.

"""Pinned C -> canonical IR -> verified Malbolge -> real VM distinct bytes."""

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
RUST = Path(
    os.environ.get(
        "MALBOLGE_DISTINCT_PAIR_BIN_ROOT", str(ROOT / ".cache/rust/target/debug")
    )
)
ADAPTER = RUST / "c2malbolge_json"
LAYOUT = RUST / "malbolge_layout"
VM = RUST / "malbolge"


@final
class DistinctLiteralPairNativeTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        tools = (FRONTEND, ADAPTER, LAYOUT, VM)
        if (
            not GUEST_INCLUDE.is_dir()
            or not RESOURCE.is_dir()
            or any(not item.is_file() or not os.access(item, os.X_OK) for item in tools)
        ):
            if "MALBOLGE_DISTINCT_PAIR_BIN_ROOT" in os.environ:
                self.fail("explicit compiler or guest tools unavailable")
            self.skipTest("pinned Clang and compiled guest tools are required")

    def compile_source(
        self, directory: Path, name: str, statements: str
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
                "--capsule",
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=150,
        )
        return result, guest

    def test_real_c_distinct_printable_bytes_from_guest_arithmetic(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory_name:
            directory = Path(directory_name)
            for name, text, expected, steps in (
                ("y-slash", "putchar('Y'); putchar('/');", b"Y/", 6),
                ("y-dollar", "putchar(89); putchar(0x24);", b"Y$", 7),
                ("q-period", "putchar('Q'); putchar('.');", b"Q.", 8),
            ):
                with self.subTest(name=name):
                    result, artifact = self.compile_source(directory, name, text)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertTrue(artifact.is_file())
                    guest = subprocess.run(
                        [str(VM), str(artifact), "--report-steps"],
                        capture_output=True,
                        check=False,
                        timeout=60,
                    )
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(guest.stdout, expected)
                    self.assertEqual(
                        guest.stderr, f"malbolge-steps-v1:{steps}\n".encode()
                    )

    def test_unproved_pairs_never_publish_guest_artifacts(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory_name:
            directory = Path(directory_name)
            for name, source in (
                ("other-second", "putchar('Q'); putchar('Z');"),
                ("wrong-transition", "putchar('Y'); putchar('.');"),
                ("three-distinct", "putchar('Y'); putchar('/'); putchar('$');"),
                ("arithmetic", "putchar('Q'); putchar('.' + 0);"),
            ):
                with self.subTest(name=name):
                    result, artifact = self.compile_source(directory, name, source)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(artifact.exists())


if __name__ == "__main__":
    _ = unittest.main()
