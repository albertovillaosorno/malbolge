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
#   - End-to-end C23 second-signed-input echo and real guest EOF parity.
# - Must-Not:
#   - Infer a guest result from native stdout or accept a forged Clang AST.
# - Allows:
#   - Inputs: one frozen source, pinned frontend, and binary byte/EOF streams.
#   - Outputs: independent native/VM parity and no-artifact refusal.
#   - Side effects: bounded child compilers and temporary guest artifacts.
# - Split-When:
#   - A general dynamic C23 CFG compiler proves the same runtime behavior.
# - Merge-When:
#   - The existing two-read guest release tests cover parameterized output.
# - Summary:
#   - Guest must really echo the second read before its EOF-selected marker.

"""Source-locked C23 two-read, three-output real-Malbolge acceptance."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Final, final

ROOT: Final = Path(__file__).resolve().parents[1]
SOURCE: Final = ROOT / "tests/compiler/c-frontend/accepted/second_echo_eof_branch.c"
GOLDEN: Final = (
    ROOT / "tests/compiler/c-frontend/golden/second_echo_eof_branch_current.json"
)
SHA256: Final = "38b68cab604142ec1f08ec9972b2a585b42f02f671840044f982f079cf10d738"
FRONTEND: Final = (
    ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
)
CLANG: Final = ROOT / ".dependencies/llvm/22.1.8/bin/clang"
ADAPTER: Final = ROOT / ".cache/rust/target/debug/c2malbolge_json"
DRIVER: Final = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
VM: Final = ROOT / ".cache/rust/target/debug/malbolge"
VECTORS: Final = (
    ("empty", b""),
    ("first-null", b"\x00"),
    ("first-high", b"\xff"),
    ("second-nul", b"\x81\x00"),
    ("second-31", b"\x00\x1f"),
    ("second-255", b"\x03\xff"),
    ("high-first", b"\xff\x80"),
    ("trailing-unread", b"\x11\x55\xa7"),
    ("truncated", b"\x00"),
)


def expected_output(stream: bytes) -> bytes:
    first = stream[0] if stream else 106
    second = stream[1] if len(stream) > 1 else 106
    return bytes((first, second, 30 if len(stream) < 2 else 154))


def environment() -> dict[str, str]:
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = os.pathsep.join(
        part
        for part in (
            str(ROOT / ".dependencies/llvm/22.1.8/lib"),
            env.get("LD_LIBRARY_PATH", ""),
        )
        if part
    )
    return env


@final
class SecondEchoEofBranchPublicationTests(unittest.TestCase):
    def test_native_c23_and_normative_guest_binary_parity(self) -> None:
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(), SHA256)
        normalized = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(ROOT / "src/runtime/guest-c-library/contract/include"),
                "--resource-dir",
                str(ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"),
                "--source-id",
                SOURCE.name,
                str(SOURCE),
            ],
            env=environment(),
            capture_output=True,
            check=False,
            timeout=20,
        )
        self.assertEqual(normalized.returncode, 0, normalized.stderr)
        self.assertEqual(json.loads(normalized.stdout), json.loads(GOLDEN.read_bytes()))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            tmp = Path(directory)
            wrapper = tmp / "main.c"
            wrapper.write_text(
                f'#include "{SOURCE}"\nint main(void) {{ emit(); return 0; }}\n',
                encoding="utf-8",
            )
            for optimization in ("-O0", "-O2"):
                executable = tmp / f"native-{optimization[2:]}"
                built = subprocess.run(
                    [
                        str(CLANG),
                        "-std=c23",
                        optimization,
                        "-Wall",
                        "-Wextra",
                        "-Werror",
                        "-fsanitize=undefined",
                        "-fno-sanitize-recover=all",
                        str(wrapper),
                        "-o",
                        str(executable),
                    ],
                    env=environment(),
                    capture_output=True,
                    check=False,
                    timeout=20,
                )
                self.assertEqual(built.returncode, 0, built.stderr)
                for label, stream in VECTORS:
                    with self.subTest(native=optimization, input=label):
                        control = subprocess.run(
                            [str(executable)],
                            input=stream,
                            capture_output=True,
                            check=False,
                            timeout=10,
                        )
                        self.assertEqual(control.returncode, 0, control.stderr)
                        self.assertEqual(control.stdout, expected_output(stream))

            target = tmp / "second-echo.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--capsule",
                    "--max-wall-seconds",
                    "100",
                    "--output",
                    str(target),
                    str(SOURCE),
                ],
                env=environment(),
                capture_output=True,
                check=False,
                timeout=115,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(target.is_file())
            # Frozen binary/EOF boundary vectors keep external VM startup
            # costs finite; source compilation independently admits fourteen
            # additional physical path witnesses in its typed backend.
            for label, stream in VECTORS:
                with self.subTest(guest=label):
                    executed = subprocess.run(
                        [
                            str(VM),
                            str(target),
                            "--input-stdin",
                            "--max-steps",
                            "500",
                            "--report-steps",
                        ],
                        input=stream,
                        capture_output=True,
                        check=False,
                        timeout=10,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, expected_output(stream))
                    steps = 119 if len(stream) < 2 else 175
                    self.assertIn(
                        f"malbolge-steps-v1:{steps}".encode(), executed.stderr
                    )

    def test_forged_second_echo_source_and_ast_refuse(self) -> None:
        original = json.loads(GOLDEN.read_bytes())
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            tmp = Path(directory)
            for name, edit in (
                ("wrong-second", (46, "reference", "first@904")),
                ("hidden-read", (42, "reference", "external:getchar")),
                ("changed-parent", (46, "parent", 26)),
            ):
                forged = json.loads(GOLDEN.read_bytes())
                node_index, attribute, value = edit
                forged["nodes"][node_index][attribute] = value
                output = tmp / f"{name}.malbolge"
                result = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(tmp / "missing-backend"),
                        "--output",
                        str(output),
                        "--source",
                        str(SOURCE),
                    ],
                    input=json.dumps(forged).encode(),
                    env=environment(),
                    capture_output=True,
                    check=False,
                    timeout=20,
                )
                with self.subTest(forgery=name):
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(output.exists())
            self.assertEqual(original["nodes"][46]["reference"], "second@972")
            changed = tmp / "changed.c"
            changed.write_bytes(
                SOURCE.read_bytes().replace(b"putchar(second);", b"putchar(first);")
            )
            result = subprocess.run(
                [
                    str(ADAPTER),
                    "--layout-backend",
                    str(tmp / "missing-backend"),
                    "--output",
                    str(tmp / "changed.malbolge"),
                    "--source",
                    str(changed),
                ],
                input=GOLDEN.read_bytes(),
                env=environment(),
                capture_output=True,
                check=False,
                timeout=20,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((tmp / "changed.malbolge").exists())


if __name__ == "__main__":
    unittest.main()
