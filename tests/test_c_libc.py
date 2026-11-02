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
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Self, TextIO, cast, override

import pytest

from scripts.validate import c_abi, c_libc, c_libc_source

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import BinaryIO

ROOT = Path(__file__).resolve().parents[1]
LIBC_PATH = ROOT / "docs/technical/specification/c-libc-v1.json"
LIBC_ROOT = ROOT / "src/runtime/guest-c-library"
INCLUDE = LIBC_ROOT / "contract/include"
MEMORY = LIBC_ROOT / "domain/memory.c"
STRING = LIBC_ROOT / "domain/string.c"
MATH_EXACT = LIBC_ROOT / "domain/math_exact.c"
MATH_SQRT = LIBC_ROOT / "domain/math_sqrt.c"
MATH_SINCOS = LIBC_ROOT / "domain/math_sincos.c"
MATH_TRANS_SPECIAL = LIBC_ROOT / "domain/math_transcendental_bits.c"
MATH_INTERNAL = LIBC_ROOT / "contract"
MATH_TRANS_HARNESS = (
    ROOT / "tests/runtime/guest_math_transcendental_special_conformance.c"
)
MATH_SINCOS_HARNESS = ROOT / "tests/runtime/guest_math_sincos_conformance.c"
MATH_ATAN2_INPUT_HARNESS = (
    ROOT / "tests/runtime/guest_math_atan2_kernel_input_conformance.c"
)
ACCEPTED = ROOT / "tests/tidy/libc/accepted/libc_memory_string.c"
ACCEPTED_MATH = ROOT / "tests/tidy/libc/accepted/libc_math_exact.c"
ACCEPTED_SQRT = ROOT / "tests/tidy/libc/accepted/libc_math_sqrt.c"
ACCEPTED_SINCOS = ROOT / "tests/tidy/libc/accepted/libc_math_sincos.c"
REJECTED = ROOT / "tests/tidy/libc-rejected"
HARNESS = ROOT / "tests/tidy/libc/guest_libc_harness.c"
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
LLD_LINK = ROOT / ".dependencies/llvm/22.1.8/bin/lld-link.exe"
LLVM_NM = ROOT / ".dependencies/llvm/22.1.8/bin/llvm-nm.exe"
VALIDATOR = ROOT / "src/automation/repository/composition/scripts/validate/main.py"
WINDOWS_OS_NAME = "nt"
LOADER_SYMLINK = "symlink"
LOADER_DIRECTORY = "directory"
LOADER_FIFO = "fifo"
EXPECTED_DIAGNOSTIC_LINE = 39
EXPECTED_DIAGNOSTIC_COLUMN = 12
MALLOC_ROUTINE = "malloc"
SYSTEM_ROUTINE = "system"
MATH_OBJECT_STEMS = frozenset({"math_exact", "math_sqrt"})
MSVC_FLOAT_MARKER = frozenset({"_fltused"})
WINDOWS_ABI_TARGETS = (
    ("i686-pc-windows-msvc", frozenset({"__fltused"})),
    ("x86_64-pc-windows-msvc", MSVC_FLOAT_MARKER),
    ("aarch64-pc-windows-msvc", frozenset[str]()),
)
WASM_TARGET_MACHINERY = frozenset({"__stack_pointer"})
EXPECTED_AVAILABLE = frozenset(
    {
        "ceil",
        "cos",
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
        "sin",
        "sqrt",
        "trunc",
    }
)
EXPECTED_UNAVAILABLE = frozenset(
    {
        "atan2",
        "calloc",
        "free",
        "getchar",
        "malloc",
        "putchar",
        "realloc",
        "snprintf",
        "vsnprintf",
    }
)
EXPECTED_FORBIDDEN = frozenset(
    {
        "fopen",
        "getenv",
        "setlocale",
        "signal",
        "system",
        "time",
        "tmpfile",
    }
)
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
        "atan2",
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


def test_guest_libc_json_parser_rejects_unbounded_direct_text() -> None:
    """Direct parser calls cannot bypass the file authority's byte budget."""
    oversized = '{"a":"' + "x" * c_libc.MAX_DOCUMENT_BYTES + '"}'
    with pytest.raises(c_libc.CLibcValidationError, match="JSON.*byte limit"):
        _ = c_libc.loads_document(oversized)


def test_guest_libc_json_parser_rejects_non_utf8_text() -> None:
    """Direct parser text must be strict UTF-8 representable source input."""
    text = '{"a":"' + chr(0xD800) + '"}'
    with pytest.raises(c_libc.CLibcValidationError, match="JSON.*UTF-8"):
        _ = c_libc.loads_document(text)


@pytest.mark.parametrize("value", [None, b"{}", ["{}"], 1])
def test_guest_libc_json_parser_rejects_nontext_input(value: object) -> None:
    """Direct parser calls must fail through the same typed authority boundary."""
    with pytest.raises(c_libc.CLibcValidationError, match="JSON.*text"):
        _ = c_libc.loads_document(cast("str", value))


def test_guest_libc_document_reads_regular_copy(tmp_path: Path) -> None:
    """A normal detached JSON fixture is accepted by the authority loader."""
    copy = tmp_path / "libc.json"
    _ = copy.write_bytes(LIBC_PATH.read_bytes())
    assert c_libc.load_document(copy) == _document()


@pytest.mark.parametrize("kind", ["symlink", "directory", "fifo", "oversized"])
def test_guest_libc_loader_rejects_redirects_and_special_files(
    kind: str,
    tmp_path: Path,
) -> None:
    """Redirected or nonregular authorities cannot reach the schema parser."""
    path = tmp_path / "authority.json"
    if kind == LOADER_SYMLINK:
        path.symlink_to(LIBC_PATH)
    elif kind == LOADER_DIRECTORY:
        path.mkdir()
    elif kind == LOADER_FIFO:
        mkfifo = cast(
            "Callable[[Path], None] | None",
            getattr(os, "mkfifo", None),
        )
        if mkfifo is None:
            pytest.skip("FIFOs are unavailable on this host")
        mkfifo(path)
    else:
        _ = path.write_bytes(b"x" * (c_libc.MAX_DOCUMENT_BYTES + 1))
    with pytest.raises(
        c_libc.CLibcValidationError,
        match=r"regular non-redirected file|exceeds byte limit",
    ):
        _ = c_libc.load_document(path)


