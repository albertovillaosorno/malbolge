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
#   - Regression evidence for the canonical deterministic guest-C ABI.
# - Must-Not:
#   - Treat native host ABI behavior as guest authority or claim C lowering.
# - Allows:
#   - Inputs: canonical ABI JSON, pinned Clang, and explicit tidy fixtures.
#   - Outputs: deterministic ABI/schema/source-preflight test results.
#   - Side effects: pinned Clang and clang-tidy subprocesses in test state only.
# - Split-When:
#   - Split when another ABI version gains an independent fixture corpus.
# - Merge-When:
#   - Merge when another suite owns the exact same ABI conformance evidence.
# - Summary:
#   - Locks malbolge-c32-v1 data layout and ABI source diagnostics.
# - Description:
#   - Exercises schema closure, frontend projection, and accept/reject fixtures.
# - Usage:
#   - Collected by the repository Python test suite.
# - Defaults:
#   - Missing pinned LLVM skips executable projection checks; host ABI is never
#     substituted.
#

"""Regression tests for the canonical deterministic guest-C ABI."""

from __future__ import annotations

import json
import os
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from pathlib import Path
from typing import BinaryIO, TextIO, cast

import pytest

from scripts.validate import c_abi, c_abi_source
from scripts.validate import main as manual_validator

ROOT = Path(__file__).resolve().parents[1]
ABI_PATH = ROOT / "docs/technical/specification/c-abi-v1.json"
PROFILE_PATH = ROOT / "malbolge.json"
ABI_CONTRACT_DOC = (
    ROOT / "docs/technical/compiler/c-profile" / "deterministic-c-to-malbolge-abi.md"
)
ACCEPTED = ROOT / "tests/tidy/accepted"
REJECTED = ROOT / "tests/tidy/rejected"
CLANG_TIDY = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang-tidy.bin"
VALIDATOR = ROOT / "src/automation/repository/composition/scripts/validate/main.py"
VALIDATOR_CONFIGURATION_ERROR = 2
WRONG_TIDY_VERSION = "clang-tidy must report LLVM 22.1.8"
EXPECTED_REJECTIONS = {
    "abi_address_space.c": c_abi_source.DIAGNOSTIC_ADDRESS_SPACE,
    "abi_bit_field.c": c_abi_source.DIAGNOSTIC_BIT_FIELD,
    "abi_bit_int.c": c_abi_source.DIAGNOSTIC_BIT_INT,
    "abi_extended_alignment.c": c_abi_source.DIAGNOSTIC_ALIGNMENT,
    "abi_int128_extension.c": c_abi_source.DIAGNOSTIC_INT128,
    "abi_packed_attribute.c": c_abi_source.DIAGNOSTIC_PACKED,
    "abi_packed_field.c": c_abi_source.DIAGNOSTIC_PACKED,
    "abi_pragma_pack.c": c_abi_source.DIAGNOSTIC_PRAGMA_PACK,
    "abi_vector_extension.c": c_abi_source.DIAGNOSTIC_VECTOR,
}


def _canonical_text() -> str:
    return ABI_PATH.read_text(encoding="utf-8")


def _require_llvm() -> None:
    if not c_abi_source.PINNED_CLANG.is_file():
        pytest.skip("repository-pinned Clang is unavailable")


def test_canonical_abi_is_closed_and_bound_to_current_profile() -> None:
    """The tracked v1 authority validates and selects current Malbolge."""
    projection = c_abi.canonical_projection()
    assert projection.abi_id == c_abi.ABI_ID
    assert projection.target_profile == c_abi.TARGET_PROFILE
    assert projection.clang_target == c_abi.CLANG_TARGET
    assert projection.pointer_bits == c_abi.POINTER_BITS
    assert projection.max_alignment == c_abi.MAX_ALIGNMENT
    assert projection.stack_alignment == c_abi.STACK_ALIGNMENT


def test_c_abi_contract_tracks_current_profile_geometry() -> None:
    """The ABI prose consumes current geometry instead of freezing old N14."""
    profile_text = PROFILE_PATH.read_text(encoding="utf-8")
    profile = cast("dict[str, object]", json.loads(profile_text))
    current_name = cast("str", profile["current_profile"])
    profiles = cast("dict[str, object]", profile["profiles"])
    current = cast("dict[str, object]", profiles[current_name])
    word = cast("dict[str, object]", current["word"])
    memory = cast("dict[str, object]", current["memory"])
    semantics = cast("dict[str, object]", current["semantics"])
    contract = ABI_CONTRACT_DOC.read_text(encoding="utf-8")
    assert f"{word['trits']}-trit Malbolge words" in contract
    assert f"{memory['words']:,} words" in contract
    assert f"EOF word {semantics['eof_word']:,}" in contract


def test_duplicate_abi_keys_fail_closed() -> None:
    """Duplicate JSON keys cannot silently replace ABI policy."""
    with pytest.raises(c_abi.CAbiValidationError, match="duplicate JSON key"):
        _ = c_abi.loads_document('{"schema_version":1,"schema_version":1}')


def test_unknown_abi_key_fails_closed() -> None:
    """Unknown v1 policy cannot be ignored by older consumers."""
    document = c_abi.loads_document(_canonical_text())
    document["host_pointer_bits"] = 64
    changed = json.dumps(document)
    with pytest.raises(c_abi.CAbiValidationError, match=r"unknown=.*host_pointer_bits"):
        _ = c_abi.validate_text(changed)


def test_abi_layout_drift_fails_closed() -> None:
    """Pointer-width drift is a new ABI, not an in-place v1 mutation."""
    changed = _canonical_text().replace('"bits": 32,', '"bits": 64,', 1)
    with pytest.raises(c_abi.CAbiValidationError, match=r"pointer\.bits"):
        _ = c_abi.validate_text(changed)


