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
#   - Cross-target compilation and native execution of guest-runtime C vectors.
# - Must-Not:
#   - Call host allocation/stdio as guest-runtime semantic evidence.
# - Allows:
#   - Inputs: tracked runtime sources, harness, and pinned repository Clang.
#   - Outputs: one passing/failing pytest result across reviewed Windows ABIs.
#   - Side effects: temporary native executable creation under pytest state.
# - Split-When:
#   - Another runtime semantic family requires an independent toolchain matrix.
# - Merge-When:
#   - Another suite owns this exact guest-runtime conformance lifecycle.
# - Summary:
#   - Locks guest heap/byte semantics under strict cross-target C compilation.
# - Description:
#   - Three Windows ABIs prove source portability; x64 executes semantic
#     vectors.
# - Usage:
#   - Collected by the repository Python test suite on Windows.
# - Defaults:
#   - Other hosts skip because the pinned native Clang asset is Windows.
#

"""Compile and run pure-C guest-runtime semantic conformance vectors."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/bin/clang.exe"
LLVM_NM = ROOT / ".dependencies/llvm/22.1.8/bin/llvm-nm.exe"
SANITIZER_RUNTIME_DIR = (
    ROOT / ".dependencies/llvm/22.1.8/lib/clang/22/lib/windows"
)
RUNTIME_ROOT = ROOT / "src/runtime/guest-runtime"
INCLUDE = RUNTIME_ROOT / "contract"
HEAP_SOURCE = RUNTIME_ROOT / "domain/heap.c"
STREAM_SOURCE = RUNTIME_ROOT / "domain/byte_stream.c"
FRAME_SOURCE = RUNTIME_ROOT / "domain/frame.c"
STARTUP_SOURCE = RUNTIME_ROOT / "domain/startup.c"
FORMAT_SOURCE = RUNTIME_ROOT / "domain/format.c"
FORMAT_PARSE_SOURCE = RUNTIME_ROOT / "domain/format_parse.c"
VARARGS_SOURCE = RUNTIME_ROOT / "domain/varargs.c"
FORMAT_ARGS_SOURCE = RUNTIME_ROOT / "domain/format_args.c"
FORMAT_SCALAR_SOURCE = RUNTIME_ROOT / "domain/format_scalar.c"
FORMAT_MEMORY_SOURCE = RUNTIME_ROOT / "domain/format_memory.c"
FORMAT_FLOAT_SOURCE = RUNTIME_ROOT / "domain/format_float.c"
HARNESS = ROOT / "tests/runtime/guest_runtime_conformance.c"
FORMAT_HARNESS = ROOT / "tests/runtime/guest_format_conformance.c"
FORMAT_PARSE_HARNESS = ROOT / "tests/runtime/guest_format_parse_conformance.c"
VARARGS_HARNESS = ROOT / "tests/runtime/guest_varargs_conformance.c"
FORMAT_ARGS_HARNESS = ROOT / "tests/runtime/guest_format_args_conformance.c"
FORMAT_SCALAR_HARNESS = ROOT / "tests/runtime/guest_format_scalar_conformance.c"
FORMAT_MEMORY_HARNESS = ROOT / "tests/runtime/guest_format_memory_conformance.c"
FORMAT_FLOAT_HARNESS = ROOT / "tests/runtime/guest_format_float_conformance.c"
GUEST_LIBC_ROOT = ROOT / "src/runtime/guest-c-library"
GUEST_LIBC_INCLUDE = GUEST_LIBC_ROOT / "contract/include"
ALLOCATION_WRAPPERS = GUEST_LIBC_ROOT / "domain/allocation.c"
STDIO_WRAPPERS = GUEST_LIBC_ROOT / "domain/stdio.c"
STDIO_HARNESS = ROOT / "tests/runtime/guest_stdio_wrapper_conformance.c"
ALLOCATION_HARNESS = (
    ROOT / "tests/runtime/guest_allocation_wrapper_conformance.c"
)
WINDOWS_OS_NAME = "nt"
WINDOWS_ABI_TARGETS = (
    "i686-pc-windows-msvc",
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
RUNTIME_SOURCES = (
    HEAP_SOURCE,
    STREAM_SOURCE,
    FRAME_SOURCE,
    STARTUP_SOURCE,
    FORMAT_SOURCE,
    FORMAT_PARSE_SOURCE,
    VARARGS_SOURCE,
    FORMAT_ARGS_SOURCE,
    FORMAT_SCALAR_SOURCE,
    FORMAT_MEMORY_SOURCE,
    FORMAT_FLOAT_SOURCE,
)
SOURCES = (*RUNTIME_SOURCES, HARNESS)
EMPTY_SYMBOLS: frozenset[str] = frozenset()
EXPECTED_RUNTIME_UNDEFINED: dict[Path, frozenset[str]] = {
    HEAP_SOURCE: EMPTY_SYMBOLS,
    STREAM_SOURCE: EMPTY_SYMBOLS,
    FRAME_SOURCE: EMPTY_SYMBOLS,
    STARTUP_SOURCE: frozenset({
        "malbolge_guest_heap_allocate",
        "malbolge_guest_heap_allocate_zeroed",
        "malbolge_guest_heap_init",
        "malbolge_guest_heap_release",
        "malbolge_guest_heap_resize",
    }),
    FORMAT_SOURCE: EMPTY_SYMBOLS,
    FORMAT_PARSE_SOURCE: EMPTY_SYMBOLS,
    VARARGS_SOURCE: EMPTY_SYMBOLS,
    FORMAT_ARGS_SOURCE: frozenset({
        "malbolge_guest_format_argument_kind",
        "malbolge_guest_format_directive_validate",
        "malbolge_guest_varargs_read",
        "malbolge_guest_varargs_validate",
    }),
    FORMAT_SCALAR_SOURCE: frozenset({
        "malbolge_guest_format_argument_kind",
        "malbolge_guest_format_character",
        "malbolge_guest_format_signed_decimal",
        "malbolge_guest_format_unsigned",
    }),
    FORMAT_MEMORY_SOURCE: frozenset({
        "malbolge_guest_format_argument_kind",
        "malbolge_guest_format_bytes",
    }),
    FORMAT_FLOAT_SOURCE: frozenset({
        "malbolge_guest_format_argument_kind",
    }),
}
WASM_STACK_UNDEFINED = frozenset({"_stack_pointer"})
EXPECTED_WRAPPER_UNDEFINED = frozenset({
    "malbolge_guest_runtime_allocate",
    "malbolge_guest_runtime_allocate_zeroed",
    "malbolge_guest_runtime_release",
    "malbolge_guest_runtime_resize",
})
EXPECTED_STDIO_UNDEFINED = frozenset({
    "malbolge_guest_decode_input_word",
    "malbolge_guest_intrinsic_input_word",
    "malbolge_guest_intrinsic_output_byte",
    "malbolge_guest_output_byte",
})


def run_command(
    command: tuple[str, ...],
    cwd: Path,
    *,
    env: dict[str, str] | None = None,
) -> sp.CompletedProcess[str]:
    """Run one fixed Clang or harness command without a shell.

    Returns:
        The completed process containing status and captured diagnostics.

    """
    return sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        env=env,
        text=True,
        shell=False,
        timeout=30,
    )


def undefined_symbols(object_file: Path) -> frozenset[str]:
    """Return undefined symbol names from one relocatable object.

    Returns:
        The exact undefined-symbol name set reported by pinned llvm-nm.

    """
    completed = run_command((str(LLVM_NM), "-u", str(object_file)), ROOT)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    symbols = (
        line.split()[-1]
        for line in completed.stdout.splitlines()
        if line.split()
    )
    return frozenset(symbol.removeprefix("_") for symbol in symbols)


@pytest.mark.skipif(
    os.name != WINDOWS_OS_NAME,
    reason="pinned native C runtime harness uses Windows Clang",
)
def test_guest_runtime_c_conformance(tmp_path: Path) -> None:
    """Compile all reviewed ABIs and execute the native semantic vectors."""
    for target in WINDOWS_ABI_TARGETS:
        compiled = run_command(
            (
                str(CLANG),
                f"--target={target}",
                "-std=c23",
                *STRICT_WARNINGS,
                f"-I{INCLUDE}",
                "-fsyntax-only",
                *(str(source) for source in SOURCES),
            ),
            ROOT,
        )
        assert compiled.returncode == 0, compiled.stdout + compiled.stderr
        for source in RUNTIME_SOURCES:
            object_file = tmp_path / f"{source.stem}-{target}.o"
            object_build = run_command(
                (
                    str(CLANG),
                    f"--target={target}",
                    "-std=c23",
                    "-ffreestanding",
                    "-fno-builtin",
                    *STRICT_WARNINGS,
                    f"-I{INCLUDE}",
                    "-c",
                    str(source),
                    "-o",
                    str(object_file),
                ),
                ROOT,
            )
            assert object_build.returncode == 0, (
                object_build.stdout + object_build.stderr
            )
            assert (
                undefined_symbols(object_file)
                == EXPECTED_RUNTIME_UNDEFINED[source]
            )

    for source in RUNTIME_SOURCES:
        object_file = tmp_path / f"{source.stem}.o"
        compiled = run_command(
            (
                str(CLANG),
                "-std=c23",
                "-ffreestanding",
                *STRICT_WARNINGS,
                f"-I{INCLUDE}",
                "-c",
                str(source),
                "-o",
                str(object_file),
            ),
            ROOT,
        )
        assert compiled.returncode == 0, compiled.stdout + compiled.stderr
        assert (
            undefined_symbols(object_file) == EXPECTED_RUNTIME_UNDEFINED[source]
        )

    wrapper_syntax = run_command(
        (
            str(CLANG),
            "--target=wasm32-unknown-unknown",
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            *STRICT_WARNINGS,
            f"-I{GUEST_LIBC_INCLUDE}",
            f"-I{INCLUDE}",
            "-fsyntax-only",
            str(ALLOCATION_WRAPPERS),
        ),
        ROOT,
    )
    assert wrapper_syntax.returncode == 0, wrapper_syntax.stderr

    wrapper_object = tmp_path / "allocation-wrappers.o"
    compiled = run_command(
        (
            str(CLANG),
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            *STRICT_WARNINGS,
            f"-I{GUEST_LIBC_INCLUDE}",
            f"-I{INCLUDE}",
            "-c",
            str(ALLOCATION_WRAPPERS),
            "-o",
            str(wrapper_object),
        ),
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    assert undefined_symbols(wrapper_object) == EXPECTED_WRAPPER_UNDEFINED

    executable = tmp_path / "guest-runtime-conformance.exe"
    compiled = run_command(
        (
            str(CLANG),
            "-std=c23",
            *STRICT_WARNINGS,
            f"-I{INCLUDE}",
            *(str(source) for source in SOURCES),
            "-o",
            str(executable),
        ),
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    executed = run_command((str(executable),), tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr


@pytest.mark.skipif(
    os.name != WINDOWS_OS_NAME,
    reason="pinned native C runtime harness uses Windows Clang",
)
def test_guest_stdio_wrapper_conformance(tmp_path: Path) -> None:
    """Lock guest byte wrappers and their intrinsic-only dependencies."""
    for target in WINDOWS_ABI_TARGETS:
        compiled = run_command(
            (
                str(CLANG),
                f"--target={target}",
                "-std=c23",
                "-ffreestanding",
                "-fno-builtin",
                *STRICT_WARNINGS,
                f"-I{GUEST_LIBC_INCLUDE}",
                f"-I{INCLUDE}",
                "-fsyntax-only",
                str(STDIO_WRAPPERS),
                str(STDIO_HARNESS),
            ),
            ROOT,
        )
        assert compiled.returncode == 0, compiled.stdout + compiled.stderr

    production_object = tmp_path / "stdio-production.o"
    compiled = run_command(
        (
            str(CLANG),
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            *STRICT_WARNINGS,
            f"-I{GUEST_LIBC_INCLUDE}",
            f"-I{INCLUDE}",
            "-c",
            str(STDIO_WRAPPERS),
            "-o",
            str(production_object),
        ),
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    assert undefined_symbols(production_object) == EXPECTED_STDIO_UNDEFINED

    renamed_object = tmp_path / "stdio-test.o"
    compiled = run_command(
        (
            str(CLANG),
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            "-Dgetchar=malbolge_test_getchar",
            "-Dputchar=malbolge_test_putchar",
            *STRICT_WARNINGS,
            f"-I{GUEST_LIBC_INCLUDE}",
            f"-I{INCLUDE}",
            "-c",
            str(STDIO_WRAPPERS),
            "-o",
            str(renamed_object),
        ),
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr

    executable = tmp_path / "guest-stdio-wrapper.exe"
    linked = run_command(
        (
            str(CLANG),
            "-std=c23",
            "-fno-builtin",
            *STRICT_WARNINGS,
            f"-I{GUEST_LIBC_INCLUDE}",
            f"-I{INCLUDE}",
            str(STREAM_SOURCE),
            str(renamed_object),
            str(STDIO_HARNESS),
            "-o",
            str(executable),
        ),
        ROOT,
    )
    assert linked.returncode == 0, linked.stdout + linked.stderr
    executed = run_command((str(executable),), tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr


@pytest.mark.skipif(
    os.name != WINDOWS_OS_NAME,
    reason="pinned native formatting harness uses Windows Clang",
)
def test_guest_format_conformance(tmp_path: Path) -> None:
    """Lock typed formatting bytes/counts and self-contained objects."""
    for target in WINDOWS_ABI_TARGETS:
        compiled = run_command(
            (
                str(CLANG),
                f"--target={target}",
                "-std=c23",
                "-ffreestanding",
                "-fno-builtin",
                *STRICT_WARNINGS,
                f"-I{INCLUDE}",
                "-fsyntax-only",
                str(FORMAT_SOURCE),
                str(FORMAT_HARNESS),
            ),
            ROOT,
        )
        assert compiled.returncode == 0, compiled.stdout + compiled.stderr

    wasm_object = tmp_path / "format-wasm.o"
    wasm_compiled = run_command(
        (
            str(CLANG),
            "--target=wasm32-unknown-unknown",
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            *STRICT_WARNINGS,
            f"-I{INCLUDE}",
            "-c",
            str(FORMAT_SOURCE),
            "-o",
            str(wasm_object),
        ),
        ROOT,
    )
    assert wasm_compiled.returncode == 0, (
        wasm_compiled.stdout + wasm_compiled.stderr
    )
    assert undefined_symbols(wasm_object) == WASM_STACK_UNDEFINED

    executable = tmp_path / "guest-format.exe"
    linked = run_command(
        (
            str(CLANG),
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            *STRICT_WARNINGS,
            f"-I{INCLUDE}",
            str(FORMAT_SOURCE),
            str(FORMAT_HARNESS),
            "-o",
            str(executable),
        ),
        ROOT,
    )
    assert linked.returncode == 0, linked.stdout + linked.stderr
    executed = run_command((str(executable),), tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr


@pytest.mark.skipif(
    os.name != WINDOWS_OS_NAME,
    reason="pinned native sanitizer runtime is Windows x86-64",
)
def test_guest_runtime_sanitizers(tmp_path: Path) -> None:
    """Execute guest-runtime vectors under pinned ASan and UBSan."""
    executable = tmp_path / "guest-runtime-sanitized.exe"
    compiled = run_command(
        (
            str(CLANG),
            "-std=c23",
            "-fno-builtin",
            "-fsanitize=address,undefined",
            *STRICT_WARNINGS,
            f"-I{INCLUDE}",
            *(str(source) for source in SOURCES),
            "-o",
            str(executable),
        ),
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr

    sanitizer_env = dict(os.environ)
    sanitizer_env["PATH"] = (
        f"{SANITIZER_RUNTIME_DIR}{os.pathsep}{sanitizer_env.get("PATH", "")}"
    )
    sanitizer_env["ASAN_OPTIONS"] = "halt_on_error=1"
    sanitizer_env["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=1"
    executed = run_command((str(executable),), tmp_path, env=sanitizer_env)
    assert executed.returncode == 0, executed.stdout + executed.stderr

    format_executable = tmp_path / "guest-format-sanitized.exe"
    format_compiled = run_command(
        (
            str(CLANG),
            "-std=c23",
            "-fno-builtin",
            "-fsanitize=address,undefined",
            *STRICT_WARNINGS,
            f"-I{INCLUDE}",
            str(FORMAT_SOURCE),
            str(FORMAT_HARNESS),
            "-o",
            str(format_executable),
        ),
        ROOT,
    )
    assert format_compiled.returncode == 0, (
        format_compiled.stdout + format_compiled.stderr
    )
    format_executed = run_command(
        (str(format_executable),),
        tmp_path,
        env=sanitizer_env,
    )
    assert format_executed.returncode == 0, (
        format_executed.stdout + format_executed.stderr
    )


@pytest.mark.skipif(
    os.name != WINDOWS_OS_NAME,
    reason="pinned native C runtime harness uses Windows Clang",
)
def test_guest_allocation_wrapper_conformance(tmp_path: Path) -> None:
    """Execute public allocation wrapper bodies over guest runtime state."""
    renamed_object = tmp_path / "allocation-test.o"
    compiled = run_command(
        (
            str(CLANG),
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            "-Dmalloc=malbolge_test_malloc",
            "-Dcalloc=malbolge_test_calloc",
            "-Drealloc=malbolge_test_realloc",
            "-Dfree=malbolge_test_free",
            *STRICT_WARNINGS,
            f"-I{GUEST_LIBC_INCLUDE}",
            f"-I{INCLUDE}",
            "-c",
            str(ALLOCATION_WRAPPERS),
            "-o",
            str(renamed_object),
        ),
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr

    executable = tmp_path / "guest-allocation-wrapper.exe"
    linked = run_command(
        (
            str(CLANG),
            "-std=c23",
            "-fno-builtin",
            *STRICT_WARNINGS,
            f"-I{INCLUDE}",
            str(HEAP_SOURCE),
            str(STARTUP_SOURCE),
            str(renamed_object),
            str(ALLOCATION_HARNESS),
            "-o",
            str(executable),
        ),
        ROOT,
    )
    assert linked.returncode == 0, linked.stdout + linked.stderr
    executed = run_command((str(executable),), tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr


@pytest.mark.skipif(
    os.name != WINDOWS_OS_NAME,
    reason="pinned native static analyzer uses Windows Clang",
)
def test_guest_runtime_static_analysis() -> None:
    """Require path-sensitive Clang analysis to emit no runtime diagnostics."""
    for source in RUNTIME_SOURCES:
        analyzed = run_command(
            (
                str(CLANG),
                "--analyze",
                "-std=c23",
                "-ffreestanding",
                "-fno-builtin",
                *STRICT_WARNINGS,
                f"-I{INCLUDE}",
                "-Xanalyzer",
                "-analyzer-output=text",
                str(source),
            ),
            ROOT,
        )
        assert analyzed.returncode == 0, analyzed.stdout + analyzed.stderr
        assert not analyzed.stderr.strip()

    for source in (ALLOCATION_WRAPPERS, STDIO_WRAPPERS):
        analyzed = run_command(
            (
                str(CLANG),
                "--analyze",
                "-std=c23",
                "-ffreestanding",
                "-fno-builtin",
                *STRICT_WARNINGS,
                f"-I{GUEST_LIBC_INCLUDE}",
                f"-I{INCLUDE}",
                "-Xanalyzer",
                "-analyzer-output=text",
                str(source),
            ),
            ROOT,
        )
        assert analyzed.returncode == 0, analyzed.stdout + analyzed.stderr
        assert not analyzed.stderr.strip()


@pytest.mark.skipif(
    os.name != WINDOWS_OS_NAME,
    reason="pinned native format-parser harness uses Windows Clang",
)
def test_guest_format_parser_conformance(tmp_path: Path) -> None:
    """Lock C23 grammar tokens and parser dependency boundaries."""
    for target in WINDOWS_ABI_TARGETS:
        compiled = run_command(
            (
                str(CLANG),
                f"--target={target}",
                "-std=c23",
                "-ffreestanding",
                "-fno-builtin",
                *STRICT_WARNINGS,
                f"-I{INCLUDE}",
                "-fsyntax-only",
                str(FORMAT_PARSE_SOURCE),
                str(FORMAT_PARSE_HARNESS),
            ),
            ROOT,
        )
        assert compiled.returncode == 0, compiled.stdout + compiled.stderr

    wasm_object = tmp_path / "format-parse-wasm.o"
    wasm_compiled = run_command(
        (
            str(CLANG),
            "--target=wasm32-unknown-unknown",
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            *STRICT_WARNINGS,
            f"-I{INCLUDE}",
            "-c",
            str(FORMAT_PARSE_SOURCE),
            "-o",
            str(wasm_object),
        ),
        ROOT,
    )
    assert wasm_compiled.returncode == 0, (
        wasm_compiled.stdout + wasm_compiled.stderr
    )
    assert undefined_symbols(wasm_object) == WASM_STACK_UNDEFINED

    executable = tmp_path / "guest-format-parse.exe"
    linked = run_command(
        (
            str(CLANG),
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            *STRICT_WARNINGS,
            f"-I{INCLUDE}",
            str(FORMAT_PARSE_SOURCE),
            str(FORMAT_PARSE_HARNESS),
            "-o",
            str(executable),
        ),
        ROOT,
    )
    assert linked.returncode == 0, linked.stdout + linked.stderr
    executed = run_command((str(executable),), tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr


@pytest.mark.skipif(
    os.name != WINDOWS_OS_NAME,
    reason="pinned native guest-varargs harness uses Windows Clang",
)
def test_guest_varargs_conformance(tmp_path: Path) -> None:
    """Lock canonical promoted-argument cursor semantics and dependencies."""
    for target in WINDOWS_ABI_TARGETS:
        compiled = run_command(
            (
                str(CLANG),
                f"--target={target}",
                "-std=c23",
                "-ffreestanding",
                "-fno-builtin",
                *STRICT_WARNINGS,
                f"-I{INCLUDE}",
                "-fsyntax-only",
                str(VARARGS_SOURCE),
                str(VARARGS_HARNESS),
            ),
            ROOT,
        )
        assert compiled.returncode == 0, compiled.stdout + compiled.stderr

    wasm_object = tmp_path / "guest-varargs-wasm.o"
    wasm_compiled = run_command(
        (
            str(CLANG),
            "--target=wasm32-unknown-unknown",
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            *STRICT_WARNINGS,
            f"-I{INCLUDE}",
            "-c",
            str(VARARGS_SOURCE),
            "-o",
            str(wasm_object),
        ),
        ROOT,
    )
    assert wasm_compiled.returncode == 0, (
        wasm_compiled.stdout + wasm_compiled.stderr
    )
    assert undefined_symbols(wasm_object) == WASM_STACK_UNDEFINED

    executable = tmp_path / "guest-varargs.exe"
    linked = run_command(
        (
            str(CLANG),
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            *STRICT_WARNINGS,
            f"-I{INCLUDE}",
            str(VARARGS_SOURCE),
            str(VARARGS_HARNESS),
            "-o",
            str(executable),
        ),
        ROOT,
    )
    assert linked.returncode == 0, linked.stdout + linked.stderr
    executed = run_command((str(executable),), tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr


@pytest.mark.skipif(
    os.name != WINDOWS_OS_NAME,
    reason="pinned native format-argument harness uses Windows Clang",
)
def test_guest_format_argument_resolution(tmp_path: Path) -> None:
    """Lock dynamic fields, promotion mapping, and transactional rollback."""
    sources = (FORMAT_PARSE_SOURCE, VARARGS_SOURCE, FORMAT_ARGS_SOURCE)
    for target in WINDOWS_ABI_TARGETS:
        compiled = run_command(
            (
                str(CLANG),
                f"--target={target}",
                "-std=c23",
                "-ffreestanding",
                "-fno-builtin",
                *STRICT_WARNINGS,
                f"-I{INCLUDE}",
                "-fsyntax-only",
                *(str(source) for source in sources),
                str(FORMAT_ARGS_HARNESS),
            ),
            ROOT,
        )
        assert compiled.returncode == 0, compiled.stdout + compiled.stderr

    wasm_object = tmp_path / "format-args-wasm.o"
    wasm_compiled = run_command(
        (
            str(CLANG),
            "--target=wasm32-unknown-unknown",
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            *STRICT_WARNINGS,
            f"-I{INCLUDE}",
            "-c",
            str(FORMAT_ARGS_SOURCE),
            "-o",
            str(wasm_object),
        ),
        ROOT,
    )
    assert wasm_compiled.returncode == 0, (
        wasm_compiled.stdout + wasm_compiled.stderr
    )
    assert undefined_symbols(wasm_object) == frozenset({
        "_stack_pointer",
        "malbolge_guest_format_argument_kind",
        "malbolge_guest_format_directive_validate",
        "malbolge_guest_varargs_read",
        "malbolge_guest_varargs_validate",
    })

    executable = tmp_path / "guest-format-args.exe"
    linked = run_command(
        (
            str(CLANG),
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            *STRICT_WARNINGS,
            f"-I{INCLUDE}",
            *(str(source) for source in sources),
            str(FORMAT_ARGS_HARNESS),
            "-o",
            str(executable),
        ),
        ROOT,
    )
    assert linked.returncode == 0, linked.stdout + linked.stderr
    executed = run_command((str(executable),), tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr


@pytest.mark.skipif(
    os.name != WINDOWS_OS_NAME,
    reason="pinned native scalar-format harness uses Windows Clang",
)
def test_guest_scalar_format_execution(tmp_path: Path) -> None:
    """Lock post-promotion narrowing and scalar conversion output."""
    sources = (FORMAT_SOURCE, FORMAT_PARSE_SOURCE, FORMAT_SCALAR_SOURCE)
    for target in WINDOWS_ABI_TARGETS:
        compiled = run_command(
            (
                str(CLANG),
                f"--target={target}",
                "-std=c23",
                "-ffreestanding",
                "-fno-builtin",
                *STRICT_WARNINGS,
                f"-I{INCLUDE}",
                "-fsyntax-only",
                *(str(source) for source in sources),
                str(FORMAT_SCALAR_HARNESS),
            ),
            ROOT,
        )
        assert compiled.returncode == 0, compiled.stdout + compiled.stderr

    wasm_object = tmp_path / "format-scalar-wasm.o"
    wasm_compiled = run_command(
        (
            str(CLANG),
            "--target=wasm32-unknown-unknown",
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            *STRICT_WARNINGS,
            f"-I{INCLUDE}",
            "-c",
            str(FORMAT_SCALAR_SOURCE),
            "-o",
            str(wasm_object),
        ),
        ROOT,
    )
    assert wasm_compiled.returncode == 0, (
        wasm_compiled.stdout + wasm_compiled.stderr
    )
    assert undefined_symbols(wasm_object) == frozenset({
        "_stack_pointer",
        "malbolge_guest_format_argument_kind",
        "malbolge_guest_format_character",
        "malbolge_guest_format_signed_decimal",
        "malbolge_guest_format_unsigned",
    })

    executable = tmp_path / "guest-format-scalar.exe"
    linked = run_command(
        (
            str(CLANG),
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            *STRICT_WARNINGS,
            f"-I{INCLUDE}",
            *(str(source) for source in sources),
            str(FORMAT_SCALAR_HARNESS),
            "-o",
            str(executable),
        ),
        ROOT,
    )
    assert linked.returncode == 0, linked.stdout + linked.stderr
    executed = run_command((str(executable),), tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr


@pytest.mark.skipif(
    os.name != WINDOWS_OS_NAME,
    reason="pinned native memory-format harness uses Windows Clang",
)
def test_guest_memory_format_execution(tmp_path: Path) -> None:
    """Lock bounded guest-object string reads and count stores."""
    sources = (FORMAT_SOURCE, FORMAT_PARSE_SOURCE, FORMAT_MEMORY_SOURCE)
    for target in WINDOWS_ABI_TARGETS:
        compiled = run_command(
            (
                str(CLANG),
                f"--target={target}",
                "-std=c23",
                "-ffreestanding",
                "-fno-builtin",
                *STRICT_WARNINGS,
                f"-I{INCLUDE}",
                "-fsyntax-only",
                *(str(source) for source in sources),
                str(FORMAT_MEMORY_HARNESS),
            ),
            ROOT,
        )
        assert compiled.returncode == 0, compiled.stdout + compiled.stderr

    wasm_object = tmp_path / "format-memory-wasm.o"
    wasm_compiled = run_command(
        (
            str(CLANG),
            "--target=wasm32-unknown-unknown",
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            *STRICT_WARNINGS,
            f"-I{INCLUDE}",
            "-c",
            str(FORMAT_MEMORY_SOURCE),
            "-o",
            str(wasm_object),
        ),
        ROOT,
    )
    assert wasm_compiled.returncode == 0, (
        wasm_compiled.stdout + wasm_compiled.stderr
    )
    assert undefined_symbols(wasm_object) == frozenset({
        "_stack_pointer",
        "malbolge_guest_format_argument_kind",
        "malbolge_guest_format_bytes",
    })

    executable = tmp_path / "guest-format-memory.exe"
    linked = run_command(
        (
            str(CLANG),
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            *STRICT_WARNINGS,
            f"-I{INCLUDE}",
            *(str(source) for source in sources),
            str(FORMAT_MEMORY_HARNESS),
            "-o",
            str(executable),
        ),
        ROOT,
    )
    assert linked.returncode == 0, linked.stdout + linked.stderr
    executed = run_command((str(executable),), tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr


@pytest.mark.skipif(
    os.name != WINDOWS_OS_NAME,
    reason="pinned native hexadecimal-float harness uses Windows Clang",
)
def test_guest_hexadecimal_float_format_execution(tmp_path: Path) -> None:
    """Lock integer-only binary64 a/A conversion and dependency boundaries."""
    sources = (FORMAT_SOURCE, FORMAT_PARSE_SOURCE, FORMAT_FLOAT_SOURCE)
    for target in WINDOWS_ABI_TARGETS:
        compiled = run_command(
            (
                str(CLANG),
                f"--target={target}",
                "-std=c23",
                "-ffreestanding",
                "-fno-builtin",
                *STRICT_WARNINGS,
                f"-I{INCLUDE}",
                "-fsyntax-only",
                *(str(source) for source in sources),
                str(FORMAT_FLOAT_HARNESS),
            ),
            ROOT,
        )
        assert compiled.returncode == 0, compiled.stdout + compiled.stderr

    wasm_object = tmp_path / "format-float-wasm.o"
    wasm_compiled = run_command(
        (
            str(CLANG),
            "--target=wasm32-unknown-unknown",
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            *STRICT_WARNINGS,
            f"-I{INCLUDE}",
            "-c",
            str(FORMAT_FLOAT_SOURCE),
            "-o",
            str(wasm_object),
        ),
        ROOT,
    )
    assert wasm_compiled.returncode == 0, (
        wasm_compiled.stdout + wasm_compiled.stderr
    )
    assert undefined_symbols(wasm_object) == frozenset({
        "_stack_pointer",
        "malbolge_guest_format_argument_kind",
    })

    executable = tmp_path / "guest-format-float.exe"
    linked = run_command(
        (
            str(CLANG),
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            *STRICT_WARNINGS,
            f"-I{INCLUDE}",
            *(str(source) for source in sources),
            str(FORMAT_FLOAT_HARNESS),
            "-o",
            str(executable),
        ),
        ROOT,
    )
    assert linked.returncode == 0, linked.stdout + linked.stderr
    executed = run_command((str(executable),), tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr
