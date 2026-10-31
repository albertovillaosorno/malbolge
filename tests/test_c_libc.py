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
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from typing import TYPE_CHECKING
from typing import cast
from typing import override

import pytest

from scripts.validate import c_abi
from scripts.validate import c_libc
from scripts.validate import c_libc_source

if TYPE_CHECKING:
    from collections.abc import Callable

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
VALIDATOR = (
    ROOT / "src/automation/repository/composition/scripts/validate/main.py"
)
WINDOWS_OS_NAME = "nt"
LOADER_SYMLINK = "symlink"
LOADER_DIRECTORY = "directory"
LOADER_FIFO = "fifo"
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
})
EXPECTED_UNAVAILABLE = frozenset({
    "atan2",
    "calloc",
    "free",
    "getchar",
    "malloc",
    "putchar",
    "realloc",
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
        _ = c_libc_source._parse_ast('{"number":' + number + '}', ACCEPTED)


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