def test_frontend_projection_matches_pinned_clang(tmp_path: Path) -> None:
    """Pinned Clang's parse target remains an exact executable projection."""
    _require_llvm()
    source = tmp_path / "empty.c"
    _ = source.write_text("int abi_probe;\n", encoding="utf-8")
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            str(c_abi_source.PINNED_CLANG),
            f"--target={c_abi.CLANG_TARGET}",
            "-std=c23",
            "-ffreestanding",
            "-S",
            "-emit-llvm",
            str(source),
            "-o",
            "-",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert f'target datalayout = "{c_abi.LLVM_DATA_LAYOUT}"' in completed.stdout
    assert f'target triple = "{c_abi.CLANG_TARGET}"' in completed.stdout


def test_accepted_abi_fixtures_are_clean_and_parse() -> None:
    """Admitted fixtures satisfy ABI preflight and the pinned parse target."""
    _require_llvm()
    projection = c_abi.canonical_projection()
    sources = tuple(sorted(ACCEPTED.glob("*.c")))
    assert {source.name for source in sources} == {
        "abi_language_surface.c",
        "abi_layout.c",
    }
    for source in sources:
        assert (
            c_abi_source.analyze_source(
                source,
                projection=projection,
            )
            == ()
        )
        # jig-ignore-next-line: indivisible reviewed identifier
        completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            [
                str(c_abi_source.PINNED_CLANG),
                f"--target={projection.clang_target}",
                "-std=c23",
                "-ffreestanding",
                "-fno-builtin",
                "-pedantic-errors",
                "-fsyntax-only",
                str(source),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )
        assert completed.returncode == 0, completed.stderr


def test_rejected_abi_fixtures_have_source_located_codes() -> None:
    """Each ABI exclusion has durable source-located regression evidence."""
    _require_llvm()
    projection = c_abi.canonical_projection()
    sources = tuple(sorted(REJECTED.glob("*.c")))
    assert {source.name for source in sources} == set(EXPECTED_REJECTIONS)
    for source in sources:
        diagnostics = c_abi_source.analyze_source(
            source,
            projection=projection,
        )
        assert diagnostics
        assert EXPECTED_REJECTIONS[source.name] in {
            diagnostic.code for diagnostic in diagnostics
        }
        assert all(diagnostic.path == source.resolve() for diagnostic in diagnostics)
        assert all(diagnostic.line > 0 for diagnostic in diagnostics)
        assert all(diagnostic.column > 0 for diagnostic in diagnostics)


def test_imported_forbidden_alias_is_diagnosed_at_source_use() -> None:
    """Included forbidden types are reported at the selected source use."""
    _require_llvm()
    source = (
        ROOT / "tests" / "tidy" / "plugin-rejected" / "abi_imported_forbidden_alias.c"
    )

    diagnostics = c_abi_source.analyze_source(source)

    assert diagnostics
    assert {diagnostic.code for diagnostic in diagnostics} == {
        c_abi_source.DIAGNOSTIC_INT128
    }
    expected_path = source.resolve()
    assert all(diagnostic.path == expected_path for diagnostic in diagnostics)


