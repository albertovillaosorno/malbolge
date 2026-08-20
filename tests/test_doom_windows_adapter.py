# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Native execution of the focused DOOM Windows adapter boundary harness.
# - Must-Not:
#   - Launch the game or depend on an external DOOM source tree.
# - Allows:
#   - Inputs: tracked harness plus pinned repository Clang and Windows SDK libs.
#   - Outputs: one passing or failing pytest result.
#   - Side effects: compilation and execution only inside pytest temporary
#     state.
# - Split-When:
#   - Split when native adapter harness families gain separate toolchains.
# - Merge-When:
#   - Merge when another test owns this exact Windows adapter harness lifecycle.
# - Summary:
#   - Compiles and runs focused DOOM Windows adapter regression evidence.
# - Description:
#   - Uses pinned Clang, verifies Windows SDK ABI facts, and avoids shell use.
# - Usage:
#   - Collected by the repository Python test suite on Windows.
# - Defaults:
#   - Skips on non-Windows hosts where the adapter is not available.
#

"""Compile and run focused DOOM Windows host adapter boundary regressions."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/bin/clang.exe"
ADAPTER = (
    ROOT / "src/interface/command-line/adapter-outbound/adapters/doom/windows.c"
)
HARNESS = ROOT / "tests/doom_windows_adapter.c"
WINDOWS_OS_NAME = "nt"
WINDOWS_ABI_TARGETS = (
    "x86_64-pc-windows-msvc",
    "aarch64-pc-windows-msvc",
)
STRICT_WARNINGS = (
    "-Wall",
    "-Wextra",
    "-Wpedantic",
    "-Wconversion",
    "-Wsign-conversion",
    "-Wshadow",
    "-Wformat=2",
    "-Wundef",
    "-Wcast-qual",
    "-Wcast-align",
    "-Wswitch-enum",
    "-Wswitch-default",
    "-Wvla",
    "-Wimplicit-fallthrough",
    "-Wstrict-prototypes",
    "-Wmissing-prototypes",
    "-Wmissing-variable-declarations",
    "-Wnull-dereference",
    "-Werror",
)
SDK_ABI_PROBE = r"""
#include <stddef.h>
#include <windows.h>
#include <mmsystem.h>

_Static_assert(sizeof(MSG) == 48, "MSG size");
_Static_assert(offsetof(MSG, wParam) == 16, "MSG wParam");
_Static_assert(offsetof(MSG, lParam) == 24, "MSG lParam");
_Static_assert(offsetof(MSG, pt) == 36, "MSG point");
_Static_assert(sizeof(BITMAPINFOHEADER) == 40, "bitmap header");
_Static_assert(offsetof(BITMAPINFO, bmiColors) == 40, "bitmap palette");
_Static_assert(sizeof(WAVEFORMATEX) == 18, "wave format");
_Static_assert(offsetof(WAVEFORMATEX, cbSize) == 16, "wave cbSize");
_Static_assert(sizeof(WAVEHDR) == 48, "wave header");
_Static_assert(offsetof(WAVEHDR, lpNext) == 32, "wave next");
_Static_assert(sizeof(WNDCLASSEXA) == 80, "window class");
_Static_assert(offsetof(WNDCLASSEXA, lpszClassName) == 64, "class name");
_Static_assert(sizeof(PAINTSTRUCT) == 72, "paint struct");
_Static_assert(MEM_COMMIT == 0x1000, "MEM_COMMIT");
_Static_assert(MEM_RESERVE == 0x2000, "MEM_RESERVE");
_Static_assert(MEM_RELEASE == 0x8000, "MEM_RELEASE");
_Static_assert(PAGE_READWRITE == 0x04, "PAGE_READWRITE");
_Static_assert(WS_OVERLAPPEDWINDOW == 0x00CF0000L, "window style");
_Static_assert(WS_POPUP == 0x80000000L, "popup style");
_Static_assert(WM_CAPTURECHANGED == 0x0215, "capture changed");
_Static_assert(WAVE_FORMAT_PCM == 1, "PCM format");
_Static_assert(WAVE_MAPPER == (UINT)-1, "wave mapper");
_Static_assert(WHDR_DONE == 1, "wave done");
"""


@pytest.mark.skipif(os.name != WINDOWS_OS_NAME, reason="Windows adapter only")
def test_doom_windows_adapter_boundaries(tmp_path: Path) -> None:
    """Compile and execute focused Windows host-boundary regressions."""
    for target in WINDOWS_ABI_TARGETS:
        # jig-ignore-next-line: indivisible Ruff suppression on fixed argv.
        sdk_probe = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            (
                str(CLANG),
                f"--target={target}",
                "-std=c23",
                "-Wall",
                "-Wextra",
                "-Wpedantic",
                "-Werror",
                "-fsyntax-only",
                "-x",
                "c",
                "-",
            ),
            cwd=ROOT,
            check=False,
            capture_output=True,
            input=SDK_ABI_PROBE,
            text=True,
            shell=False,
        )
        assert sdk_probe.returncode == 0, sdk_probe.stdout + sdk_probe.stderr

        # jig-ignore-next-line: indivisible Ruff suppression on fixed argv.
        adapter_compile = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            (
                str(CLANG),
                f"--target={target}",
                "-std=c23",
                *STRICT_WARNINGS,
                "-fsyntax-only",
                str(ADAPTER),
            ),
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            shell=False,
        )
        assert adapter_compile.returncode == 0, (
            adapter_compile.stdout + adapter_compile.stderr
        )

    executable = tmp_path / "doom-windows-adapter-test.exe"
    command = (
        str(CLANG),
        "--target=x86_64-pc-windows-msvc",
        "-std=c23",
        *STRICT_WARNINGS,
        "-Wno-unused-function",
        "-ffunction-sections",
        "-fdata-sections",
        "-fuse-ld=lld",
        "-Wl,/OPT:REF",
        str(HARNESS),
        "-o",
        str(executable),
        "-luser32",
        "-lgdi32",
        "-lwinmm",
        "-lkernel32",
    )
    compiled = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        shell=False,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    executed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        (str(executable),),
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        shell=False,
    )
    assert executed.returncode == 0, executed.stdout + executed.stderr
