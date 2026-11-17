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
#   - Source-C signed EOF-to-unsigned-char output parity at guest publication.
# - Must-Not:
#   - Admit byte-only EOF surrogates or pass on a compiler timeout.
# - Allows:
#   - Inputs: one frozen C23 read/write program and four finite byte streams.
#   - Outputs: independent Clang/guest parity or typed unsupported refusal.
#   - Side effects: bounded subprocesses and isolated temporary artifacts.
# - Split-When:
#   - Source-C EOF-dependent output becomes generally executable.
# - Merge-When:
#   - The P2 EOF-checksum gate proves this full conversion path.
# - Summary:
#   - EOF must not accidentally become the Malbolge profile's low byte.

"""A real guest may implement C putchar(getchar()) or refuse it, never lie."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Final, final

ROOT: Final = Path(__file__).resolve().parents[1]
DRIVER: Final = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
CLANG: Final = ROOT / ".dependencies/llvm/22.1.8/bin/clang"
FRONTEND: Final = (
    ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
)
ADAPTER: Final = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT: Final = ROOT / ".cache/rust/target/debug/malbolge_layout"
VM: Final = ROOT / ".cache/rust/target/debug/malbolge"
SOURCE: Final = "#include <stdio.h>\nvoid emit(void) { putchar(getchar()); }\n"
VECTORS: Final = (
    ("eof", b"", b"\xff"),
    ("nul", b"\x00", b"\x00"),
    ("ascii", b"A", b"A"),
    ("high-byte", b"\xff", b"\xff"),
)


@final
class GetcharEofPublicationTests(unittest.TestCase):
    def test_independent_native_eof_oracles(self) -> None:
        if not CLANG.is_file():
            self.skipTest("pinned Clang required")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as raw:
            directory = Path(raw)
            source = directory / "getchar.c"
            _ = source.write_text(SOURCE, encoding="utf-8")
            wrapper = directory / "main.c"
            _ = wrapper.write_text(
                '#include "getchar.c"\nint main(void) { emit(); return 0; }\n',
                encoding="utf-8",
            )
            env = os.environ.copy()
            llvm_lib = str(ROOT / ".dependencies/llvm/22.1.8/lib")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                part for part in (llvm_lib, env.get("LD_LIBRARY_PATH", "")) if part
            )
            for optimization in ("-O0", "-O2"):
                native = directory / f"native-{optimization[2:]}"
                built = subprocess.run(
                    [
                        str(CLANG),
                        "-std=c23",
                        optimization,
                        "-Wall",
                        "-Wextra",
                        "-Werror",
                        str(wrapper),
                        "-o",
                        str(native),
                    ],
                    env=env,
                    capture_output=True,
                    check=False,
                    timeout=10,
                )
                self.assertEqual(built.returncode, 0, built.stderr)
                for label, data, expected in VECTORS:
                    with self.subTest(optimization=optimization, input=label):
                        run = subprocess.run(
                            [str(native)],
                            input=data,
                            capture_output=True,
                            check=False,
                            timeout=10,
                        )
                        self.assertEqual(run.returncode, 0, run.stderr)
                        self.assertEqual(run.stdout, expected)

    def test_discarded_signed_getchar_executes_on_real_guest(self) -> None:
        """An unused C i32 getchar must consume input and handle EOF."""
        if not all(
            binary.is_file() for binary in (CLANG, FRONTEND, ADAPTER, LAYOUT, VM)
        ):
            self.skipTest("pinned source compiler and guest VM required")
        for count in (1, 2):
            with (
                self.subTest(reads=count),
                tempfile.TemporaryDirectory(dir=ROOT / ".temp") as raw,
            ):
                directory = Path(raw)
                source = directory / "discarded.c"
                _ = source.write_text(
                    "#include <stdio.h>\nvoid emit(void) { "
                    + "getchar(); " * count
                    + "}\n",
                    encoding="utf-8",
                )
                target = directory / "discarded.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--capsule",
                        "--max-wall-seconds",
                        "40",
                        "--output",
                        str(target),
                        str(source),
                    ],
                    capture_output=True,
                    check=False,
                    timeout=45,
                )
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                self.assertTrue(target.is_file())
                for data in (b"", b"\xff", b"\x00\x80"):
                    with self.subTest(input=data):
                        guest = subprocess.run(
                            [
                                str(VM),
                                str(target),
                                "--input-stdin",
                                "--report-steps",
                                "--max-steps",
                                "1000",
                            ],
                            input=data,
                            capture_output=True,
                            check=False,
                            timeout=15,
                        )
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        self.assertEqual(guest.stdout, b"")
                        self.assertIn(
                            f"malbolge-steps-v1:{count + 1}".encode(), guest.stderr
                        )

    def test_parenthesized_and_discard_prefix_eof_not_miscompiled(self) -> None:
        """Equivalent unguarded signed reads cannot publish EOF surrogates."""
        if not all(
            binary.is_file() for binary in (CLANG, FRONTEND, ADAPTER, LAYOUT, VM)
        ):
            self.skipTest("pinned frontend and real guest VM required")
        variants = (
            ("parenthesized", "putchar((getchar()));"),
            ("double-parenthesized", "putchar(((getchar())));"),
            ("discard-prefix", "getchar(); putchar(getchar());"),
            (
                "double-discard-prefix",
                "getchar(); getchar(); putchar(((getchar())));",
            ),
        )
        vectors = (b"", b"\x00", b"\xff", b"\x00\x80", b"\xff\x00\x7f")
        env = os.environ.copy()
        llvm_lib = str(ROOT / ".dependencies/llvm/22.1.8/lib")
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            part for part in (llvm_lib, env.get("LD_LIBRARY_PATH", "")) if part
        )
        for name, statement in variants:
            with (
                self.subTest(shape=name),
                tempfile.TemporaryDirectory(dir=ROOT / ".temp") as raw,
            ):
                directory = Path(raw)
                source = directory / "getchar.c"
                _ = source.write_text(
                    f"#include <stdio.h>\nvoid emit(void) {{ {statement} }}\n",
                    encoding="utf-8",
                )
                wrapper = directory / "main.c"
                _ = wrapper.write_text(
                    '#include "getchar.c"\nint main(void) { emit(); return 0; }\n',
                    encoding="utf-8",
                )
                oracles: list[list[bytes]] = []
                for optimization in ("-O0", "-O2"):
                    binary = directory / f"native-{optimization[2:]}"
                    built = subprocess.run(
                        [
                            str(CLANG),
                            "-std=c23",
                            optimization,
                            "-Wall",
                            "-Wextra",
                            "-Werror",
                            str(wrapper),
                            "-o",
                            str(binary),
                        ],
                        env=env,
                        capture_output=True,
                        check=False,
                        timeout=15,
                    )
                    self.assertEqual(built.returncode, 0, built.stderr)
                    outputs: list[bytes] = []
                    for data in vectors:
                        native = subprocess.run(
                            [str(binary)],
                            input=data,
                            capture_output=True,
                            check=False,
                            timeout=10,
                        )
                        self.assertEqual(native.returncode, 0, native.stderr)
                        outputs.append(native.stdout)
                    oracles.append(outputs)
                self.assertEqual(oracles[0], oracles[1])
                self.assertEqual(oracles[0][0], b"\xff")

                target = directory / "getchar.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--capsule",
                        "--max-wall-seconds",
                        "70",
                        "--output",
                        str(target),
                        str(source),
                    ],
                    capture_output=True,
                    check=False,
                    timeout=75,
                )
                if compiled.returncode != 0:
                    self.assertIn(
                        b"normalized frontend rejected: Unsupported",
                        compiled.stderr,
                    )
                    self.assertFalse(target.exists())
                    continue
                self.assertTrue(target.is_file())
                for data, expected in zip(vectors, oracles[0], strict=True):
                    guest = subprocess.run(
                        [
                            str(VM),
                            str(target),
                            "--input-stdin",
                            "--max-steps",
                            "1000",
                        ],
                        input=data,
                        capture_output=True,
                        check=False,
                        timeout=15,
                    )
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(guest.stdout, expected)

    # Safe refusal is mandatory until guest output can convert signed EOF.
    def test_source_c_eof_conversion_executes_correctly_or_refuses(
        self,
    ) -> None:
        """A direct getchar output must be correct at EOF or refuse."""
        if not all(
            binary.is_file() for binary in (CLANG, FRONTEND, ADAPTER, LAYOUT, VM)
        ):
            self.skipTest("pinned Clang and real compiler/VM binaries required")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as raw:
            directory = Path(raw)
            source = directory / "getchar.c"
            _ = source.write_text(SOURCE, encoding="utf-8")
            target = directory / "getchar.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--capsule",
                    "--max-wall-seconds",
                    "70",
                    "--output",
                    str(target),
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=75,
            )
            if compiled.returncode != 0:
                # Unsupported is safe; a timeout, crash, or stray guest file
                # is not a proof that the compiler rejected this operation.
                self.assertIn(
                    b"normalized frontend rejected: Unsupported",
                    compiled.stderr,
                )
                self.assertFalse(target.exists())
                return
            self.assertTrue(target.is_file(), "compiler claimed an absent guest")
            for label, data, expected in VECTORS:
                with self.subTest(guest_input=label):
                    guest = subprocess.run(
                        [
                            str(VM),
                            str(target),
                            "--input-stdin",
                            "--report-steps",
                            "--max-steps",
                            "1000",
                        ],
                        input=data,
                        capture_output=True,
                        check=False,
                        timeout=15,
                    )
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(guest.stdout, expected)
                    self.assertIn(b"malbolge-steps-v1:", guest.stderr)


if __name__ == "__main__":
    _ = unittest.main()