def test_manual_guest_validator_uses_abi_preflight() -> None:
    """The documented manual command rejects an ABI fixture before lowering."""
    _require_llvm()
    if not CLANG_TIDY.is_file():
        pytest.skip("repository-pinned clang-tidy is unavailable")
    accepted = ACCEPTED / "abi_layout.c"
    rejected = REJECTED / "abi_bit_field.c"
    # jig-ignore-next-line: indivisible reviewed identifier
    accepted_result = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [sys.executable, str(VALIDATOR), str(accepted)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    assert accepted_result.returncode == 0, accepted_result.stderr
    # jig-ignore-next-line: indivisible reviewed identifier
    rejected_result = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [sys.executable, str(VALIDATOR), str(rejected)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    assert rejected_result.returncode == 1
    assert c_abi_source.DIAGNOSTIC_BIT_FIELD in rejected_result.stderr


def test_invalid_guest_source_utf8_fails_closed(tmp_path: Path) -> None:
    """ABI preflight never asks Clang to reinterpret invalid source bytes."""
    _require_llvm()
    source = tmp_path / "invalid.c"
    _ = source.write_bytes(bytes((0x69, 0x6E, 0x74, 0x20, 0xFF, 0x3B)))
    with pytest.raises(c_abi_source.SourceAnalysisError, match="invalid guest-C UTF-8"):
        _ = c_abi_source.analyze_source(source)


def test_source_preflight_rejects_wrong_clang_version(tmp_path: Path) -> None:
    """The ABI AST cannot be supplied by an unpinned Clang implementation."""
    source = tmp_path / "clean.c"
    _ = source.write_text("int clean;\n", encoding="utf-8")
    with pytest.raises(
        c_abi_source.SourceAnalysisError, match="must report clang version"
    ):
        _ = c_abi_source.analyze_source(source, clang=Path(sys.executable))


def test_manual_validator_rejects_wrong_clang_tidy_version() -> None:
    """Reject ABI-incompatible clang-tidy binaries at configuration time."""
    _require_llvm()
    accepted = ACCEPTED / "abi_layout.c"
    result = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            sys.executable,
            str(VALIDATOR),
            "--clang-tidy",
            sys.executable,
            str(accepted),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    assert result.returncode == VALIDATOR_CONFIGURATION_ERROR
    assert WRONG_TIDY_VERSION in result.stderr


def test_missing_abi_manifest_fails_closed(tmp_path: Path) -> None:
    """A missing ABI authority is a validation error rather than a traceback."""
    missing = tmp_path / "missing-c-abi.json"
    with pytest.raises(c_abi.CAbiValidationError, match="failed to read C ABI"):
        _ = c_abi.load_document(missing)


@pytest.mark.parametrize("fault_type", [OSError, ValueError, TypeError, RuntimeError])
@pytest.mark.parametrize(
    "operation",
    (
        "parent_symlink",
        "parent_junction",
        "leaf_lstat",
        "leaf_symlink",
        "leaf_junction",
        "open",
        "fdopen",
        "fstat",
    ),
)
def test_c_abi_document_host_file_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
    operation: str,
) -> None:
    """Unexpected host filesystem errors cannot escape the ABI boundary."""
    source = tmp_path / "c-abi.json"
    _ = source.write_text(_canonical_text(), encoding="utf-8")
    if operation == "leaf_lstat":
        original_lstat = Path.lstat

        def fail_lstat(path: Path) -> os.stat_result:
            if path == source:
                raise fault_type("injected ABI lstat fault")
            return original_lstat(path)

        monkeypatch.setattr(Path, "lstat", fail_lstat)
    elif operation in {
        "parent_symlink",
        "parent_junction",
        "leaf_symlink",
        "leaf_junction",
    }:
        target = source.parent if operation.startswith("parent_") else source
        original = (
            Path.is_symlink if operation.endswith("symlink") else Path.is_junction
        )

        def fail_redirect(path: Path) -> bool:
            if path == target:
                raise fault_type("injected ABI redirect status fault")
            return original(path)

        monkeypatch.setattr(
            Path,
            "is_symlink" if operation.endswith("symlink") else "is_junction",
            fail_redirect,
        )
    elif operation == "open":
        original_open = os.open

        def fail_open(path: Path, flags: int) -> int:
            if path == source:
                raise fault_type("injected ABI open fault")
            return original_open(path, flags)

        monkeypatch.setattr(os, "open", fail_open)
    elif operation == "fdopen":

        def fail_fdopen(_descriptor: int, _mode: str) -> object:
            raise fault_type("injected ABI fdopen fault")

        monkeypatch.setattr(os, "fdopen", fail_fdopen)
    else:

        def fail_fstat(_descriptor: int) -> os.stat_result:
            raise fault_type("injected ABI fstat fault")

        monkeypatch.setattr(os, "fstat", fail_fstat)
    with pytest.raises(c_abi.CAbiValidationError, match="failed to read C ABI"):
        _ = c_abi.load_document(source)


@pytest.mark.parametrize("fault_type", [OSError, ValueError, TypeError, RuntimeError])
def test_c_abi_fdopen_failure_closes_owned_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """A failed ABI stream wrapper releases its opened file descriptor."""
    source = tmp_path / "c-abi.json"
    _ = source.write_text(_canonical_text(), encoding="utf-8")
    original_open = os.open
    opened: list[int] = []

    def track_open(path: Path, flags: int) -> int:
        descriptor = original_open(path, flags)
        if path == source:
            opened.append(descriptor)
        return descriptor

    def fail_fdopen(_descriptor: int, _mode: str) -> object:
        raise fault_type("injected ABI fdopen fault")

    monkeypatch.setattr(os, "open", track_open)
    monkeypatch.setattr(os, "fdopen", fail_fdopen)
    with pytest.raises(c_abi.CAbiValidationError, match="failed to read C ABI"):
        _ = c_abi.load_document(source)
    assert len(opened) == 1
    with pytest.raises(OSError):
        _ = os.fstat(opened[0])


@pytest.mark.parametrize("location", ["parent", "leaf"])
@pytest.mark.parametrize("operation", ["is_symlink", "is_junction"])
@pytest.mark.parametrize("receipt", [0, None, object()])
def test_c_abi_rejects_foreign_redirect_status_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    location: str,
    operation: str,
    receipt: object,
) -> None:
    """Only native redirect-status booleans may admit authority paths."""
    source = tmp_path / "c-abi.json"
    _ = source.write_text(_canonical_text(), encoding="utf-8")
    target = source if location == "leaf" else tmp_path
    native = getattr(Path, operation)

    def forged_redirect(path: Path) -> object:
        if path == target:
            return receipt
        return native(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, operation, forged_redirect)
        with pytest.raises(c_abi.CAbiValidationError, match="redirect"):
            _ = c_abi.load_document(source)


@pytest.mark.parametrize("phase", ["admitted", "opened", "after", "visible"])
def test_c_abi_rejects_foreign_file_status_without_field_hooks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    """Source identity may only come from native os.stat_result receipts."""
    source = tmp_path / "c-abi.json"
    _ = source.write_text(_canonical_text(), encoding="utf-8")

    class ForeignStat:
        @property
        def st_mode(self) -> object:
            raise AssertionError("foreign C ABI stat field evaluated")

    native_lstat = Path.lstat
    native_fstat = os.fstat
    lstat_calls = 0
    fstat_calls = 0

    def forged_lstat(path: Path) -> object:
        nonlocal lstat_calls
        if path == source:
            lstat_calls += 1
            if phase == "admitted" and lstat_calls == 1:
                return ForeignStat()
            if phase == "visible" and lstat_calls == 2:
                return ForeignStat()
        return native_lstat(path)

    def forged_fstat(fd: int) -> object:
        nonlocal fstat_calls
        fstat_calls += 1
        if phase == "opened" and fstat_calls == 1:
            return ForeignStat()
        if phase == "after" and fstat_calls == 2:
            return ForeignStat()
        return native_fstat(fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "lstat", forged_lstat)
        isolated.setattr(os, "fstat", forged_fstat)
        with pytest.raises(c_abi.CAbiValidationError, match="status"):
            _ = c_abi.load_document(source)


@pytest.mark.parametrize("descriptor", [False, True, -1, 0.0, "5"])
def test_c_abi_rejects_foreign_raw_descriptors_before_fdopen(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    descriptor: object,
) -> None:
    """A coerced or forged descriptor must never touch host FD operations."""
    source = tmp_path / "c-abi.json"
    _ = source.write_text(_canonical_text(), encoding="utf-8")
    wrapped: list[object] = []
    closed: list[object] = []

    monkeypatch.setattr(os, "open", lambda *_args, **_kwargs: descriptor)

    def forged_fdopen(fd: object, _mode: str) -> object:
        wrapped.append(fd)
        raise AssertionError("foreign descriptor passed to fdopen")

    monkeypatch.setattr(os, "fdopen", forged_fdopen)
    monkeypatch.setattr(os, "close", lambda fd: closed.append(fd))
    with pytest.raises(c_abi.CAbiValidationError, match="descriptor"):
        _ = c_abi.load_document(source)
    assert not wrapped
    assert not closed


