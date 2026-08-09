# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Regression evidence for the version-one deterministic guest C library.
# - Must-Not:
#   - Treat host libc execution as guest conformance or implement future
#     runtime.
# - Allows:
#   - Inputs: canonical libc JSON, guest sources, fixtures, and pinned LLVM
#     tools.
#   - Outputs: schema, source-diagnostic, compile, link, and execution evidence.
#   - Side effects: compilation and execution only inside pytest temporary
#     state.
# - Split-When:
#   - Split when another guest libc version gains an independent contract.
# - Merge-When:
#   - Merge when another suite owns this exact guest-library evidence lifecycle.
# - Summary:
#   - Locks malbolge-libc-v1 availability and executable guest behavior.
# - Description:
#   - Proves available routines are self-contained guest C and rejects others.
# - Usage:
#   - Collected by the repository Python validation suite.
# - Defaults:
#   - Missing pinned Windows tools skip native execution, never substitute host.
#

"""Regression tests for the canonical malbolge-libc-v1 contract."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from typing import cast

import pytest
from scripts.validate import c_abi
from scripts.validate import c_libc
from scripts.validate import c_libc_source

ROOT = Path(__file__).resolve().parents[1]
LIBC_PATH = ROOT / "docs/technical/specification/c-libc-v1.json"
LIBC_ROOT = ROOT / "src/runtime/guest-c-library"
INCLUDE = LIBC_ROOT / "contract/include"
MEMORY = LIBC_ROOT / "domain/memory.c"
STRING = LIBC_ROOT / "domain/string.c"
MATH_EXACT = LIBC_ROOT / "domain/math_exact.c"
MATH_SQRT = LIBC_ROOT / "domain/math_sqrt.c"
ACCEPTED = ROOT / "tests/tidy/libc/accepted/libc_memory_string.c"
ACCEPTED_MATH = ROOT / "tests/tidy/libc/accepted/libc_math_exact.c"
ACCEPTED_SQRT = ROOT / "tests/tidy/libc/accepted/libc_math_sqrt.c"
REJECTED = ROOT / "tests/tidy/libc-rejected"
HARNESS = ROOT / "tests/tidy/libc/guest_libc_harness.c"
CLANG = ROOT / ".dependencies/llvm/22.1.8/bin/clang.exe"
LLD_LINK = ROOT / ".dependencies/llvm/22.1.8/bin/lld-link.exe"
LLVM_NM = ROOT / ".dependencies/llvm/22.1.8/bin/llvm-nm.exe"
VALIDATOR = (
    ROOT / "src/automation/repository/composition/scripts/validate/main.py"
)
WINDOWS_OS_NAME = "nt"
EXPECTED_DIAGNOSTIC_LINE = 39
EXPECTED_DIAGNOSTIC_COLUMN = 12
MALLOC_ROUTINE = "malloc"
MATH_OBJECT_STEMS = frozenset({"math_exact", "math_sqrt"})
MSVC_FLOAT_MARKER = frozenset({"_fltused"})
WINDOWS_ABI_TARGETS = (
    ("i686-pc-windows-msvc", frozenset({"__fltused"})),
    ("x86_64-pc-windows-msvc", MSVC_FLOAT_MARKER),
    ("aarch64-pc-windows-msvc", frozenset[str]()),
)
WASM_TARGET_MACHINERY = frozenset({"__stack_pointer"})
EXPECTED_AVAILABLE = frozenset({
    "ceil",
    "fabs",
    "floor",
    "memcmp",
    "memcpy",
    "memmove",
    "memset",
    "strcat",
    "strcmp",
    "strcpy",
    "strlen",
    "strncpy",
    "sqrt",
    "trunc",
})
EXPECTED_UNAVAILABLE = frozenset({
    "atan2",
    "calloc",
    "cos",
    "free",
    "getchar",
    "malloc",
    "putchar",
    "realloc",
    "sin",
    "snprintf",
    "vsnprintf",
})
EXPECTED_FORBIDDEN = frozenset({
    "fopen",
    "getenv",
    "setlocale",
    "signal",
    "system",
    "time",
    "tmpfile",
})
SOURCE_REJECTIONS = (
    (
        "libc_malloc_unavailable.c",
        c_libc_source.DIAGNOSTIC_UNAVAILABLE,
        "malloc",
    ),
    (
        "libc_calloc_unavailable.c",
        c_libc_source.DIAGNOSTIC_UNAVAILABLE,
        "calloc",
    ),
    (
        "libc_realloc_unavailable.c",
        c_libc_source.DIAGNOSTIC_UNAVAILABLE,
        "realloc",
    ),
    (
        "libc_free_unavailable.c",
        c_libc_source.DIAGNOSTIC_UNAVAILABLE,
        "free",
    ),
    (
        "libc_getchar_unavailable.c",
        c_libc_source.DIAGNOSTIC_UNAVAILABLE,
        "getchar",
    ),
    (
        "libc_putchar_unavailable.c",
        c_libc_source.DIAGNOSTIC_UNAVAILABLE,
        "putchar",
    ),
    (
        "libc_snprintf_unavailable.c",
        c_libc_source.DIAGNOSTIC_UNAVAILABLE,
        "snprintf",
    ),
    (
        "libc_vsnprintf_unavailable.c",
        c_libc_source.DIAGNOSTIC_UNAVAILABLE,
        "vsnprintf",
    ),
    (
        "libc_math_unavailable.c",
        c_libc_source.DIAGNOSTIC_UNAVAILABLE,
        "sin",
    ),
    (
        "libc_system_forbidden.c",
        c_libc_source.DIAGNOSTIC_FORBIDDEN,
        "system",
    ),
)
STRICT_C = (
    "-std=c23",
    "-ffreestanding",
    "-fno-builtin",
    "-fno-stack-protector",
    "-Wall",
    "-Wextra",
    "-Wpedantic",
    "-Werror",
)


def _document() -> c_libc.JsonObject:
    return c_libc.load_document(LIBC_PATH)


def _run(command: list[str], cwd: Path) -> sp.CompletedProcess[str]:
    return sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        timeout=30,
    )


def _require_clang() -> None:
    if not CLANG.is_file():
        pytest.skip("repository-pinned Clang is unavailable")


def test_canonical_libc_contract_is_closed_and_abi_bound() -> None:
    """Canonical library identity and availability are exact."""
    projection = c_libc.canonical_projection()

    assert projection.libc_id == c_libc.LIBC_ID
    assert projection.abi_id == c_abi.ABI_ID
    assert projection.target_profile == c_abi.TARGET_PROFILE
    assert projection.available_routines == EXPECTED_AVAILABLE
    assert projection.unavailable_routines == EXPECTED_UNAVAILABLE
    assert projection.forbidden_routines == EXPECTED_FORBIDDEN
    assert projection.guest_headers == (
        "math.h",
        "stdio.h",
        "stdlib.h",
        "string.h",
    )


def test_duplicate_libc_keys_fail_closed() -> None:
    """Duplicate policy keys cannot silently replace guest-library authority."""
    text = '{"schema_version":1,"schema_version":1}'
    with pytest.raises(c_libc.CLibcValidationError, match="duplicate JSON key"):
        _ = c_libc.loads_document(text)


def test_unknown_libc_key_fails_closed() -> None:
    """Unknown v1 policy requires a schema revision instead of being ignored."""
    document = _document()
    document["host_libc"] = "msvcrt"
    with pytest.raises(
        c_libc.CLibcValidationError,
        match=r"unknown=.*host_libc",
    ):
        _ = c_libc.validate_document(document)


def test_available_routine_drift_fails_closed() -> None:
    """Removing one executable routine is contract drift, not a local edit."""
    document = _document()
    routines = cast("list[c_libc.JsonValue]", document["available_routines"])
    document["available_routines"] = routines[1:]

    with pytest.raises(
        c_libc.CLibcValidationError,
        match="available_routines names",
    ):
        _ = c_libc.validate_document(document)


def test_guest_headers_are_repository_owned() -> None:
    """Every guest header is tracked under the guest runtime boundary."""
    projection = c_libc.canonical_projection()

    for header in projection.guest_headers:
        assert (projection.include_root / header).is_file()


def test_executable_guest_libc_compiles_for_frontend_target() -> None:
    """Available guest routines and their positive fixture are strict C23."""
    _require_clang()
    for source in (
        MEMORY,
        STRING,
        MATH_EXACT,
        MATH_SQRT,
        ACCEPTED,
        ACCEPTED_MATH,
        ACCEPTED_SQRT,
    ):
        completed = _run(
            [
                str(CLANG),
                "--target=wasm32-unknown-unknown",
                *STRICT_C,
                f"-I{INCLUDE}",
                "-fsyntax-only",
                str(source),
            ],
            ROOT,
        )
        assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize(("fixture", "code", "routine"), SOURCE_REJECTIONS)
def test_libc_source_preflight_reports_exact_routine_use(
    fixture: str,
    code: str,
    routine: str,
) -> None:
    """Unavailable and forbidden routines are rejected at the call source."""
    _require_clang()
    source = REJECTED / fixture

    diagnostics = c_libc_source.analyze_source(source)

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code == code
    assert diagnostic.path == source.resolve()
    assert diagnostic.line == EXPECTED_DIAGNOSTIC_LINE
    assert diagnostic.column == EXPECTED_DIAGNOSTIC_COLUMN
    assert routine in diagnostic.message


def test_user_defined_forbidden_name_is_not_a_libc_call(
    tmp_path: Path,
) -> None:
    """A source-owned function name is not mistaken for host libc identity."""
    _require_clang()
    source = tmp_path / "user-system.c"
    text = "static int system(const char *s) { return s[0] == 0; }"
    text += chr(10)
    text += 'int probe(void) { return system("x"); }'
    text += chr(10)
    _ = source.write_text(text, encoding="utf-8")

    assert c_libc_source.analyze_source(source) == ()


def test_declaration_only_header_is_not_itself_a_rejection(
    tmp_path: Path,
) -> None:
    """Contracted signatures may be included without pretending calls work."""
    _require_clang()
    source = tmp_path / "declaration-only.c"
    _ = source.write_text(
        "#include <stdlib.h>\nint declaration_probe(void) { return 0; }\n",
        encoding="utf-8",
    )

    assert c_libc_source.analyze_source(source) == ()


def _undefined_symbols(object_file: Path) -> frozenset[str]:
    completed = _run([str(LLVM_NM), "-u", str(object_file)], ROOT)
    assert completed.returncode == 0, completed.stderr
    return frozenset(
        line.split()[-1]
        for line in completed.stdout.splitlines()
        if line.split()
    )


def _assert_native_guest_object_dependencies(objects: list[Path]) -> None:
    for runtime_object in objects[:4]:
        expected = (
            MSVC_FLOAT_MARKER
            if runtime_object.stem in MATH_OBJECT_STEMS
            else frozenset[str]()
        )
        assert _undefined_symbols(runtime_object) == expected


def _assert_wasm_math_dependencies(tmp_path: Path) -> None:
    for source in (MATH_EXACT, MATH_SQRT):
        wasm_math = tmp_path / f"{source.stem}-wasm.o"
        wasm_compiled = _run(
            [
                str(CLANG),
                "--target=wasm32-unknown-unknown",
                *STRICT_C,
                f"-I{INCLUDE}",
                "-c",
                str(source),
                "-o",
                str(wasm_math),
            ],
            ROOT,
        )
        assert wasm_compiled.returncode == 0, wasm_compiled.stderr
        assert _undefined_symbols(wasm_math) == WASM_TARGET_MACHINERY


@pytest.mark.skipif(
    os.name != WINDOWS_OS_NAME,
    reason="pinned Windows Clang object matrix is Windows-only",
)
def test_exact_math_has_only_target_float_markers(tmp_path: Path) -> None:
    """Exact math never gains a callable compiler or host-library helper."""
    for target, expected in WINDOWS_ABI_TARGETS:
        object_file = tmp_path / f"math-{target}.obj"
        compiled = _run(
            [
                str(CLANG),
                f"--target={target}",
                *STRICT_C,
                f"-I{INCLUDE}",
                "-c",
                str(MATH_EXACT),
                "-o",
                str(object_file),
            ],
            ROOT,
        )
        assert compiled.returncode == 0, compiled.stderr
        assert _undefined_symbols(object_file) == expected


@pytest.mark.skipif(
    os.name != WINDOWS_OS_NAME,
    reason="no-CRT guest libc harness uses pinned Windows LLVM tools",
)
def test_guest_libc_executes_without_host_crt(tmp_path: Path) -> None:
    """All available routine semantics execute with no host C runtime link."""
    for tool in (CLANG, LLD_LINK, LLVM_NM):
        if not tool.is_file():
            pytest.skip(f"repository-pinned tool is unavailable: {tool.name}")

    objects: list[Path] = []
    for source in (MEMORY, STRING, MATH_EXACT, MATH_SQRT, HARNESS):
        output = tmp_path / f"{source.stem}.obj"
        compiled = _run(
            [
                str(CLANG),
                "--target=x86_64-pc-windows-msvc",
                *STRICT_C,
                f"-I{INCLUDE}",
                "-c",
                str(source),
                "-o",
                str(output),
            ],
            ROOT,
        )
        assert compiled.returncode == 0, compiled.stderr
        objects.append(output)

    executable = tmp_path / "guest-libc.exe"
    linked = _run(
        [
            str(LLD_LINK),
            "/nodefaultlib",
            "/subsystem:console",
            "/entry:probe_entry",
            "/machine:x64",
            "/opt:ref",
            *(str(path) for path in objects),
            f"/out:{executable}",
        ],
        ROOT,
    )
    assert linked.returncode == 0, linked.stderr

    executed = _run([str(executable)], tmp_path)
    assert executed.returncode == 0, executed.stderr

    _assert_native_guest_object_dependencies(objects)
    _assert_wasm_math_dependencies(tmp_path)


def test_manual_validator_runs_libc_preflight_before_tidy() -> None:
    """Admit available routines and reject unavailable allocation calls."""
    _require_clang()
    for accepted_source in (ACCEPTED, ACCEPTED_MATH, ACCEPTED_SQRT):
        accepted = _run(
            [sys.executable, str(VALIDATOR), str(accepted_source)],
            ROOT,
        )
        assert accepted.returncode == 0, accepted.stderr

    rejected = _run(
        [
            sys.executable,
            str(VALIDATOR),
            str(REJECTED / "libc_malloc_unavailable.c"),
        ],
        ROOT,
    )
    assert rejected.returncode == 1
    assert c_libc_source.DIAGNOSTIC_UNAVAILABLE in rejected.stderr
    assert MALLOC_ROUTINE in rejected.stderr