def test_guest_libc_loader_rejects_parent_directory_symlink(
    tmp_path: Path,
) -> None:
    """The authority path cannot redirect through a linked ancestor."""
    linked = tmp_path / "linked"
    linked.symlink_to(LIBC_PATH.parent, target_is_directory=True)
    with pytest.raises(
        c_libc.CLibcValidationError,
        match="path must not redirect",
    ):
        _ = c_libc.load_document(linked / LIBC_PATH.name)


def test_guest_libc_loader_rejects_invalid_utf8(tmp_path: Path) -> None:
    """Invalid UTF-8 stays inside the typed libc error boundary."""
    path = tmp_path / "libc.json"
    _ = path.write_bytes(b"\xff")
    with pytest.raises(
        c_libc.CLibcValidationError,
        match="invalid C libc UTF-8",
    ):
        _ = c_libc.load_document(path)


class _HostileLibcPath(type(Path())):
    """A foreign Path can redirect or fail within os.fspath hooks."""

    @override
    def __fspath__(self) -> str:
        message = "untrusted authority path formatting executed"
        raise AssertionError(message)


def test_guest_libc_loader_rejects_foreign_path_before_host_hooks(
    tmp_path: Path,
) -> None:
    """Only exact native paths may cross the filesystem authority boundary."""
    foreign = _HostileLibcPath(tmp_path / "libc.json")
    with pytest.raises(c_libc.CLibcValidationError, match="native Path"):
        _ = c_libc.load_document(foreign)


@pytest.mark.parametrize(
    "fault", [OSError, ValueError, RuntimeError, TypeError, AttributeError]
)
@pytest.mark.parametrize(
    "stage",
    [
        "path-lstat",
        "post-read-lstat",
        "parent-junction",
        "leaf-junction",
        "open",
        "fstat",
        "post-read-fstat",
    ],
)
def test_guest_libc_host_inspection_errors_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
    stage: str,
) -> None:
    """Host path, junction and descriptor faults cannot bypass libc errors."""
    path = tmp_path / "libc.json"
    _ = path.write_bytes(LIBC_PATH.read_bytes())
    original_lstat = Path.lstat
    original_junction = Path.is_junction
    stat_calls = 0

    def failing_lstat(candidate: Path, *args: object, **kwargs: object) -> object:
        nonlocal stat_calls
        if candidate == path:
            stat_calls += 1
            if stage != "post-read-lstat" or stat_calls == 2:
                raise fault("injected libc lstat failure")
        return original_lstat(candidate, *args, **kwargs)

    def failing_junction(candidate: Path) -> bool:
        if candidate == (tmp_path if stage == "parent-junction" else path):
            raise fault("injected libc junction inspection failure")
        return original_junction(candidate)

    original_fstat = os.fstat

    def failing_open(*args: object, **kwargs: object) -> int:
        del args, kwargs
        raise fault("injected libc host open failure")

    def failing_fstat(descriptor: int) -> os.stat_result:
        nonlocal stat_calls
        if stage == "post-read-fstat":
            stat_calls += 1
            if stat_calls != 2:
                return original_fstat(descriptor)
        raise fault("injected libc host descriptor failure")

    if stage in {"path-lstat", "post-read-lstat"}:
        monkeypatch.setattr(Path, "lstat", failing_lstat)
    elif stage in {"parent-junction", "leaf-junction"}:
        monkeypatch.setattr(Path, "is_junction", failing_junction)
    elif stage == "open":
        monkeypatch.setattr(os, "open", failing_open)
    else:
        monkeypatch.setattr(os, "fstat", failing_fstat)
    with pytest.raises(c_libc.CLibcValidationError, match="read C libc") as error:
        _ = c_libc.load_document(path)
    assert type(error.value.__cause__) is fault