def test_c_abi_rejects_foreign_stream_wrapper_and_releases_fd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign wrapper never gains authority or leaks its raw descriptor."""
    source = tmp_path / "c-abi.json"
    _ = source.write_text(_canonical_text(), encoding="utf-8")
    opened: list[int] = []
    native_open = os.open

    def track_open(path: Path, flags: int) -> int:
        fd = native_open(path, flags)
        opened.append(fd)
        return fd

    class ForeignStream:
        def __enter__(self) -> object:
            raise AssertionError("foreign ABI stream entered")

    monkeypatch.setattr(os, "open", track_open)
    monkeypatch.setattr(os, "fdopen", lambda *_args: ForeignStream())
    with pytest.raises(c_abi.CAbiValidationError, match="stream"):
        _ = c_abi.load_document(source)
    assert len(opened) == 1
    with pytest.raises(OSError):
        _ = os.fstat(opened[0])


@pytest.mark.parametrize("receipt_kind", ["str", "subclass"])
def test_c_abi_rejects_foreign_byte_snapshots_before_decoding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    receipt_kind: str,
) -> None:
    """Only exact native ABI bytes may reach the UTF-8 document decoder."""
    source = tmp_path / "c-abi.json"
    _ = source.write_text(_canonical_text(), encoding="utf-8")

    class ForeignBytes(bytes):
        def decode(self, *_args: object, **_kwargs: object) -> str:
            raise AssertionError("foreign C ABI bytes decoder executed")

    def forged_read(_path: Path) -> object:
        if receipt_kind == "str":
            return "{}"
        return ForeignBytes(b"{}")

    monkeypatch.setattr(c_abi, "_read_document_bytes", forged_read)
    with pytest.raises(c_abi.CAbiValidationError, match="bytes"):
        _ = c_abi.load_document(source)


def test_missing_guest_source_fails_closed(tmp_path: Path) -> None:
    """A vanished guest source is reported through the ABI error contract."""
    _require_llvm()
    missing = tmp_path / "missing.c"
    with pytest.raises(
        c_abi_source.SourceAnalysisError, match="failed to read guest C"
    ):
        _ = c_abi_source.analyze_source(missing)


@pytest.mark.parametrize("fault_type", [OSError, ValueError, TypeError, RuntimeError])
@pytest.mark.parametrize(
    "operation", ("lstat", "open", "fdopen", "fstat", "read", "post_lstat")
)
def test_guest_source_host_file_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
    operation: str,
) -> None:
    """Source descriptor admission must normalize unexpected host failures."""
    source = tmp_path / "input.c"
    _ = source.write_text("int value;\n", encoding="utf-8")
    if operation in {"lstat", "post_lstat"}:
        original_lstat = Path.lstat
        calls = 0

        def fail_lstat(path: Path) -> os.stat_result:
            nonlocal calls
            if path == source:
                calls += 1
                if operation == "lstat" or calls == 2:
                    raise fault_type("injected source lstat failure")
            return original_lstat(path)

        monkeypatch.setattr(Path, "lstat", fail_lstat)
    elif operation == "open":
        original_open = os.open

        def fail_open(path: Path, flags: int) -> int:
            if path == source:
                raise fault_type("injected source open failure")
            return original_open(path, flags)

        monkeypatch.setattr(os, "open", fail_open)
    elif operation == "fdopen":

        def fail_fdopen(_descriptor: int, _mode: str) -> object:
            raise fault_type("injected source fdopen failure")

        monkeypatch.setattr(os, "fdopen", fail_fdopen)
    elif operation == "fstat":

        def fail_fstat(_descriptor: int) -> os.stat_result:
            raise fault_type("injected source fstat failure")

        monkeypatch.setattr(os, "fstat", fail_fstat)
    else:

        def fail_read(*_arguments: object) -> object:
            raise fault_type("injected source read failure")

        monkeypatch.setattr(c_abi_source, "_snapshot_open_source", fail_read)
    with pytest.raises(
        c_abi_source.SourceAnalysisError, match="failed to read guest C"
    ):
        _ = c_abi_source._source_snapshot(source)


@pytest.mark.parametrize("fault_type", [OSError, ValueError, TypeError, RuntimeError])
def test_guest_source_fdopen_failure_closes_owned_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """A source stream wrapper failure must not leak its raw descriptor."""
    source = tmp_path / "input.c"
    _ = source.write_text("int value;\n", encoding="utf-8")
    original_open = os.open
    opened: list[int] = []

    def track_open(path: Path, flags: int) -> int:
        descriptor = original_open(path, flags)
        if path == source:
            opened.append(descriptor)
        return descriptor

    def fail_fdopen(_descriptor: int, _mode: str) -> object:
        raise fault_type("injected source fdopen failure")

    monkeypatch.setattr(os, "open", track_open)
    monkeypatch.setattr(os, "fdopen", fail_fdopen)
    with pytest.raises(c_abi_source.SourceAnalysisError):
        _ = c_abi_source._source_snapshot(source)
    assert len(opened) == 1
    with pytest.raises(OSError):
        _ = os.fstat(opened[0])


@pytest.mark.parametrize("fault_type", [OSError, ValueError, TypeError, RuntimeError])
@pytest.mark.parametrize("location", ["source", "clang"])
def test_guest_source_resolve_host_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
    location: str,
) -> None:
    """Path resolution errors are typed before Clang can use stale input."""
    source = tmp_path / "input.c"
    _ = source.write_text("int value;\n", encoding="utf-8")
    clang = tmp_path / "clang"
    target = source if location == "source" else clang
    original_resolve = Path.resolve

    def fail_resolve(path: Path, strict: bool = False) -> Path:
        if path == target:
            raise fault_type("injected source resolve failure")
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", fail_resolve)
    with pytest.raises(c_abi_source.SourceAnalysisError, match="resolve"):
        _ = c_abi_source.analyze_source(source, clang=clang)


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
@pytest.mark.parametrize("target", ["source", "clang"])
def test_guest_source_preflight_stat_host_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
    target: str,
) -> None:
    """Clang/source status exceptions cannot escape the tooling boundary."""
    source = tmp_path / "input.c"
    _ = source.write_text("int value;\n", encoding="utf-8")
    clang = tmp_path / "clang"
    _ = clang.write_bytes(b"fake clang")
    faulty = source if target == "source" else clang
    original_is_file = Path.is_file

    def fail_is_file(path: Path) -> bool:
        if path == faulty:
            raise fault_type("injected preflight status failure")
        return original_is_file(path)

    monkeypatch.setattr(Path, "is_file", fail_is_file)
    monkeypatch.setattr(
        c_abi_source, "_clang_identity", lambda _clang: "clang version 22.1.8"
    )
    with pytest.raises(c_abi_source.SourceAnalysisError, match="status"):
        c_abi_source._require_ast_inputs(source, clang)


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
@pytest.mark.parametrize("query", ["version", "ast"])
def test_guest_source_clang_transport_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
    query: str,
) -> None:
    """Host transport failures cannot turn into uncaught tool tracebacks."""
    source = tmp_path / "input.c"
    _ = source.write_text("int value;\n", encoding="utf-8")

    def fail_run(*_args: object, **_kwargs: object) -> object:
        raise fault_type("injected clang subprocess failure")

    monkeypatch.setattr(c_abi_source.sp, "run", fail_run)
    if query == "version":
        operation = lambda: c_abi_source._clang_identity(source)
    else:
        monkeypatch.setattr(c_abi_source, "_require_ast_inputs", lambda *_: None)
        operation = lambda: c_abi_source._run_ast(source, source, "target")
    with pytest.raises(c_abi_source.SourceAnalysisError, match="Clang"):
        _ = operation()


@pytest.mark.parametrize("query", ["version", "ast"])
@pytest.mark.parametrize("malformed", [None, b"not text", 42])
def test_guest_source_clang_nontext_receipts_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    query: str,
    malformed: object,
) -> None:
    """A successful exit code without decoded text is not valid AST evidence."""
    source = tmp_path / "input.c"
    _ = source.write_text("int value;\n", encoding="utf-8")
    monkeypatch.setattr(
        c_abi_source.sp,
        "run",
        lambda *_args, **_kwargs: sp.CompletedProcess(
            ["clang"], 0, stdout=malformed, stderr=""
        ),
    )
    if query == "version":
        operation = lambda: c_abi_source._clang_identity(source)
    else:
        monkeypatch.setattr(c_abi_source, "_require_ast_inputs", lambda *_: None)
        operation = lambda: c_abi_source._run_ast(source, source, "target")
    with pytest.raises(c_abi_source.SourceAnalysisError, match="Clang"):
        _ = operation()


@pytest.mark.parametrize("query", ["version", "ast"])
@pytest.mark.parametrize(
    "receipt_kind",
    [
        "foreign_result",
        "subclass_result",
        "boolean_status",
        "float_status",
        "text_status",
        "foreign_stdout",
        "foreign_stderr",
    ],
)
def test_guest_source_clang_rejects_forged_process_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    query: str,
    receipt_kind: str,
) -> None:
    """Only native Clang exit and text evidence may authorize source parsing."""
    source = tmp_path / "input.c"
    _ = source.write_text("int value;\n", encoding="utf-8")

    class ForgedReceipt:
        @property
        def returncode(self) -> object:
            raise AssertionError("foreign receipt property evaluated")

    class SubclassReceipt(sp.CompletedProcess[str]):
        pass

    class ForeignText(str):
        def __add__(self, _other: object) -> str:
            raise AssertionError("foreign stdout concatenation executed")

        def strip(self, _chars: str | None = None) -> str:
            raise AssertionError("foreign stderr formatter executed")

    if receipt_kind == "foreign_result":
        receipt: object = ForgedReceipt()
    else:
        constructor = (
            SubclassReceipt
            if receipt_kind == "subclass_result"
            else sp.CompletedProcess
        )
        status = cast(
            "int",
            {
                "boolean_status": False,
                "float_status": 0.0,
                "text_status": "0",
            }.get(receipt_kind, 0),
        )
        receipt = constructor(
            ["clang"],
            status,
            stdout=ForeignText("valid") if receipt_kind == "foreign_stdout" else "",
            stderr=ForeignText("invalid") if receipt_kind == "foreign_stderr" else "",
        )
    monkeypatch.setattr(c_abi_source.sp, "run", lambda *_a, **_kw: receipt)
    if query == "version":
        operation = lambda: c_abi_source._clang_identity(source)
    else:
        monkeypatch.setattr(c_abi_source, "_require_ast_inputs", lambda *_: None)
        operation = lambda: c_abi_source._run_ast(source, source, "target")
    with pytest.raises(c_abi_source.SourceAnalysisError, match="malformed Clang"):
        _ = operation()


@pytest.mark.parametrize("query", ["version", "ast"])
@pytest.mark.parametrize("fault_type", [OSError, ValueError, TypeError, RuntimeError])
def test_guest_source_clang_foreign_host_errors_never_format(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    query: str,
    fault_type: type[Exception],
) -> None:
    """A foreign host exception must retain its cause without hook invocation."""
    source = tmp_path / "input.c"
    _ = source.write_text("int value;\n", encoding="utf-8")

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("foreign host formatter executed")

    foreign = type("ForeignHostFault", (fault_type,), {"__str__": unsafe_str})
    fault = foreign("private foreign detail")

    def fail_run(*_a: object, **_kw: object) -> object:
        raise fault

    monkeypatch.setattr(c_abi_source.sp, "run", fail_run)
    if query == "version":
        operation = lambda: c_abi_source._clang_identity(source)
    else:
        monkeypatch.setattr(c_abi_source, "_require_ast_inputs", lambda *_: None)
        operation = lambda: c_abi_source._run_ast(source, source, "target")
    with pytest.raises(c_abi_source.SourceAnalysisError, match="Clang") as error:
        _ = operation()
    assert error.value.__cause__ is fault


@pytest.mark.parametrize("descriptor", [False, True, -1, 0.0, "4"])
def test_guest_source_rejects_non_native_open_descriptors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    descriptor: object,
) -> None:
    """A forged raw descriptor cannot reach fdopen or close another host fd."""
    source = tmp_path / "input.c"
    _ = source.write_text("int value;\n", encoding="utf-8")
    fdopen_calls: list[object] = []
    close_calls: list[object] = []

    monkeypatch.setattr(os, "open", lambda *_a, **_kw: descriptor)

    def unexpected_fdopen(fd: object, _mode: str) -> object:
        fdopen_calls.append(fd)
        raise AssertionError("forged descriptor passed to fdopen")

    monkeypatch.setattr(os, "fdopen", unexpected_fdopen)
    monkeypatch.setattr(os, "close", lambda fd: close_calls.append(fd))
    with pytest.raises(c_abi_source.SourceAnalysisError, match="descriptor"):
        _ = c_abi_source._source_snapshot(source)
    assert not fdopen_calls
    assert not close_calls


@pytest.mark.parametrize("phase", ["lstat", "first_fstat", "second_fstat"])
def test_guest_source_rejects_forged_stat_receipts_without_hooks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    """Foreign stat objects cannot masquerade as stable source identity."""
    source = tmp_path / "input.c"
    _ = source.write_text("int value;\n", encoding="utf-8")

    class ForgedStat:
        @property
        def st_mode(self) -> object:
            raise AssertionError("foreign stat hook evaluated")

    if phase == "lstat":
        monkeypatch.setattr(Path, "lstat", lambda self: ForgedStat())
    else:
        original_fstat = os.fstat
        calls = 0

        def forged_fstat(fd: int) -> os.stat_result | ForgedStat:
            nonlocal calls
            calls += 1
            if calls == (1 if phase == "first_fstat" else 2):
                return ForgedStat()
            return original_fstat(fd)

        monkeypatch.setattr(os, "fstat", forged_fstat)
    with pytest.raises(c_abi_source.SourceAnalysisError, match="status"):
        _ = c_abi_source._source_snapshot(source)


@pytest.mark.parametrize("receipt_kind", ["text", "subclass"])
def test_guest_source_rejects_non_native_read_bytes(
    tmp_path: Path,
    receipt_kind: str,
) -> None:
    """Source bytes must be native before snapshot identity is trusted."""
    source = tmp_path / "input.c"
    _ = source.write_bytes(b"int value;\n")

    class ForeignBytes(bytes):
        def decode(self, *_args: object, **_kwargs: object) -> str:
            raise AssertionError("foreign decoder executed")

    with source.open("rb") as real_stream:

        class ForgedRead:
            def fileno(self) -> int:
                return real_stream.fileno()

            def read(self) -> object:
                if receipt_kind == "subclass":
                    return ForeignBytes(b"int value;\n")
                return "int value;\n"

        with pytest.raises(c_abi_source.SourceAnalysisError, match="bytes"):
            _ = c_abi_source._snapshot_open_source(
                cast("BinaryIO", cast("object", ForgedRead())), source, source.lstat()
            )


def test_guest_source_rejects_foreign_fdopen_stream_without_entering_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged stream wrapper never gains source-read authority or leaks fds."""
    source = tmp_path / "input.c"
    _ = source.write_bytes(b"int value;\n")
    opened: list[int] = []
    original_open = os.open

    def track_open(path: Path, flags: int) -> int:
        fd = original_open(path, flags)
        opened.append(fd)
        return fd

    class ForeignStream:
        def __enter__(self) -> object:
            raise AssertionError("foreign stream hook evaluated")

    monkeypatch.setattr(os, "open", track_open)
    monkeypatch.setattr(os, "fdopen", lambda *_args: ForeignStream())
    with pytest.raises(c_abi_source.SourceAnalysisError, match="stream"):
        _ = c_abi_source._source_snapshot(source)
    assert len(opened) == 1
    with pytest.raises(OSError):
        _ = os.fstat(opened[0])


