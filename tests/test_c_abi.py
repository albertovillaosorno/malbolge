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
from typing import cast

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


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
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


@pytest.mark.parametrize("fault_type", [ValueError, RuntimeError])
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


def test_missing_guest_source_fails_closed(tmp_path: Path) -> None:
    """A vanished guest source is reported through the ABI error contract."""
    _require_llvm()
    missing = tmp_path / "missing.c"
    with pytest.raises(
        c_abi_source.SourceAnalysisError, match="failed to read guest C"
    ):
        _ = c_abi_source.analyze_source(missing)


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
