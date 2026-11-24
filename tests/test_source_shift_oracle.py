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
#   - Independent native C23 oracle for the repeated unsigned shift CFG.
# - Must-Not:
#   - Claim that the source-only checker or a native binary is a guest.
# - Allows:
#   - Inputs: finite binary streams with EOF and pinned Clang.
#   - Outputs: exact C23 -O0/-O2 UBSan output parity.
#   - Side effects: isolated temporary native executables only.
# - Split-When:
#   - A generalized typed-source cross-language oracle replaces this test.
# - Merge-When:
#   - Full source-locked guest loop acceptance includes all these streams.
# - Summary:
#   - Verify original C shift semantics, independently of Rust source replay.

"""Independent C23 reference for source-locked unsigned shift-loop checks."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess  # ruff: ignore[suspicious-subprocess-import]
import tempfile
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[1]
CLANG: Final = ROOT / ".dependencies/llvm/22.1.8/bin/clang"
LLVM_LIB: Final = ROOT / ".dependencies/llvm/22.1.8/lib"
SOURCE: Final = r"""
#include <stdio.h>
#include <limits.h>
static_assert(UINT_MAX == 0xffffffffu);
int main(void) {
    for (;;) {
        int current = getchar();
        if (current == EOF) return 0;
        unsigned value = (unsigned)current;
        unsigned masked = (value >> 3u) << 3u;
        if (putchar((int)(masked & 255u)) == EOF) return 1;
    }
}
"""
VECTORS: Final = (
    ("empty", b""),
    ("nul", b"\x00"),
    ("high", b"\x80"),
    ("max", b"\xff"),
    ("loop", b"\x00\x80\xff"),
    ("all-bytes", bytes(range(256))),
)


def test_all_bytes_and_eof_with_native_optimizations() -> None:
    """Exact binary stdout; Clang UBSan must not report undefined shifts."""
    with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
        scratch = Path(directory)
        source = scratch / "source.c"
        _ = source.write_text(SOURCE, encoding="utf-8")
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            part
            for part in (str(LLVM_LIB), env.get("LD_LIBRARY_PATH", ""))
            if part
        )
        for optimization in ("-O0", "-O2"):
            binary = scratch / f"native-{optimization[2:]}"
            compiler = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
                [
                    str(CLANG),
                    "-std=c23",
                    optimization,
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-fsanitize=undefined",
                    "-fno-sanitize-recover=all",
                    str(source),
                    "-o",
                    str(binary),
                ],
                env=env,
                capture_output=True,
                check=False,
                timeout=40,
            )
            assert compiler.returncode == 0, compiler.stderr
            for name, input_stream in VECTORS:
                native = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
                    [str(binary)],
                    input=input_stream,
                    capture_output=True,
                    check=False,
                    timeout=10,
                )
                assert native.returncode == 0, (
                    optimization,
                    name,
                    native.stderr,
                )
                # Mathematically independent low-bit mask oracle.
                expected = bytes(value & 0xF8 for value in input_stream)
                assert native.stdout == expected, (optimization, name)