@pytest.mark.parametrize("descriptor", [False, 0.0, "0", -1])
def test_guest_source_rejects_foreign_stream_descriptors_before_fstat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    descriptor: object,
) -> None:
    """Source fileno must be native, never a coerced host handle."""
    source = tmp_path / "input.c"
    _ = source.write_bytes(b"int value;\n")

    class ForeignStream:
        def fileno(self) -> object:
            return descriptor

        def read(self) -> bytes:
            raise AssertionError("read before descriptor admission")

    def forbidden_fstat(_fd: object) -> os.stat_result:
        raise AssertionError("foreign descriptor reached fstat")

    monkeypatch.setattr(os, "fstat", forbidden_fstat)
    with pytest.raises(c_abi_source.SourceAnalysisError, match="descriptor"):
        _ = c_abi_source._snapshot_open_source(
            cast("BinaryIO", cast("object", ForeignStream())),
            source,
            source.lstat(),
        )


@pytest.mark.parametrize(
    "fault_type",
    [c_abi_source.SourceAnalysisError, c_abi.CAbiValidationError],
)
def test_guest_abi_cli_never_formats_foreign_validation_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fault_type: type[Exception],
) -> None:
    """CLI must not evaluate hooks on foreign validation error subclasses."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("foreign validation error formatter executed")

    foreign = type("ForeignAbiFailure", (fault_type,), {"__str__": unsafe_str})
    fault = foreign("unsafe private detail")

    def fail_projection() -> None:
        raise fault

    monkeypatch.setattr(c_abi, "canonical_projection", fail_projection)
    monkeypatch.setattr(sys, "argv", ["c_abi_source", "input.c"])
    assert c_abi_source.main() == 2
    captured = capsys.readouterr()
    assert "ForeignAbiFailure" in captured.err
    assert "unsafe private detail" not in captured.err
    assert not captured.out


def test_guest_abi_cli_native_validation_error_retains_details(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exact native ABI failures retain a useful diagnostic."""

    def fail_projection() -> None:
        raise c_abi.CAbiValidationError("invalid canonical ABI projection")

    monkeypatch.setattr(c_abi, "canonical_projection", fail_projection)
    monkeypatch.setattr(sys, "argv", ["c_abi_source", "input.c"])
    assert c_abi_source.main() == 2
    assert "invalid canonical ABI projection" in capsys.readouterr().err


