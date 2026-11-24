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
#   - Independent native C23 shift/EOF and undefined arithmetic controls.
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
#   - Verify C shifts and executed undefined arithmetic independently.

"""Independent C23 reference for source-locked shift and EOF-loop checks."""

from __future__ import annotations

import os
import subprocess  # ruff: ignore[suspicious-subprocess-import]
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable

ROOT: Final = Path(__file__).resolve().parents[1]
CLANG: Final = ROOT / ".dependencies/llvm/22.1.8/bin/clang"
LLVM_LIB: Final = ROOT / ".dependencies/llvm/22.1.8/lib"
UNSIGNED_SOURCE: Final = r"""
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
SIGNED_SOURCE: Final = r"""
#include <stdio.h>
#include <limits.h>
static_assert(INT_MAX == 2147483647);
int main(void) {
    for (;;) {
        int current = getchar();
        if (current == EOF) return 0;
        int shifted = (current << 4) >> 3;
        if (putchar(shifted & 255) == EOF) return 1;
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


def _assert_native_oracle(
    source_text: str, expected_bytes: Callable[[bytes], bytes]
) -> None:
    """Compare independent C23 UBSan runs to a finite byte-stream oracle."""
    with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
        scratch = Path(directory)
        source = scratch / "source.c"
        _ = source.write_text(source_text, encoding="utf-8")
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            part for part in (str(LLVM_LIB), env.get("LD_LIBRARY_PATH", "")) if part
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
                expected = expected_bytes(input_stream)
                assert native.stdout == expected, (optimization, name)


def test_all_bytes_and_eof_with_native_optimizations() -> None:
    """Unsigned shifts wrap; native C23 remains exact under -O0/-O2."""
    _assert_native_oracle(
        UNSIGNED_SOURCE,
        lambda stream: bytes(value & 0xF8 for value in stream),
    )


def test_defined_signed_shifts_with_native_optimizations() -> None:
    """Signed shifts of nonnegative bytes remain representable at C32."""
    _assert_native_oracle(
        SIGNED_SOURCE,
        lambda stream: bytes((value * 2) & 0xFF for value in stream),
    )


# The source checker must reject executed undefined C23 arithmetic even when
# a later byte output does not depend on the invalid result. Native UBSan
# witnesses independently check both optimization modes and the absence of
# stdout before the arithmetic trap.
UNDEFINED_RUNTIME_ERROR: Final = b"runtime error:"
UNDEFINED_EMPTY_OUTPUT: Final = b""
UNDEFINED_UNSIGNED_COUNT_SOURCE: Final = r"""
#include <stdio.h>
int main(void) {
    volatile unsigned count = 32u;
    unsigned shifted = 1u << count;
    return putchar((int)(shifted & 255u)) == EOF ? 2 : 0;
}
"""
UNDEFINED_SIGNED_OVERFLOW_SOURCE: Final = r"""
#include <stdio.h>
int main(void) {
    volatile int value = 255;
    int shifted = value << 24;
    return putchar(shifted & 255) == EOF ? 2 : 0;
}
"""


UNDEFINED_DEAD_SHIFT_SOURCE: Final = r"""
#include <stdio.h>
int main(void) {
    volatile unsigned value = 1u;
    volatile unsigned count = 32u;
    volatile unsigned ignored = value << count;
    (void)ignored;
    return putchar('A') == EOF ? 2 : 0;
}
"""
UNDEFINED_DEAD_ADD_SOURCE: Final = r"""
#include <stdio.h>
#include <limits.h>
int main(void) {
    volatile int value = INT_MAX;
    volatile int one = 1;
    volatile int ignored = value + one;
    (void)ignored;
    return putchar('A') == EOF ? 2 : 0;
}
"""
UNDEFINED_DEAD_DIVIDE_SOURCE: Final = r"""
#include <stdio.h>
int main(void) {
    volatile unsigned numerator = 3u;
    volatile unsigned divisor = 0u;
    volatile unsigned ignored = numerator / divisor;
    (void)ignored;
    return putchar('A') == EOF ? 2 : 0;
}
"""


UNDEFINED_SELECTED_BRANCH_SOURCE: Final = r"""
#include <stdio.h>
int main(void) {
    int current = getchar();
    if (current != 0) {
        volatile unsigned divisor = 0u;
        volatile unsigned ignored = (unsigned)current / divisor;
        (void)ignored;
    }
    return putchar('A') == EOF ? 2 : 0;
}
"""


def _assert_native_rejects_undefined_arithmetic(
    source_text: str,
    streams: tuple[tuple[bytes, bytes | None], ...] = ((b"", None),),
) -> None:
    """An executed undefined operation must trap before guest-like output."""
    with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
        scratch = Path(directory)
        source = scratch / "undefined.c"
        _ = source.write_text(source_text, encoding="utf-8")
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            part for part in (str(LLVM_LIB), env.get("LD_LIBRARY_PATH", "")) if part
        )
        for optimization in ("-O0", "-O2"):
            binary = scratch / f"undefined-{optimization[2:]}"
            compiled = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
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
            assert compiled.returncode == 0, compiled.stderr
            for input_stream, expected in streams:
                native = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
                    [str(binary)],
                    input=input_stream,
                    capture_output=True,
                    check=False,
                    timeout=10,
                )
                if expected is None:
                    assert native.returncode != 0, (optimization, input_stream)
                    assert UNDEFINED_RUNTIME_ERROR in native.stderr, (
                        optimization,
                        input_stream,
                        native.stderr,
                    )
                    assert native.stdout == UNDEFINED_EMPTY_OUTPUT, (
                        optimization,
                        input_stream,
                    )
                else:
                    assert native.returncode == 0, (optimization, input_stream)
                    assert native.stderr == b"", (optimization, input_stream)
                    assert native.stdout == expected, (optimization, input_stream)


def test_native_rejects_out_of_range_unsigned_shift() -> None:
    """The 32-bit unsigned count `32` cannot silently wrap to zero."""
    _assert_native_rejects_undefined_arithmetic(UNDEFINED_UNSIGNED_COUNT_SOURCE)


def test_native_rejects_signed_left_overflow() -> None:
    """A positive signed value with an unrepresentable shift is undefined."""
    _assert_native_rejects_undefined_arithmetic(UNDEFINED_SIGNED_OVERFLOW_SOURCE)


def test_native_rejects_dead_shift_before_output() -> None:
    """An unused invalid shift still prevents a defined C23 return."""
    _assert_native_rejects_undefined_arithmetic(UNDEFINED_DEAD_SHIFT_SOURCE)


def test_native_rejects_dead_signed_add_before_output() -> None:
    """Signed overflow is undefined even if its result is discarded."""
    _assert_native_rejects_undefined_arithmetic(UNDEFINED_DEAD_ADD_SOURCE)


def test_native_rejects_dead_divide_before_output() -> None:
    """Zero division is undefined even when the result is discarded."""
    _assert_native_rejects_undefined_arithmetic(UNDEFINED_DEAD_DIVIDE_SOURCE)


def test_native_selected_branch_only_traps_on_executed_division() -> None:
    """Only the taken invalid arithmetic arm prevents the C23 return."""
    _assert_native_rejects_undefined_arithmetic(
        UNDEFINED_SELECTED_BRANCH_SOURCE,
        (
            (b"\x00", b"A"),
            (b"\x01", None),
            (b"\xff", None),
            (b"", None),
        ),
    )
