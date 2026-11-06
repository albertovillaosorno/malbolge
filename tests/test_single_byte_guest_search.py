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
#   - Real guest validation of bounded source-derived single-byte search.
# - Must-Not:
#   - Treat candidate previews or host printing as guest output evidence.
# - Allows:
#   - Inputs: complete C sources with one output byte and pinned tools.
#   - Outputs: independently verified VM bytes or explicit layout refusal.
#   - Side effects: isolated temporary C and guest artifacts.
# - Split-When:
#   - General byte stream generation replaces the bounded candidate grammar.
# - Merge-When:
#   - Source-C parity matrix covers this byte-synthesis boundary.
# - Summary:
#   - Test a value omitted from finite precomputed guest witness tables.
# - Description:
#   - Verify both no-input and nonempty-input guest execution, not stdout shims.
# - Usage:
#   - python3.14 -B -m unittest tests.test_single_byte_guest_search -v
# - Defaults:
#   - Reject insufficiently witnessed output without publishing a guest.

"""Real compiler and VM acceptance for the bounded single-byte guest search."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
FRONTEND = (
    ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
)
ADAPTER = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT = ROOT / ".cache/rust/target/debug/malbolge_layout"
VM = ROOT / ".cache/rust/target/debug/malbolge"


class SingleByteGuestSearchTests(unittest.TestCase):
    def test_unseeded_byte_real_guest_output(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("repository-pinned compiler binaries are not built")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for byte, steps in ((64, 7),):
                with self.subTest(byte=byte):
                    source = Path(scratch) / f"byte-{byte}.c"
                    _written = source.write_text(
                        "#include <stdio.h>\n"
                        f"void emit(void) {{ putchar({byte}); }}\n"
                    )
                    guest = Path(scratch) / f"byte-{byte}.malbolge"
                    compiled = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            "--capsule",
                            "--source-id",
                            f"tests/single-byte-search-{byte}-v1",
                            "--output",
                            str(guest),
                            str(source),
                        ],
                        check=False,
                        capture_output=True,
                        timeout=90,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(guest.is_file())
                    for payload in (b"", bytes((0, 255, 128))):
                        replay = subprocess.run(
                            [
                                str(VM),
                                str(guest),
                                "--input-stdin",
                                "--report-steps",
                            ],
                            input=payload,
                            check=False,
                            capture_output=True,
                            timeout=30,
                        )
                        self.assertEqual(replay.returncode, 0, replay.stderr)
                        self.assertEqual(replay.stdout, bytes((byte,)))
                        self.assertEqual(
                            replay.stderr,
                            f"malbolge-steps-v1:{steps}\n".encode(),
                        )