def test_guest_source_utf8_failure_retains_native_decoder_cause(
    tmp_path: Path,
) -> None:
    """Rejected source text exposes the decoder as trusted failure evidence."""
    source = tmp_path / "invalid.c"
    _ = source.write_bytes(b"\xff")
    with pytest.raises(c_abi_source.SourceAnalysisError, match="UTF-8") as error:
        _ = c_abi_source.analyze_source(source)
    assert type(error.value.__cause__) is UnicodeDecodeError


def test_abi_preflight_rejects_source_rewrite_during_ast(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Clang AST must not be combined with stale diagnostic source bytes."""
    source = tmp_path / "changed.c"
    _ = source.write_text("int one;\n", encoding="utf-8")

    def rewrite_source(_path: Path, _clang: Path, _target: str) -> object:
        _ = (_path, _clang, _target)
        _ = source.write_text("int two;\n", encoding="utf-8")
        return {}

    monkeypatch.setattr(c_abi_source, "_run_ast", rewrite_source)
    with pytest.raises(c_abi_source.SourceAnalysisError, match="changed"):
        _ = c_abi_source.analyze_source(source)


def test_abi_preflight_rejects_same_byte_inode_swap_during_ast(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same-byte inode substitution is not proof of a stable AST source."""
    source = tmp_path / "source.c"
    content = "int one;\n"
    _ = source.write_text(content, encoding="utf-8")

    def swap_source(_path: Path, _clang: Path, _target: str) -> object:
        _ = (_path, _clang, _target)
        source.unlink()
        _ = source.write_text(content, encoding="utf-8")
        return {}

    monkeypatch.setattr(c_abi_source, "_run_ast", swap_source)
    with pytest.raises(c_abi_source.SourceAnalysisError, match="changed"):
        _ = c_abi_source.analyze_source(source)


def test_abi_document_rejects_symlinked_leaf(tmp_path: Path) -> None:
    """A linked canonical-looking JSON file is not ABI authority."""
    external = tmp_path / "outside.json"
    _ = external.write_text(_canonical_text(), encoding="utf-8")
    manifest = tmp_path / "c-abi-v1.json"
    manifest.symlink_to(external)
    with pytest.raises(c_abi.CAbiValidationError, match=r"regular|redirect"):
        _ = c_abi.load_document(manifest)


def test_abi_document_rejects_symlinked_directory(tmp_path: Path) -> None:
    """ABI authority cannot be borrowed through a linked parent directory."""
    external = tmp_path / "outside"
    external.mkdir()
    _ = (external / "c-abi-v1.json").write_text(_canonical_text(), encoding="utf-8")
    alias = tmp_path / "alias"
    alias.symlink_to(external, target_is_directory=True)
    with pytest.raises(c_abi.CAbiValidationError, match="redirect"):
        _ = c_abi.load_document(alias / "c-abi-v1.json")


def test_abi_document_rejects_oversized_regular_file(tmp_path: Path) -> None:
    """Oversized regular JSON must fail before parsing or allocating a tree."""
    manifest = tmp_path / "large.json"
    _ = manifest.write_bytes(b" " * ((1024 * 1024) + 1))
    with pytest.raises(c_abi.CAbiValidationError, match="byte limit"):
        _ = c_abi.load_document(manifest)


@pytest.mark.parametrize("redirect", ("source", "directory", "root"))
def test_manual_doom_discovery_rejects_redirects(redirect: str, tmp_path: Path) -> None:
    """Explicit recursive doom scanning must not accept redirected inputs."""
    doom = tmp_path / "doom"
    doom.mkdir()
    _ = (doom / "regular.c").write_text("int regular;\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    _ = (outside / "hidden.c").write_text("int hidden;\n", encoding="utf-8")
    if redirect == "source":
        (doom / "alias.c").symlink_to(outside / "hidden.c")
    elif redirect == "directory":
        (doom / "alias").symlink_to(outside, target_is_directory=True)
    else:
        _ = doom.rename(tmp_path / "moved")
        doom.symlink_to(outside, target_is_directory=True)
    with pytest.raises(manual_validator.InputError, match="redirect"):
        _ = manual_validator._validated_files([str(doom)])  # pyright: ignore[reportPrivateUsage]


def test_manual_doom_accepts_physical_nesting_and_explicit_alias(
    tmp_path: Path,
) -> None:
    """Ordinary nested sources and explicitly named source links still work."""
    nested = tmp_path / "doom" / "nested"
    nested.mkdir(parents=True)
    source = nested / "example.c"
    _ = source.write_text("int example;\n", encoding="utf-8")
    assert manual_validator._validated_files([str(tmp_path / "doom")]) == (source,)  # pyright: ignore[reportPrivateUsage]
    alias = tmp_path / "alias.c"
    alias.symlink_to(source)
    assert manual_validator._validated_files([str(alias)]) == (source,)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
def test_c_abi_foreign_host_failure_never_formats_exception(
    monkeypatch: pytest.MonkeyPatch, fault_type: type[Exception]
) -> None:
    """Disk admission faults stay typed without running foreign formatters."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("foreign ABI disk failure formatter executed")

    foreign = type("ForeignAbiDiskFault", (fault_type,), {"__str__": unsafe_str})
    fault = foreign("disk denied")

    def fail_read(_path: Path) -> bytes:
        raise fault

    monkeypatch.setattr(c_abi, "_read_document_bytes", fail_read)
    with pytest.raises(
        c_abi.CAbiValidationError, match="failed to read C ABI"
    ) as caught:
        _ = c_abi.load_document(ABI_PATH)
    assert caught.value.__cause__ is fault
    assert "ForeignAbiDiskFault" in str(caught.value)


def test_c_abi_foreign_json_parser_failure_never_formats_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A JSON decoder subclass cannot substitute execution for diagnostics."""

    class ForeignJsonFault(json.JSONDecodeError):
        def __str__(self) -> str:
            raise AssertionError("foreign ABI JSON decoder formatter executed")

    fault = ForeignJsonFault("bad JSON", "{}", 0)

    def fail_decode(*_args: object, **_kwargs: object) -> None:
        raise fault

    monkeypatch.setattr(c_abi.json, "loads", fail_decode)
    with pytest.raises(c_abi.CAbiValidationError, match="invalid JSON") as caught:
        _ = c_abi.loads_document("{}")
    assert caught.value.__cause__ is fault
    assert "ForeignJsonFault" in str(caught.value)


@pytest.mark.parametrize(
    "fault_type",
    [c_abi.CAbiValidationError, c_abi.target_profile.ProfileValidationError],
)
def test_c_abi_cli_never_formats_foreign_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fault_type: type[Exception],
) -> None:
    """The ABI validator exits one instead of invoking foreign error hooks."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("foreign ABI CLI failure formatter executed")

    foreign = type("ForeignAbiCliFault", (fault_type,), {"__str__": unsafe_str})
    fault = foreign("unsafe CLI error")

    def fail_projection() -> None:
        raise fault

    monkeypatch.setattr(c_abi, "canonical_projection", fail_projection)
    assert c_abi.main() == 1
    output = capsys.readouterr()
    assert not output.out
    assert "ForeignAbiCliFault" in output.err


@pytest.mark.parametrize(
    "case", ("partial", "foreign-count", "write-fault", "flush-fault", "foreign-flush")
)
def test_c_abi_cli_requires_delivered_summary(
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    """A valid ABI projection cannot certify success with a partial receipt."""

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

    projection = c_abi.canonical_projection()
    monkeypatch.setattr(c_abi, "canonical_projection", lambda: projection)
    monkeypatch.setattr(sys, "stdout", cast("TextIO", cast("object", FakeOutput())))
    assert c_abi.main() == 1


def test_c_abi_cli_requires_successful_flush(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A successful summary requires one full write and a flush."""

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

    projection = c_abi.canonical_projection()
    output = CapturingOutput()
    monkeypatch.setattr(c_abi, "canonical_projection", lambda: projection)
    monkeypatch.setattr(sys, "stdout", cast("TextIO", cast("object", output)))
    assert c_abi.main() == 0
    expected = f"{projection.abi_id} target={projection.target_profile} "
    expected += f"clang={projection.clang_target}\n"
    assert output.messages == [expected]
    assert output.flushes == 1


def test_c_abi_cli_failed_stderr_retains_failed_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed diagnostic stream cannot convert rejection into success."""

    class FailedStderr:
        def write(self, _message: str) -> None:
            raise OSError("output unavailable")

    def rejected_projection() -> None:
        raise c_abi.CAbiValidationError("invalid ABI")

    monkeypatch.setattr(c_abi, "canonical_projection", rejected_projection)
    monkeypatch.setattr(sys, "stderr", cast("TextIO", cast("object", FailedStderr())))
    assert c_abi.main() == 1


def test_c_abi_native_host_failure_retains_detail_and_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Trusted native disk failures retain their original useful diagnosis."""
    fault = PermissionError("ABI document read permission denied")

    def fail_read(_path: Path) -> bytes:
        raise fault

    monkeypatch.setattr(c_abi, "_read_document_bytes", fail_read)
    with pytest.raises(
        c_abi.CAbiValidationError, match="ABI document read permission denied"
    ) as caught:
        _ = c_abi.load_document(ABI_PATH)
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize("receipt", ["short", "boolean", "overlong", "bad-flush"])
def test_guest_abi_source_diagnostic_requires_complete_output(
    monkeypatch: pytest.MonkeyPatch,
    receipt: str,
) -> None:
    """A missing source diagnostic cannot count as a completed ABI check."""
    evidence = c_abi_source.AbiDiagnostic(
        code="MALBOLGE-ABI-001", column=1, line=1,
        message="unsupported bit field", path=Path("input.c"),
    )
    def injected_analysis(*_args: object, **_kwargs: object) -> tuple[c_abi_source.AbiDiagnostic, ...]:
        return (evidence,)

    monkeypatch.setattr(c_abi_source, "analyze_source", injected_analysis)

    class FailingStream:
        def write(self, message: str) -> object:
            if receipt == "short":
                return len(message) - 1
            if receipt == "boolean":
                return True
            if receipt == "overlong":
                return len(message) + 1
            return len(message)

        def flush(self) -> object:
            return False if receipt == "bad-flush" else None

    monkeypatch.setattr(sys, "stderr", FailingStream())
    with pytest.raises(c_abi_source.SourceAnalysisError, match="output"):
        _ = c_abi_source.validate_source(Path("input.c"))


def test_guest_abi_source_error_sink_failure_keeps_nonzero_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A broken stderr stream cannot mask a rejected canonical ABI."""

    def invalid_projection() -> None:
        raise c_abi_source.SourceAnalysisError("invalid source")

    class UnavailableStderr:
        def write(self, _message: str) -> None:
            raise OSError("stderr unavailable")

        def flush(self) -> None:
            raise AssertionError("failed write must not be flushed")

    monkeypatch.setattr(c_abi, "canonical_projection", invalid_projection)
    monkeypatch.setattr(sys, "argv", ["c_abi_source", "input.c"])
    monkeypatch.setattr(sys, "stderr", UnavailableStderr())
    assert c_abi_source.main() == 2


def test_guest_abi_source_help_requires_complete_delivery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged short help write cannot authorize exit zero."""

    class ShortStdout:
        def write(self, message: str) -> int:
            return len(message) - 1

        def flush(self) -> None:
            raise AssertionError("do not flush an incomplete help message")

    monkeypatch.setattr(sys, "argv", ["c_abi_source", "--help"])
    monkeypatch.setattr(sys, "stdout", ShortStdout())
    assert c_abi_source.main() == 2



def test_guest_abi_source_valid_help_flushes_before_zero_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Native completed help output retains the normal successful exit."""
    records: list[str] = []

    class CompleteStdout:
        def write(self, message: str) -> int:
            records.append(message)
            return len(message)

        def flush(self) -> None:
            records.append("flush")

    monkeypatch.setattr(sys, "argv", ["c_abi_source", "--help"])
    monkeypatch.setattr(sys, "stdout", CompleteStdout())
    with pytest.raises(SystemExit) as caught:
        _ = c_abi_source.main()
    assert caught.value.code == 0
    assert records and "usage:" in records[0]
    assert records[-1] == "flush"