@pytest.mark.parametrize("fault", [OSError, ValueError, RuntimeError])
def test_guest_libc_fdopen_failure_releases_owned_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """No raw descriptor may survive a failed binary stream wrapper."""
    path = tmp_path / "libc.json"
    _ = path.write_bytes(LIBC_PATH.read_bytes())
    original_open = os.open
    original_fstat = os.fstat
    captured: list[int] = []

    def capture_open(
        file: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        descriptor = original_open(file, flags, mode, dir_fd=dir_fd)
        captured.append(descriptor)
        return descriptor

    def failing_fdopen(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise fault("injected libc fdopen failure")

    monkeypatch.setattr(os, "open", capture_open)
    monkeypatch.setattr(os, "fdopen", failing_fdopen)
    try:
        with pytest.raises(c_libc.CLibcValidationError, match="read C libc"):
            _ = c_libc.load_document(path)
    finally:
        leaked = [
            descriptor
            for descriptor in captured
            if _descriptor_open(descriptor, original_fstat)
        ]
        for descriptor in leaked:
            os.close(descriptor)
    assert captured
    assert not leaked


def _descriptor_open(descriptor: int, fstat: Callable[[int], os.stat_result]) -> bool:
    """Inspect an owned descriptor with the unpatched host stat operation."""
    try:
        _ = fstat(descriptor)
    except OSError:
        return False
    return True


def test_guest_libc_loader_rejects_same_byte_path_swap_during_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Matching descriptor bytes alone cannot certify the original pathname."""
    path = tmp_path / "libc.json"
    replacement = tmp_path / "replacement.json"
    content = LIBC_PATH.read_bytes()
    _ = path.write_bytes(content)
    _ = replacement.write_bytes(content)
    original_fstat = os.fstat
    inspections = 0

    def replacing_fstat(descriptor: int) -> os.stat_result:
        nonlocal inspections
        inspected = original_fstat(descriptor)
        inspections += 1
        if inspections == 2:
            os.replace(replacement, path)
        return inspected

    monkeypatch.setattr(os, "fstat", replacing_fstat)
    with pytest.raises(c_libc.CLibcValidationError, match="stable regular file"):
        _ = c_libc.load_document(path)
    assert inspections >= 2


def test_guest_libc_loader_rejects_parent_redirection_during_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post-read identity also rejects a newly symlinked parent directory."""
    parent = tmp_path / "original"
    parent.mkdir()
    path = parent / "libc.json"
    _ = path.write_bytes(LIBC_PATH.read_bytes())
    moved = tmp_path / "moved"
    original_fstat = os.fstat
    inspections = 0

    def redirecting_fstat(descriptor: int) -> os.stat_result:
        nonlocal inspections
        inspected = original_fstat(descriptor)
        inspections += 1
        if inspections == 2:
            parent.rename(moved)
            parent.symlink_to(moved, target_is_directory=True)
        return inspected

    monkeypatch.setattr(os, "fstat", redirecting_fstat)
    with pytest.raises(c_libc.CLibcValidationError, match="path must not redirect"):
        _ = c_libc.load_document(path)
    assert inspections >= 2


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
        MATH_SINCOS,
        MATH_TRANS_SPECIAL,
        ACCEPTED,
        ACCEPTED_MATH,
        ACCEPTED_SQRT,
        ACCEPTED_SINCOS,
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


def test_transcendental_special_cases_execute_without_libm(
    tmp_path: Path,
) -> None:
    """Resolve exact raw-bit edge cases without exposing transcendental libc."""
    _require_clang()
    executable = tmp_path / "transcendental-special"
    compiled = _run(
        [
            str(CLANG),
            *STRICT_C,
            f"-I{MATH_INTERNAL}",
            str(MATH_TRANS_SPECIAL),
            str(MATH_TRANS_HARNESS),
            "-o",
            str(executable),
        ],
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stderr

    completed = _run([str(executable)], ROOT)
    assert completed.returncode == 0, completed.stderr


def test_public_sincos_executes_without_host_libm(tmp_path: Path) -> None:
    """Execute public sine/cosine through special and numerical paths."""
    _require_clang()
    executable = tmp_path / "public-sincos"
    compiled = _run(
        [
            str(CLANG),
            *STRICT_C,
            f"-I{INCLUDE}",
            f"-I{MATH_INTERNAL}",
            str(MATH_TRANS_SPECIAL),
            str(MATH_SINCOS),
            str(MATH_SINCOS_HARNESS),
            "-o",
            str(executable),
        ],
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stderr
    completed = _run([str(executable)], ROOT)
    assert completed.returncode == 0, completed.stderr


def test_atan2_kernel_input_normalizes_without_floating_division(
    tmp_path: Path,
) -> None:
    """Normalize finite atan2 ratios without exposing the public routine."""
    _require_clang()
    executable = tmp_path / "atan2-kernel-input"
    compiled = _run(
        [
            str(CLANG),
            *STRICT_C,
            f"-I{MATH_INTERNAL}",
            str(MATH_TRANS_SPECIAL),
            str(MATH_ATAN2_INPUT_HARNESS),
            "-o",
            str(executable),
        ],
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stderr
    completed = _run([str(executable)], ROOT)
    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize(
    "text",
    [
        '{"kind":"TranslationUnitDecl","kind":"FunctionDecl"}',
        '{"inner":[{"id":"one","id":"two"}]}',
    ],
)
def test_libc_clang_ast_rejects_duplicate_json_evidence_keys(text: str) -> None:
    """Later duplicate fields cannot silently replace earlier AST evidence."""
    with pytest.raises(c_libc_source.LibcSourceError, match="duplicate.*AST"):
        _ = c_libc_source._parse_ast(text, ACCEPTED)


@pytest.mark.parametrize("number", ["NaN", "Infinity", "-Infinity"])
def test_libc_clang_ast_rejects_nonstandard_json_numbers(number: str) -> None:
    """Clang AST evidence must be strict JSON, not Python extensions."""
    with pytest.raises(c_libc_source.LibcSourceError, match="nonfinite.*AST"):
        _ = c_libc_source._parse_ast('{"number":' + number + "}", ACCEPTED)


@pytest.mark.parametrize("value", [None, b"{}", [], 10])
def test_libc_clang_ast_rejects_nontext_direct_input(value: object) -> None:
    """Only exact decoded host text may reach the AST JSON parser."""
    with pytest.raises(c_libc_source.LibcSourceError, match="AST JSON.*text"):
        _ = c_libc_source._parse_ast(cast("str", value), ACCEPTED)


@pytest.mark.parametrize(
    "text",
    [
        "{}",
        '{"kind":"FunctionDecl","id":"0x1","inner":[{}]}',
        '{"kind":"TranslationUnitDecl","inner":[{}]}',
        '{"kind":"TranslationUnitDecl","id":"0x1"}',
        '{"kind":"TranslationUnitDecl","id":"0x1","inner":[]}',
        '{"kind":"TranslationUnitDecl","id":"0x1","inner":[null]}',
        '{"kind":"TranslationUnitDecl","id":true,"inner":[{}]}',
    ],
)
def test_libc_clang_ast_requires_real_translation_unit_shape(text: str) -> None:
    """Empty or synthetic AST roots cannot be mistaken for clean source scans."""
    with pytest.raises(c_libc_source.LibcSourceError, match="AST root"):
        _ = c_libc_source._parse_ast(text, ACCEPTED)


def test_libc_clang_ast_empty_receipt_cannot_admit_forbidden_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A zero-exit process returning {} is not evidence of a clean C source."""
    monkeypatch.setattr(c_libc_source, "_require_clang", lambda _: None)
    monkeypatch.setattr(
        sp,
        "run",
        lambda *args, **kwargs: sp.CompletedProcess(
            args=[], returncode=0, stdout="{}", stderr=""
        ),
    )
    with pytest.raises(c_libc_source.LibcSourceError, match="AST root"):
        _ = c_libc_source._run_ast(ACCEPTED, _libc_test_ast_config())


@pytest.mark.parametrize("stage", ["definitions", "references"])
def test_libc_clang_ast_deep_nesting_fails_as_typed_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    """Very deep untrusted AST trees cannot leak Python recursion failures."""
    source = tmp_path / "source.c"
    _ = source.write_bytes(b"int guest(void) { return 0; }\n")
    config = _libc_test_ast_config()
    node: dict[str, object] = {}
    for _ in range(1500):
        node = {"inner": [node]}
    monkeypatch.setattr(c_libc_source, "_run_ast", lambda *args: node)
    if stage == "references":
        monkeypatch.setattr(
            c_libc_source, "_local_definition_ids", lambda *args: frozenset()
        )
    with pytest.raises(c_libc_source.LibcSourceError, match="AST depth"):
        _ = c_libc_source.analyze_source(
            source, clang=CLANG, abi=config.abi, libc=config.libc
        )


def _libc_test_ast_config() -> c_libc_source._AstConfig:
    """Provide canonical source AST configuration for isolated host tests."""
    return c_libc_source._AstConfig(
        clang=CLANG,
        abi=c_abi.canonical_projection(),
        libc=c_libc.canonical_projection(),
    )


def _run_libc_test_ast(stage: str) -> object:
    """Exercise the version or AST subprocess admission with one return type."""
    if stage == "version":
        return c_libc_source._clang_identity(CLANG)
    return c_libc_source._run_ast(ACCEPTED, _libc_test_ast_config())


@pytest.mark.parametrize("stage", ["version", "ast"])
@pytest.mark.parametrize(
    "fault", [OSError, ValueError, RuntimeError, TypeError, AttributeError]
)
def test_libc_clang_process_host_faults_are_typed(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    fault: type[Exception],
) -> None:
    """Unavailable host process calls must not leak their implementation faults."""

    def failing_run(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise fault("injected guest libc Clang transport failure")

    monkeypatch.setattr(sp, "run", failing_run)
    if stage == "ast":
        monkeypatch.setattr(c_libc_source, "_require_clang", lambda _: None)
    with pytest.raises(c_libc_source.LibcSourceError, match="Clang") as failure:
        _ = _run_libc_test_ast(stage)
    assert type(failure.value.__cause__) is fault


@pytest.mark.parametrize("stage", ["version", "ast"])
@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("returncode", False),
        ("returncode", 0.0),
        ("returncode", None),
        ("stdout", None),
        ("stdout", b"not text"),
        ("stderr", None),
        ("stderr", b"not text"),
    ],
)
def test_libc_clang_rejects_malformed_process_receipts(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    field: str,
    invalid: object,
) -> None:
    """A fake exit zero, missing text or byte output cannot certify Clang."""
    values: dict[str, object] = {
        "returncode": 0,
        "stdout": "clang version 22.1.8" if stage == "version" else "{}",
        "stderr": "",
    }
    values[field] = invalid
    completed = sp.CompletedProcess[str](
        args=[],
        returncode=cast("int", values["returncode"]),
        stdout=cast("str", values["stdout"]),
        stderr=cast("str", values["stderr"]),
    )
    monkeypatch.setattr(sp, "run", lambda *args, **kwargs: completed)
    if stage == "ast":
        monkeypatch.setattr(c_libc_source, "_require_clang", lambda _: None)
    with pytest.raises(c_libc_source.LibcSourceError, match="malformed Clang"):
        _ = _run_libc_test_ast(stage)


@pytest.mark.parametrize("stage", ["version", "ast"])
@pytest.mark.parametrize("response", [None, False, {}, object()])
def test_libc_clang_rejects_nonprocess_receipt_objects(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    response: object,
) -> None:
    """No malformed host object may impersonate a completed Clang process."""
    monkeypatch.setattr(sp, "run", lambda *args, **kwargs: response)
    if stage == "ast":
        monkeypatch.setattr(c_libc_source, "_require_clang", lambda _: None)
    with pytest.raises(c_libc_source.LibcSourceError, match="malformed Clang"):
        _ = _run_libc_test_ast(stage)


@pytest.mark.parametrize("fault", [OSError, ValueError, RuntimeError])
def test_libc_source_fdopen_failure_closes_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """Failed guest source wrappers must not leak the raw opened descriptor."""
    source = tmp_path / "source.c"
    _ = source.write_bytes(b"int guest(void) { return 0; }\n")
    original_open = os.open
    original_fstat = os.fstat
    captured: list[int] = []

    def tracking_open(
        file: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        descriptor = original_open(file, flags, mode, dir_fd=dir_fd)
        captured.append(descriptor)
        return descriptor

    def failing_fdopen(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise fault("injected libc source fdopen failure")

    monkeypatch.setattr(os, "open", tracking_open)
    monkeypatch.setattr(os, "fdopen", failing_fdopen)
    try:
        with pytest.raises(c_libc_source.LibcSourceError, match="source"):
            _ = c_libc_source._source_snapshot(source)
    finally:
        leaked = [
            descriptor
            for descriptor in captured
            if _descriptor_open(descriptor, original_fstat)
        ]
        for descriptor in leaked:
            os.close(descriptor)
    assert captured
    assert not leaked


@pytest.mark.parametrize("stage", ["source", "clang"])
@pytest.mark.parametrize("fault", [OSError, ValueError, RuntimeError])
def test_libc_source_resolve_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    fault: type[Exception],
) -> None:
    """Source/Clang resolution failures cannot bypass the admission boundary."""
    source = tmp_path / "source.c"
    _ = source.write_bytes(b"int guest(void) { return 0; }\n")
    config = _libc_test_ast_config()
    target = source if stage == "source" else CLANG
    original_resolve = Path.resolve

    def failing_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == target:
            raise fault("injected libc source resolution failure")
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", failing_resolve)
    with pytest.raises(c_libc_source.LibcSourceError, match="resolve") as error:
        _ = c_libc_source.analyze_source(
            source, clang=CLANG, abi=config.abi, libc=config.libc
        )
    assert type(error.value.__cause__) is fault


@pytest.mark.parametrize("fault", [OSError, ValueError, RuntimeError])
def test_libc_source_clang_status_faults_are_typed(
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """Clang preflight must type even unexpected filesystem status failures."""
    original_is_file = Path.is_file

    def failing_is_file(path: Path) -> bool:
        if path == CLANG:
            raise fault("injected Clang file status failure")
        return original_is_file(path)

    monkeypatch.setattr(Path, "is_file", failing_is_file)
    with pytest.raises(c_libc_source.LibcSourceError, match="Clang") as error:
        c_libc_source._require_clang(CLANG)
    assert type(error.value.__cause__) is fault


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


@pytest.mark.parametrize(
    ("macro", "invocation", "header_contents"),
    [
        (
            "#define CALL_SYSTEM(arg) system(arg)\n",
            'CALL_SYSTEM("ignored")',
            None,
        ),
        (
            '#include "macro-system.h"\n',
            'CALL_SYSTEM("ignored")',
            "#define CALL_SYSTEM(arg) system(arg)\n",
        ),
        (
            """#define SYSTEM_ALIAS system
#define CALL_SYSTEM(arg) SYSTEM_ALIAS(arg)
""",
            'CALL_SYSTEM("ignored")',
            None,
        ),
        (
            "#define APPLY(fn, arg) fn(arg)\n",
            'APPLY(system, "ignored")',
            None,
        ),
    ],
)
def test_libc_macro_expansion_rejects_forbidden_call_at_invocation(
    tmp_path: Path,
    *,
    macro: str,
    invocation: str,
    header_contents: str | None,
) -> None:
    """Macro-expanded host calls cannot escape source-located libc admission."""
    _require_clang()
    source = tmp_path / "macro-system.c"
    if header_contents is not None:
        _ = (tmp_path / "macro-system.h").write_text(header_contents, encoding="utf-8")
    text = (
        "extern int system(const char *command);\n"
        + macro
        + f"int probe(void) {{ return {invocation}; }}\n"
    )
    _ = source.write_text(text, encoding="utf-8")

    diagnostics = c_libc_source.analyze_source(source)

    assert len(diagnostics) == 1
    assert diagnostics[0].code == c_libc_source.DIAGNOSTIC_FORBIDDEN
    assert diagnostics[0].path == source.resolve()
    assert diagnostics[0].line == text.count("\n")
    assert diagnostics[0].column == text.splitlines()[-1].index(invocation) + 1
    assert SYSTEM_ROUTINE in diagnostics[0].message


def test_libc_macro_expansion_rejects_unavailable_malloc(
    tmp_path: Path,
) -> None:
    """Macro expansion cannot turn an unavailable allocator into guest libc."""
    _require_clang()
    source = tmp_path / "macro-malloc.c"
    content = """#include <stdlib.h>
#define MAKE() malloc(8)
void *probe(void) { return MAKE(); }
"""
    _ = source.write_text(content, encoding="utf-8")
    diagnostics = c_libc_source.analyze_source(source)
    assert len(diagnostics) == 1
    assert diagnostics[0].code == c_libc_source.DIAGNOSTIC_UNAVAILABLE
    assert diagnostics[0].line == len(content.splitlines())
    assert diagnostics[0].column == content.splitlines()[-1].index("MAKE()") + 1
    assert MALLOC_ROUTINE in diagnostics[0].message


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("offset", True),
        ("offset", -1),
        ("offset", 1_000_000),
        ("file", "foreign-header.h"),
        ("line", 9_999),
        ("col", 9_999),
    ],
)
def test_libc_macro_expansion_rejects_unbound_location_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    field: str,
    invalid: object,
) -> None:
    """Malformed location receipts cannot certify a forbidden reference."""
    source = tmp_path / "source.c"
    _ = source.write_text(
        """extern int system(const char *);
int probe(void) { return system("ignored"); }
""",
        encoding="utf-8",
    )
    expansion: c_libc_source.JsonObject = {
        "offset": 39,
        "file": str(source),
    }
    expansion[field] = cast("c_libc_source.JsonValue", invalid)
    ast: c_libc_source.JsonObject = {
        "kind": "TranslationUnitDecl",
        "id": "unit",
        "inner": [
            {
                "kind": "DeclRefExpr",
                "range": {
                    "begin": {
                        "spellingLoc": {"offset": 0},
                        "expansionLoc": expansion,
                    }
                },
                "referencedDecl": {
                    "id": "external",
                    "kind": "FunctionDecl",
                    "name": "system",
                },
            }
        ],
    }

    def fake_ast(source_path: Path, config: object) -> c_libc_source.JsonObject:
        _ = source_path, config
        return ast

    monkeypatch.setattr(c_libc_source, "_run_ast", fake_ast)
    with pytest.raises(
        c_libc_source.LibcSourceError,
        match="Clang macro expansion source location",
    ):
        _ = c_libc_source.analyze_source(source)


def test_libc_macro_expansion_preserves_user_function_definition(
    tmp_path: Path,
) -> None:
    """A source-owned function remains legal through macro invocation."""
    _require_clang()
    source = tmp_path / "macro-user-system.c"
    _ = source.write_text(
        """static int system(const char *s) { return s[0] == 0; }
#define CALL_SYSTEM(arg) system(arg)
int probe(void) { return CALL_SYSTEM("ignored"); }
""",
        encoding="utf-8",
    )
    assert c_libc_source.analyze_source(source) == ()


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
        line.split()[-1] for line in completed.stdout.splitlines() if line.split()
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
    for source in (
        MEMORY,
        STRING,
        MATH_EXACT,
        MATH_SQRT,
        MATH_TRANS_SPECIAL,
        MATH_SINCOS,
        HARNESS,
    ):
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
    for accepted_source in (
        ACCEPTED,
        ACCEPTED_MATH,
        ACCEPTED_SQRT,
        ACCEPTED_SINCOS,
    ):
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


def test_libc_preflight_rejects_source_rewrite_during_ast(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guest libc AST must not refer to bytes changed after snapshot."""
    source = tmp_path / "rewritten.c"
    _ = source.write_text("int one;\n", encoding="utf-8")

    def rewrite_source(_path: Path, _config: object) -> object:
        _ = (_path, _config)
        _ = source.write_text("int two;\n", encoding="utf-8")
        return {}

    monkeypatch.setattr(c_libc_source, "_run_ast", rewrite_source)
    with pytest.raises(c_libc_source.LibcSourceError, match="changed"):
        _ = c_libc_source.analyze_source(source)


def test_libc_preflight_rejects_same_byte_inode_swap_during_ast(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same-byte regular source substitution invalidates the libc AST."""
    source = tmp_path / "swapped.c"
    content = "int one;\n"
    _ = source.write_text(content, encoding="utf-8")

    def swap_source(_path: Path, _config: object) -> object:
        _ = (_path, _config)
        source.unlink()
        _ = source.write_text(content, encoding="utf-8")
        return {}

    monkeypatch.setattr(c_libc_source, "_run_ast", swap_source)
    with pytest.raises(c_libc_source.LibcSourceError, match="changed"):
        _ = c_libc_source.analyze_source(source)


@pytest.mark.parametrize("phase", ["admitted", "opened", "after", "visible"])
def test_libc_source_native_stat_receipts_reject_foreign_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    """Guest-C source status values must be native before field inspection."""
    source = tmp_path / "source.c"
    _ = source.write_bytes(b"int guest(void) { return 0; }\n")

    class ForeignStat:
        @override
        def __getattribute__(self, name: str) -> object:
            del self, name
            raise AssertionError("foreign guest source stat hook executed")

    original_lstat = Path.lstat
    original_fstat = os.fstat
    lstat_calls = 0
    fstat_calls = 0

    def forged_lstat(path: Path) -> os.stat_result:
        nonlocal lstat_calls
        if path == source:
            lstat_calls += 1
            if (phase == "admitted" and lstat_calls == 1) or (
                phase == "visible" and lstat_calls == 2
            ):
                return cast("os.stat_result", cast("object", ForeignStat()))
        return original_lstat(path)

    def forged_fstat(descriptor: int) -> os.stat_result:
        nonlocal fstat_calls
        fstat_calls += 1
        if (phase == "opened" and fstat_calls == 1) or (
            phase == "after" and fstat_calls == 2
        ):
            return cast("os.stat_result", cast("object", ForeignStat()))
        return original_fstat(descriptor)

    monkeypatch.setattr(Path, "lstat", forged_lstat)
    monkeypatch.setattr(os, "fstat", forged_fstat)
    with pytest.raises(c_libc_source.LibcSourceError, match="native stat"):
        _ = c_libc_source._source_snapshot(source)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("receipt", [True, False, -1, 3.0])
def test_libc_source_native_open_descriptor_rejects_foreign_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """Fake open values never own file descriptors or close stdin/stdout."""
    source = tmp_path / "source.c"
    _ = source.write_bytes(b"int guest(void) { return 0; }\n")
    original_open = os.open

    def forged_open(path: Path, flags: int) -> int:
        if path == source:
            return cast("int", receipt)
        return original_open(path, flags)

    monkeypatch.setattr(os, "open", forged_open)
    with pytest.raises(c_libc_source.LibcSourceError, match="native descriptor"):
        _ = c_libc_source._source_snapshot(source)  # pyright: ignore[reportPrivateUsage]


class _LibcSourceForgedStream:
    """Own a real descriptor while returning host-controlled fake values."""

    def __init__(
        self, stream: BinaryIO, payload: object, descriptor: object = None
    ) -> None:
        self.stream: BinaryIO = stream
        self.payload: object = payload
        self.descriptor: object = descriptor

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        del args
        self.stream.close()

    def fileno(self) -> int:
        return cast(
            "int",
            self.descriptor if self.descriptor is not None else self.stream.fileno(),
        )

    def read(self) -> bytes:
        return cast("bytes", self.payload)


def test_libc_source_rejects_forged_same_extent_stream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Equal-length forged source bytes cannot certify a C input snapshot."""
    path = tmp_path / "source.c"
    native = b"int main(void) { return 0; }\n"
    _ = path.write_bytes(native)
    forged = b"x" * len(native)
    native_fdopen = os.fdopen
    descriptor_receipts: list[int] = []
    hooks: list[str] = []

    class ForgedReader:
        def __init__(self, descriptor: int) -> None:
            self.descriptor: int = descriptor
            descriptor_receipts.append(descriptor)

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            os.close(self.descriptor)

        def fileno(self) -> int:
            hooks.append("fileno")
            return self.descriptor

        def read(self) -> bytes:
            hooks.append("read")
            return forged

    def fake_fdopen(descriptor: int, mode: str) -> object:
        if mode == "rb":
            return ForgedReader(descriptor)
        return native_fdopen(descriptor, mode)

    monkeypatch.setattr(os, "fdopen", fake_fdopen)
    with pytest.raises(c_libc_source.LibcSourceError, match="native stream"):
        _ = c_libc_source._source_snapshot(path)  # pyright: ignore[reportPrivateUsage]
    assert not hooks
    assert len(descriptor_receipts) == 1
    with pytest.raises(OSError):
        _ = os.fstat(descriptor_receipts[0])


def test_libc_source_rejects_native_stream_of_duplicate_fd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A native buffered reader of a duplicate is not our open descriptor."""
    path = tmp_path / "source.c"
    _ = path.write_bytes(b"int main(void) { return 0; }\n")
    native_fdopen = os.fdopen
    originals: list[int] = []
    borrowed: list[BinaryIO] = []

    def fake_fdopen(descriptor: int, mode: str) -> BinaryIO:
        originals.append(descriptor)
        stream = cast("BinaryIO", native_fdopen(os.dup(descriptor), mode))
        borrowed.append(stream)
        return stream

    monkeypatch.setattr(os, "fdopen", fake_fdopen)
    try:
        with pytest.raises(c_libc_source.LibcSourceError, match="native stream"):
            _ = c_libc_source._source_snapshot(path)  # pyright: ignore[reportPrivateUsage]
        with pytest.raises(OSError):
            _ = os.fstat(originals[0])
    finally:
        for stream in reversed(borrowed):
            stream.close()
        for descriptor in originals:
            try:
                os.close(descriptor)
            except OSError:
                pass


@pytest.mark.parametrize("kind", ["str", "list", "subclass"])
def test_libc_source_native_stream_bytes_reject_foreign_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """A foreign reader is rejected before its byte-length hook runs."""
    source = tmp_path / "source.c"
    raw = b"int guest(void) { return 0; }\n"
    _ = source.write_bytes(raw)
    original_fdopen = os.fdopen
    borrowed: list[BinaryIO] = []

    class ForeignBytes(bytes):
        @override
        def __len__(self) -> int:
            raise AssertionError("foreign guest source length hook executed")

    payloads: dict[str, object] = {
        "str": raw.decode(),
        "list": list(raw),
        "subclass": ForeignBytes(raw),
    }

    def forged_fdopen(fd: int, mode: str) -> BinaryIO:
        stream = cast("BinaryIO", original_fdopen(os.dup(fd), mode))
        borrowed.append(stream)
        return cast(
            "BinaryIO", cast("object", _LibcSourceForgedStream(stream, payloads[kind]))
        )

    monkeypatch.setattr(os, "fdopen", forged_fdopen)
    try:
        with pytest.raises(c_libc_source.LibcSourceError, match="native stream"):
            _ = c_libc_source._source_snapshot(source)  # pyright: ignore[reportPrivateUsage]
    finally:
        for stream in borrowed:
            stream.close()


@pytest.mark.parametrize("receipt", [True, -1, 3.0])
def test_libc_source_native_stream_descriptor_rejects_foreign_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """A foreign source reader cannot certify an opened inode."""
    source = tmp_path / "source.c"
    raw = b"int guest(void) { return 0; }\n"
    _ = source.write_bytes(raw)
    original_fdopen = os.fdopen
    borrowed: list[BinaryIO] = []

    def forged_fdopen(fd: int, mode: str) -> BinaryIO:
        stream = cast("BinaryIO", original_fdopen(os.dup(fd), mode))
        borrowed.append(stream)
        return cast(
            "BinaryIO", cast("object", _LibcSourceForgedStream(stream, raw, receipt))
        )

    monkeypatch.setattr(os, "fdopen", forged_fdopen)
    try:
        with pytest.raises(c_libc_source.LibcSourceError, match="native stream"):
            _ = c_libc_source._source_snapshot(source)  # pyright: ignore[reportPrivateUsage]
    finally:
        for stream in borrowed:
            stream.close()


@pytest.mark.parametrize(
    "fault_type", [c_libc_source.LibcSourceError, c_abi.CAbiValidationError]
)
def test_libc_source_cli_does_not_format_foreign_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fault_type: type[Exception],
) -> None:
    """CLI failures never execute untrusted exception subclass formatters."""

    class ForeignError(fault_type):
        @override
        def __str__(self) -> str:
            raise AssertionError("foreign guest libc CLI hook executed")

    fault = ForeignError("unsafe host detail")

    def fail_abi() -> None:
        raise fault

    monkeypatch.setattr(c_abi, "canonical_projection", fail_abi)
    monkeypatch.setattr(sys, "argv", ["c_libc_source", "source.c"])
    assert c_libc_source.main() == 2
    output = capsys.readouterr()
    assert "ForeignError" in output.err
    assert not output.out


@pytest.mark.parametrize("receipt", [0, 1, object()])
def test_libc_clang_status_rejects_foreign_boolean_receipts(
    monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """Clang executable presence cannot be inferred from truthiness hooks."""
    original_is_file = Path.is_file

    class ForeignVerdict:
        def __bool__(self) -> bool:
            raise AssertionError("foreign Clang status truthiness hook executed")

    verdict = ForeignVerdict() if type(receipt) is object else receipt

    def forged_is_file(path: Path) -> bool:
        if path == CLANG:
            return cast("bool", verdict)
        return original_is_file(path)

    def known_clang_identity(_clang: Path) -> str:
        return "clang version 22.1.8"

    monkeypatch.setattr(Path, "is_file", forged_is_file)
    monkeypatch.setattr(c_libc_source, "_clang_identity", known_clang_identity)
    with pytest.raises(c_libc_source.LibcSourceError, match="native status"):
        c_libc_source._require_clang(CLANG)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("receipt", [True, -1, 3.0])
def test_libc_stream_descriptor_after_read_requires_native_int(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """A non-native source reader cannot perform post-read identity checks."""
    source = tmp_path / "source.c"
    raw = b"int guest(void) { return 0; }\n"
    _ = source.write_bytes(raw)
    original_fdopen = os.fdopen
    borrowed: list[BinaryIO] = []

    class ForgedSecondDescriptor(_LibcSourceForgedStream):
        def __init__(self, stream: BinaryIO) -> None:
            super().__init__(stream, raw)
            self.calls: int = 0

        @override
        def fileno(self) -> int:
            self.calls += 1
            return cast("int", receipt) if self.calls == 2 else self.stream.fileno()

    def forged_fdopen(fd: int, mode: str) -> BinaryIO:
        stream = cast("BinaryIO", original_fdopen(os.dup(fd), mode))
        borrowed.append(stream)
        return cast("BinaryIO", cast("object", ForgedSecondDescriptor(stream)))

    monkeypatch.setattr(os, "fdopen", forged_fdopen)
    try:
        with pytest.raises(c_libc_source.LibcSourceError, match="native stream"):
            _ = c_libc_source._source_snapshot(source)  # pyright: ignore[reportPrivateUsage]
    finally:
        for stream in borrowed:
            stream.close()


@pytest.mark.parametrize("phase", ["admitted", "opened", "after", "visible"])
def test_libc_authority_foreign_stat_receipts_never_execute_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    """Authority stat identity cannot invoke forged host field accessors."""
    path = tmp_path / "libc.json"
    _ = path.write_bytes(b"{}")

    class ForeignStat:
        @override
        def __getattribute__(self, name: str) -> object:
            del self, name
            raise AssertionError("foreign libc authority stat hook executed")

    native_lstat = Path.lstat
    native_fstat = os.fstat
    lstat_calls = 0
    fstat_calls = 0

    def forged_lstat(target: Path) -> os.stat_result:
        nonlocal lstat_calls
        if target == path:
            lstat_calls += 1
            if (phase == "admitted" and lstat_calls == 1) or (
                phase == "visible" and lstat_calls == 2
            ):
                return cast("os.stat_result", cast("object", ForeignStat()))
        return native_lstat(target)

    def forged_fstat(fd: int) -> os.stat_result:
        nonlocal fstat_calls
        fstat_calls += 1
        if (phase == "opened" and fstat_calls == 1) or (
            phase == "after" and fstat_calls == 2
        ):
            return cast("os.stat_result", cast("object", ForeignStat()))
        return native_fstat(fd)

    monkeypatch.setattr(Path, "lstat", forged_lstat)
    monkeypatch.setattr(os, "fstat", forged_fstat)
    with pytest.raises(c_libc.CLibcValidationError, match="native stat"):
        _ = c_libc.load_document(path)


@pytest.mark.parametrize(
    "phase", ["parent_symlink", "parent_junction", "leaf_symlink", "leaf_junction"]
)
@pytest.mark.parametrize("receipt", [0, 1, object()])
def test_libc_authority_foreign_redirect_receipts_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str, receipt: object
) -> None:
    """Parent and leaf redirect verdicts must be exact host booleans."""
    path = tmp_path / "libc.json"
    _ = path.write_bytes(b"{}")
    target = path if phase.startswith("leaf") else path.parent
    is_symlink = phase.endswith("symlink")
    native = Path.is_symlink if is_symlink else Path.is_junction

    class ForeignVerdict:
        def __bool__(self) -> bool:
            raise AssertionError("foreign libc redirect truthiness hook executed")

    verdict = ForeignVerdict() if type(receipt) is object else receipt

    def forged_redirect(candidate: Path) -> bool:
        if candidate == target:
            return cast("bool", verdict)
        return native(candidate)

    monkeypatch.setattr(
        Path, "is_symlink" if is_symlink else "is_junction", forged_redirect
    )
    with pytest.raises(c_libc.CLibcValidationError, match="native redirect"):
        _ = c_libc.load_document(path)


@pytest.mark.parametrize("receipt", [-1, 3.0])
def test_libc_authority_foreign_open_descriptor_rejected_before_ownership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """Invalid open returns cannot be wrapped as owned file descriptors."""
    path = tmp_path / "libc.json"
    _ = path.write_bytes(b"{}")
    native_open = os.open

    def forged_open(candidate: Path, flags: int) -> int:
        if candidate == path:
            return cast("int", receipt)
        return native_open(candidate, flags)

    monkeypatch.setattr(os, "open", forged_open)
    with pytest.raises(c_libc.CLibcValidationError, match="native descriptor"):
        _ = c_libc.load_document(path)


@pytest.mark.parametrize("receipt", [True, -1, 3.0])
def test_libc_authority_foreign_stream_descriptor_rejected_before_stat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """Untrusted fileno receipts cannot validate the authority inode."""
    path = tmp_path / "libc.json"
    _ = path.write_bytes(b"{}")
    native_fdopen = os.fdopen

    class ForgedFileno(_LibcSourceForgedStream):
        @override
        def read(self, *args: object) -> bytes:
            del args
            return b"{}"

    def forged_fdopen(fd: int, mode: str) -> BinaryIO:
        stream = cast("BinaryIO", native_fdopen(fd, mode))
        return cast("BinaryIO", cast("object", ForgedFileno(stream, b"{}", receipt)))

    monkeypatch.setattr(os, "fdopen", forged_fdopen)
    with pytest.raises(c_libc.CLibcValidationError, match="native descriptor"):
        _ = c_libc.load_document(path)


@pytest.mark.parametrize(
    "fault_type", [c_libc.CLibcValidationError, c_abi.CAbiValidationError]
)
def test_libc_authority_cli_does_not_format_foreign_error_subclasses(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fault_type: type[Exception],
) -> None:
    """An exception subclass cannot inject untrusted error formatting."""

    class ForeignError(fault_type):
        @override
        def __str__(self) -> str:
            raise AssertionError("foreign libc authority CLI hook executed")

    def fail_projection() -> None:
        raise ForeignError("untrusted diagnostic")

    monkeypatch.setattr(c_libc, "canonical_projection", fail_projection)
    assert c_libc.main() == 1
    assert "ForeignError" in capsys.readouterr().err


@pytest.mark.parametrize(
    "case", ("partial", "foreign-count", "write-fault", "flush-fault", "foreign-flush")
)
def test_libc_authority_cli_requires_delivered_summary(
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    """A valid contract cannot certify success with an invalid output receipt."""

    class FakeOutput:
        def write(self, message: str) -> object:
            if case == "partial":
                return len(message) - 1
            if case == "foreign-count":
                return True
            if case == "write-fault":
                raise OSError("output unavailable")
            return len(message)

        def flush(self) -> object:
            if case == "flush-fault":
                raise OSError("flush unavailable")
            if case == "foreign-flush":
                return False
            return None

    projection = c_libc.canonical_projection()
    monkeypatch.setattr(c_libc, "canonical_projection", lambda: projection)
    monkeypatch.setattr(sys, "stdout", cast("TextIO", cast("object", FakeOutput())))
    assert c_libc.main() == 1


def test_libc_authority_cli_flushes_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A valid contract emits and flushes exactly one summary record."""

    class CapturingOutput:
        messages: list[str]
        flushes: int

        def __init__(self) -> None:
            self.messages = []
            self.flushes = 0

        def write(self, message: str) -> int:
            self.messages.append(message)
            return len(message)

        def flush(self) -> None:
            self.flushes += 1

    projection = c_libc.canonical_projection()
    output = CapturingOutput()
    monkeypatch.setattr(c_libc, "canonical_projection", lambda: projection)
    monkeypatch.setattr(sys, "stdout", cast("TextIO", cast("object", output)))
    assert c_libc.main() == 0
    assert output.messages == [
        f"C libc contract ready: {projection.libc_id} ({projection.abi_id})\n"
    ]
    assert output.flushes == 1


def test_libc_authority_cli_failed_stderr_retains_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failure exit remains nonzero when the diagnostic sink fails."""

    class FailingStderr:
        def write(self, _message: str) -> None:
            raise OSError("diagnostic unavailable")

    def rejected_contract() -> None:
        raise c_libc.CLibcValidationError("invalid libc")

    monkeypatch.setattr(c_libc, "canonical_projection", rejected_contract)
    monkeypatch.setattr(sys, "stderr", cast("TextIO", cast("object", FailingStderr())))
    assert c_libc.main() == 1


@pytest.mark.parametrize("receipt", [True, False])
def test_libc_authority_boolean_descriptor_rejected_without_wrapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipt: bool
) -> None:
    """Boolean file descriptors must not accidentally consume stdio."""
    path = tmp_path / "libc.json"
    _ = path.write_bytes(b"{}")
    native_open = os.open

    def forged_open(candidate: Path, flags: int) -> int:
        if candidate == path:
            return cast("int", receipt)
        return native_open(candidate, flags)

    monkeypatch.setattr(os, "open", forged_open)
    with pytest.raises(c_libc.CLibcValidationError, match="native descriptor"):
        _ = c_libc.load_document(path)


@pytest.mark.parametrize("phase", ["opened", "after"])
def test_libc_authority_stream_descriptor_must_match_owned_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    """A foreign stream cannot certify its bytes with a different native fd."""
    path = tmp_path / "libc.json"
    _ = path.write_bytes(b"{}")
    native_fdopen = os.fdopen

    class SwappedDescriptorStream(_LibcSourceForgedStream):
        def __init__(self, wrapped: BinaryIO) -> None:
            super().__init__(wrapped, b"{}")
            self.calls: int = 0

        @override
        def fileno(self) -> int:
            self.calls += 1
            if (phase == "opened" and self.calls == 1) or (
                phase == "after" and self.calls == 2
            ):
                return self.stream.fileno() + 1000
            return self.stream.fileno()

        @override
        def read(self, *args: object) -> bytes:
            del args
            return b"{}"

    def forged_fdopen(fd: int, mode: str) -> BinaryIO:
        wrapped = cast("BinaryIO", native_fdopen(fd, mode))
        return cast("BinaryIO", cast("object", SwappedDescriptorStream(wrapped)))

    monkeypatch.setattr(os, "fdopen", forged_fdopen)
    with pytest.raises(c_libc.CLibcValidationError, match="stream descriptor"):
        _ = c_libc.load_document(path)


def test_libc_authority_does_not_format_foreign_utf8_decoder_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Direct loader faults preserve decoder cause but not subclass formatting."""

    class ForeignUnicodeFault(UnicodeDecodeError):
        @override
        def __str__(self) -> str:
            raise AssertionError("foreign libc decoder formatter executed")

    fault = ForeignUnicodeFault("utf-8", b"\xff", 0, 1, "unsafe detail")

    class ForeignBytes(bytes):
        @override
        def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
            del encoding, errors
            raise fault

    def forged_read(_path: Path) -> bytes:
        return ForeignBytes(b"{}")

    monkeypatch.setattr(c_libc, "_read_regular_bytes", forged_read)
    with pytest.raises(
        c_libc.CLibcValidationError, match="ForeignUnicodeFault"
    ) as error:
        _ = c_libc.load_document(tmp_path / "libc.json")
    assert error.value.__cause__ is fault
