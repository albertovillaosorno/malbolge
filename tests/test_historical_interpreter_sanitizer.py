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
#   - Executable regression evidence for the historical sanitizer harness.
# - Must-Not:
#   - Normalize raw addresses or make historical memory errors normative.
# - Allows:
#   - Inputs: pinned source, Clang, manifest, and reviewed normalized evidence.
#   - Outputs: exact schema, identity, and reproduced result assertions.
#   - Side effects: temporary sanitizer build files removed by the harness.
# - Split-When:
#   - Split when another host sanitizer configuration gains its own evidence.
# - Merge-When:
#   - Merge when another suite owns the same end-to-end sanitizer boundary.
# - Summary:
#   - Reproduces clean and H-003 historical interpreter sanitizer outcomes.
# - Description:
#   - Verifies source identity and normalized ASan/UBSan findings.
# - Usage:
#   - Collected by the repository Python test suite.
# - Defaults:
#   - Tool absence skips execution; malformed or drifting evidence fails.
#

"""Historical interpreter sanitizer harness regression tests."""

from __future__ import annotations

import json
import os
import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, cast, override

import pytest

from scripts.validate import historical_interpreter_sanitizer as harness

if TYPE_CHECKING:
    from collections.abc import Callable

CASE_AUTHORITY = "CASES"
HISTORICAL_SOURCE_NAME = "main.c"
ALTERED_SOURCE = b"modified after verification"
EXPECTED_CASES = (
    "clean-interpreter-roundtrip",
    "empty-source-overread",
    "one-word-source-overread",
)


def test_sanitizer_manifest_and_source_identity_are_exact() -> None:
    """Manifest order and immutable source identity remain reviewed."""
    cases = harness.load_cases()
    assert tuple(case.identifier for case in cases) == EXPECTED_CASES
    source = harness.SOURCE.read_bytes()
    assert sha256(source).hexdigest() == harness.SOURCE_SHA256
    evidence = harness.load_evidence()
    assert evidence["schema_version"] == harness.SCHEMA_VERSION
    assert evidence["source_sha256"] == harness.SOURCE_SHA256


@pytest.mark.parametrize(
    "identifier",
    [
        "../escaped",
        "child/escaped",
        r"child\escaped",
        "C:escape",
        ".hidden",
        "NUL",
        "con.copy",
        "x" * 129,
    ],
)
def test_sanitizer_rejects_unsafe_case_ids_before_file_creation(
    identifier: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unchecked fixture IDs must not select filenames outside the sandbox."""
    document = {
        "schema_version": harness.SCHEMA_VERSION,
        "source_root": "tests/compatibility/specification",
        "cases": [
            {
                "id": identifier,
                "source_hex": "44",
                "input_hex": "",
            }
        ],
    }
    cases = tmp_path / "cases.json"
    _ = cases.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(harness, "CASES", cases)
    with pytest.raises(
        harness.SanitizerHarnessError,
        match="portable filename stem",
    ):
        _ = harness.load_cases()
    with pytest.raises(
        harness.SanitizerHarnessError,
        match="portable filename stem",
    ):
        _ = harness.SanitizerCase(
            identifier=identifier,
            input_bytes=b"",
            source_bytes=b"D",
        )


def test_sanitizer_rejects_case_insensitive_fixture_name_collision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Case-only aliases cannot overwrite one another on Windows hosts."""
    document = {
        "schema_version": harness.SCHEMA_VERSION,
        "source_root": "tests/compatibility/specification",
        "cases": [
            {"id": identifier, "source_hex": "44", "input_hex": ""}
            for identifier in ("roundtrip", "RoundTrip")
        ],
    }
    cases = tmp_path / "cases.json"
    _ = cases.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(harness, "CASES", cases)
    with pytest.raises(
        harness.SanitizerHarnessError,
        match="duplicate sanitizer case: RoundTrip",
    ):
        _ = harness.load_cases()


def test_sanitizer_case_allows_safe_portable_filename_stem() -> None:
    """Portable punctuation remains admissible in fixture names."""
    identifier = "case_2.part-b"
    case = harness.SanitizerCase(
        identifier=identifier,
        input_bytes=b"",
        source_bytes=b"D",
    )
    assert case.identifier == identifier


class UnprintableHostOSError(OSError):
    """A host adapter whose diagnostic cannot safely be rendered."""

    @override
    def __str__(self) -> str:
        raise AssertionError("host error text must not be formatted")


class UnprintableHostRuntimeError(RuntimeError):
    """An additional fault family with a hostile message adapter."""

    @override
    def __str__(self) -> str:
        raise AssertionError("host error text must not be formatted")


@pytest.mark.parametrize(
    "source_kind", ["cases", "evidence", "historical-source"]
)
@pytest.mark.parametrize(
    "fault_type",
    [
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
        UnprintableHostOSError,
        UnprintableHostRuntimeError,
    ],
)
def test_sanitizer_source_wrapper_failure_closes_owned_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_kind: str,
    fault_type: type[Exception],
) -> None:
    """Manifest, evidence, and historical source readers own failed wraps."""
    source = tmp_path / (
        "main.c" if source_kind == "historical-source" else f"{source_kind}.json"
    )
    _ = source.write_bytes(b"{}")
    if source_kind == "cases":
        monkeypatch.setattr(harness, "CASES", source)
    elif source_kind == "evidence":
        monkeypatch.setattr(harness, "EVIDENCE", source)
    else:
        monkeypatch.setattr(harness, "SOURCE", source)
        monkeypatch.setattr(harness, "is_supported", lambda: True)
        monkeypatch.setattr(harness, "_compiler_identity", lambda: None)
    native_open = os.open
    native_fdopen = os.fdopen
    opened: list[int] = []
    fault = fault_type("injected sanitizer source wrapper failure")

    def capture_open(path: Path, flags: int) -> int:
        descriptor = native_open(path, flags)
        if path == source:
            opened.append(descriptor)
        return descriptor

    def reject_fdopen(descriptor: int, mode: str) -> object:
        if descriptor in opened and mode == "rb":
            raise fault
        return native_fdopen(descriptor, mode)

    monkeypatch.setattr(os, "open", capture_open)
    monkeypatch.setattr(os, "fdopen", reject_fdopen)
    try:
        with pytest.raises(harness.SanitizerHarnessError) as caught:
            if source_kind == "cases":
                _ = harness.load_cases()
            elif source_kind == "evidence":
                _ = harness.load_evidence()
            else:
                _ = harness.run_harness()
        assert "host stream wrapper failed" in str(caught.value)
        assert caught.value.__cause__ is fault
        assert len(opened) == 1
        with pytest.raises(OSError, match=r"Bad file descriptor|Invalid handle"):
            _ = os.fstat(opened[0])
    finally:
        for descriptor in opened:
            try:
                os.close(descriptor)
            except OSError:
                pass


def test_sanitizer_evidence_rejects_invalid_utf8(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reviewed evidence encoding failure remains a typed harness error."""
    evidence = tmp_path / "evidence.json"
    _ = evidence.write_bytes(bytes((0x7B, 0xFF, 0x7D)))
    monkeypatch.setattr(harness, "EVIDENCE", evidence)
    with pytest.raises(harness.SanitizerHarnessError, match="cannot load"):
        _ = harness.load_evidence()


def test_sanitizer_evidence_rejects_duplicate_json_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reviewed sanitizer evidence rejects ambiguous JSON identities."""
    evidence = tmp_path / "evidence.json"
    _ = evidence.write_text(
        '{"schema_version":1,"schema_version":1}',
        encoding="utf-8",
        newline="\n",
    )
    monkeypatch.setattr(harness, "EVIDENCE", evidence)
    with pytest.raises(
        harness.SanitizerHarnessError,
        match="duplicate sanitizer JSON key: schema_version",
    ):
        _ = harness.load_evidence()


@pytest.mark.parametrize("authority", ["CASES", "EVIDENCE"])
def test_sanitizer_rejects_redirected_json_authority(
    authority: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An alias to an existing JSON authority is not physical evidence."""
    actual = tmp_path / "actual.json"
    _ = actual.write_text('{"schema_version":1}', encoding="utf-8")
    alias = tmp_path / "alias.json"
    _ = alias.symlink_to(actual)
    monkeypatch.setattr(harness, authority, alias)
    loader = (
        harness.load_cases
        if authority == CASE_AUTHORITY
        else harness.load_evidence
    )
    with pytest.raises(
        harness.SanitizerHarnessError, match=r"regular|redirect"
    ):
        _ = loader()


def test_sanitizer_rejects_redirected_json_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A regular leaf reached through a directory symlink is not admitted."""
    real = tmp_path / "real"
    real.mkdir()
    _ = (real / "evidence.json").write_text(
        '{"schema_version":1}',
        encoding="utf-8",
    )
    alias = tmp_path / "alias"
    _ = alias.symlink_to(real, target_is_directory=True)
    monkeypatch.setattr(harness, "EVIDENCE", alias / "evidence.json")
    with pytest.raises(harness.SanitizerHarnessError, match="redirect"):
        _ = harness.load_evidence()


def test_sanitizer_rejects_oversized_json_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """JSON input must be bounded before parsing and allocating its contents."""
    evidence = tmp_path / "evidence.json"
    _ = evidence.write_bytes(b" " * (harness.MAX_DOCUMENT_BYTES + 1))
    monkeypatch.setattr(harness, "EVIDENCE", evidence)
    with pytest.raises(harness.SanitizerHarnessError, match="byte limit"):
        _ = harness.load_evidence()


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO unavailable")
def test_sanitizer_rejects_fifo_json_without_blocking(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Untrusted evidence must never block waiting for a FIFO writer."""
    fifo = tmp_path / "evidence.json"
    mkfifo = cast("Callable[[Path], None] | None", getattr(os, "mkfifo", None))
    if mkfifo is None:
        pytest.skip("FIFO creation is unavailable")
    mkfifo(fifo)
    monkeypatch.setattr(harness, "EVIDENCE", fifo)
    with pytest.raises(harness.SanitizerHarnessError, match="regular"):
        _ = harness.load_evidence()


def test_sanitizer_rejects_replaced_json_between_stat_and_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even same-byte replacements cannot change an admitted JSON inode."""
    evidence = tmp_path / "evidence.json"
    replacement = tmp_path / "replacement.json"
    contents = '{"schema_version":1}'
    _ = evidence.write_text(contents, encoding="utf-8")
    _ = replacement.write_text(contents, encoding="utf-8")
    original_open = os.open

    def swap_before_open(path: Path, flags: int) -> int:
        if path == evidence:
            _ = replacement.replace(evidence)
        return original_open(path, flags)

    monkeypatch.setattr(os, "open", swap_before_open)
    monkeypatch.setattr(harness, "EVIDENCE", evidence)
    with pytest.raises(harness.SanitizerHarnessError, match="changed"):
        _ = harness.load_evidence()


def test_sanitizer_rejects_redirected_fixture_in_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even in-root source aliases must not substitute a reviewed fixture."""
    fixture_root = tmp_path / "fixtures"
    fixture_root.mkdir()
    real = fixture_root / "real.malbolge"
    _ = real.write_bytes(b"D")
    _ = (fixture_root / "alias.malbolge").symlink_to(real)
    cases = tmp_path / "cases.json"
    _ = cases.write_text(
        json.dumps({
            "schema_version": harness.SCHEMA_VERSION,
            "source_root": "fixtures",
            "cases": [
                {
                    "id": "alias",
                    "source": "alias.malbolge",
                    "input_hex": "",
                }
            ],
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(harness, "ROOT", tmp_path)
    monkeypatch.setattr(harness, "CASES", cases)
    with pytest.raises(
        harness.SanitizerHarnessError, match=r"regular|redirect"
    ):
        _ = harness.load_cases()


def test_sanitizer_rejects_redirected_fixture_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source directories must not redirect through symlink aliases."""
    real = tmp_path / "real"
    real.mkdir()
    _ = (real / "source.malbolge").write_bytes(b"D")
    _ = (tmp_path / "alias").symlink_to(real, target_is_directory=True)
    cases = tmp_path / "cases.json"
    _ = cases.write_text(
        json.dumps({
            "schema_version": harness.SCHEMA_VERSION,
            "source_root": "alias",
            "cases": [
                {"id": "test", "source": "source.malbolge", "input_hex": ""}
            ],
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(harness, "ROOT", tmp_path)
    monkeypatch.setattr(harness, "CASES", cases)
    with pytest.raises(harness.SanitizerHarnessError, match="redirect"):
        _ = harness.load_cases()


def test_sanitizer_rejects_redirected_historical_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The historical source digest cannot authorize a redirected source."""
    actual = tmp_path / "main.c"
    _ = actual.write_bytes(b"original historical source")
    alias = tmp_path / "alias.c"
    _ = alias.symlink_to(actual)
    monkeypatch.setattr(harness, "SOURCE", alias)
    monkeypatch.setattr(
        harness, "SOURCE_SHA256", sha256(actual.read_bytes()).hexdigest()
    )
    monkeypatch.setattr(harness, "is_supported", lambda: True)
    monkeypatch.setattr(harness, "_compiler_identity", lambda: None)
    with pytest.raises(
        harness.SanitizerHarnessError, match=r"regular|redirect"
    ):
        _ = harness.run_harness()


def _simulated_execute_case(
    executable: Path,
    work: Path,
    case: harness.SanitizerCase,
) -> dict[str, object]:
    assert executable.is_file()
    assert work.is_dir()
    return {"id": case.identifier}


def test_sanitizer_compiles_only_verified_historical_source_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A source rewrite after hashing must not change the compiler input."""
    trusted = b"historical interpreter source snapshot"
    original = tmp_path / HISTORICAL_SOURCE_NAME
    _ = original.write_bytes(trusted)
    runtime = tmp_path / "asan-runtime.dll"
    _ = runtime.write_bytes(b"runtime fixture")
    (tmp_path / "fixtures").mkdir()
    manifest = tmp_path / "cases.json"
    _ = manifest.write_text(
        json.dumps({
            "schema_version": harness.SCHEMA_VERSION,
            "source_root": "fixtures",
            "cases": [{"id": "snapshot", "source_hex": "44", "input_hex": ""}],
        }),
        encoding="utf-8",
    )
    for name, value in {
        "ROOT": tmp_path,
        "SOURCE": original,
        "CASES": manifest,
        "ASAN_RUNTIME": runtime,
        "SOURCE_SHA256": sha256(trusted).hexdigest(),
        "is_supported": lambda: True,
        "_compiler_identity": lambda: None,
    }.items():
        monkeypatch.setattr(harness, name, value)

    def fake_compile(
        command: tuple[str, ...], *, cwd: Path
    ) -> subprocess.CompletedProcess[bytes]:
        assert cwd == tmp_path
        assert str(original) not in command
        staged = Path(command[-4])
        assert staged.name == HISTORICAL_SOURCE_NAME
        assert staged.parent != tmp_path
        assert staged.read_bytes() == trusted
        _ = original.write_bytes(ALTERED_SOURCE)
        _ = Path(command[-1]).write_bytes(b"simulated executable")
        return subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr(harness, "_run", fake_compile)
    monkeypatch.setattr(harness, "_execute_case", _simulated_execute_case)
    result = harness.run_harness()
    assert result["cases"] == [{"id": "snapshot"}]
    assert original.read_bytes() == ALTERED_SOURCE


@pytest.mark.parametrize("root_kind", ("symlink", "regular-file"))
def test_sanitizer_harness_rejects_untrusted_temporary_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    root_kind: str,
) -> None:
    """Sanitizer builds never follow redirected or non-directory .temp roots."""
    root = tmp_path / "repository"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    temporary_root = root / ".temp"
    if root_kind == "symlink":
        try:
            temporary_root.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"directory links unsupported: {error}")
    else:
        _ = temporary_root.write_bytes(b"not a directory")

    built: list[Path] = []

    def fake_build(work: Path, *, source_bytes: bytes) -> Path:
        built.append(work)
        _ = (work / "unexpected-build.txt").write_bytes(source_bytes)
        return work / "sanitizer.exe"

    for attr, value in {
        "ROOT": root,
        "is_supported": lambda: True,
        "_compiler_identity": lambda: None,
        "_verify_source": lambda: b"trusted source",
        "_build": fake_build,
        "load_cases": lambda: (),
    }.items():
        monkeypatch.setattr(harness, attr, value)
    with pytest.raises(harness.SanitizerHarnessError, match="temporary root"):
        _ = harness.run_harness()
    assert not built
    assert not tuple(outside.iterdir())
    assert (
        temporary_root.is_symlink()
        if root_kind == "symlink"
        else temporary_root.is_file()
    )


def test_sanitizer_harness_rejects_foreign_workspace_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A misdirected TemporaryDirectory must not receive compiler outputs."""
    root = tmp_path / "repository"
    root.mkdir()
    (root / ".temp").mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    built: list[Path] = []

    class ForeignWorkspace:
        def __init__(self, *, prefix: str, dir: Path) -> None:
            assert prefix == "historical-sanitizer-"
            assert dir == root / ".temp"

        def __enter__(self) -> str:
            return str(outside)

        def __exit__(self, *_args: object) -> None:
            return None

    def fake_build(work: Path, *, source_bytes: bytes) -> Path:
        built.append(work)
        _ = (work / "unexpected-build.txt").write_bytes(source_bytes)
        return work / "sanitizer.exe"

    for attr, value in {
        "ROOT": root,
        "is_supported": lambda: True,
        "_compiler_identity": lambda: None,
        "_verify_source": lambda: b"trusted source",
        "_build": fake_build,
        "load_cases": lambda: (),
    }.items():
        monkeypatch.setattr(harness, attr, value)
    monkeypatch.setattr(harness.tempfile, "TemporaryDirectory", ForeignWorkspace)
    with pytest.raises(harness.SanitizerHarnessError, match="workspace"):
        _ = harness.run_harness()
    assert not built
    assert not tuple(outside.iterdir())


@pytest.mark.parametrize(
    ("exit_code", "stdout", "stderr"),
    [
        (False, b"clang version 22.1.8 mock\n", b""),
        (0.0, b"clang version 22.1.8 mock\n", b""),
        (0, "clang version 22.1.8 mock\n", b""),
        (0, b"clang version 22.1.8 mock\n", ""),
    ],
)
def test_sanitizer_compiler_identity_rejects_malformed_process_receipts(
    monkeypatch: pytest.MonkeyPatch,
    *,
    exit_code: object,
    stdout: object,
    stderr: object,
) -> None:
    """Compiler version evidence requires an exact native process receipt."""
    receipt = subprocess.CompletedProcess[bytes](
        (str(harness.CLANG), "--version"),
        cast("int", exit_code),
        stdout=cast("bytes", stdout),
        stderr=cast("bytes", stderr),
    )

    def forged_run(
        command: object, *, cwd: Path
    ) -> subprocess.CompletedProcess[bytes]:
        del command, cwd
        return receipt

    monkeypatch.setattr(harness, "_run", forged_run)
    with pytest.raises(harness.SanitizerHarnessError, match="process receipt"):
        # ruff: ignore[private-member-access]
        harness._compiler_identity()  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize(
    "receipt_parts",
    [
        (False, b"", b""),
        (0.0, b"", b""),
        (0, "", b""),
        (0, b"", ""),
    ],
)
def test_sanitizer_case_execution_rejects_malformed_process_receipts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    receipt_parts: tuple[object, object, object],
) -> None:
    """Forged process results cannot certify a clean sanitizer case."""
    exit_code, stdout, stderr = receipt_parts
    receipt = subprocess.CompletedProcess[bytes](
        (
            str(tmp_path / "sanitizer.exe"),
            str(tmp_path / "malformed-case.malbolge"),
        ),
        cast("int", exit_code),
        stdout=cast("bytes", stdout),
        stderr=cast("bytes", stderr),
    )

    def forged_run(
        *args: object, **kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        del args, kwargs
        return receipt

    monkeypatch.setattr(subprocess, "run", forged_run)
    case = harness.SanitizerCase(
        identifier="malformed-case", input_bytes=b"", source_bytes=b"D"
    )
    with pytest.raises(harness.SanitizerHarnessError, match="process receipt"):
        # ruff: ignore[private-member-access]
        _ = harness._execute_case(  # pyright: ignore[reportPrivateUsage]
            tmp_path / "sanitizer.exe", tmp_path, case
        )


@pytest.mark.parametrize("exit_code", [False, 0.0])
def test_sanitizer_build_rejects_malformed_process_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exit_code: object,
) -> None:
    """A forged successful Clang exit cannot certify a sanitizer build."""
    monkeypatch.setattr(harness, "ROOT", tmp_path)
    work = tmp_path / "work"
    work.mkdir()
    _ = (work / "malbolge-sanitized.exe").write_bytes(b"fake executable")
    runtime = tmp_path / "mock-runtime.dll"
    _ = runtime.write_bytes(b"mock runtime")
    monkeypatch.setattr(harness, "ASAN_RUNTIME", runtime)
    def forged_run(
        command: object, *, cwd: Path
    ) -> subprocess.CompletedProcess[bytes]:
        del cwd
        return subprocess.CompletedProcess[bytes](
            cast("tuple[str, ...]", command),
            cast("int", exit_code),
            stdout=b"",
            stderr=b"",
        )

    monkeypatch.setattr(harness, "_run", forged_run)
    with pytest.raises(harness.SanitizerHarnessError, match="process receipt"):
        # ruff: ignore[private-member-access]
        _ = harness._build(  # pyright: ignore[reportPrivateUsage]
            work, source_bytes=b"trusted historical source"
        )
    assert not (work / runtime.name).exists()


def test_sanitizer_cli_cannot_format_foreign_host_exception(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An untrusted OSError formatter cannot escape the CLI failure boundary."""
    fault = UnprintableHostOSError("unsafe host detail")

    def fail_evidence() -> harness.JsonObject:
        raise fault

    monkeypatch.setattr(harness, "_verified_harness", fail_evidence)
    monkeypatch.setattr(sys, "argv", ["historical-sanitizer"])
    assert harness.main() == 1
    assert type(fault).__name__ in capsys.readouterr().err


def test_sanitizer_harness_reproduces_reviewed_findings() -> None:
    """Pinned Clang reproduces clean output and both H-003 findings."""
    if not harness.is_supported():
        pytest.skip("pinned Windows sanitizer toolchain is unavailable")
    assert harness.run_harness() == harness.load_evidence()


_INVALID_WRITE_COUNTS = ("short", "overlong", "boolean", "missing")
_STAGED_MAIN_C = "main.c"
_STAGED_HEADER = "halloc_compat.h"
_STAGED_SHIM = "halloc_compat.c"
_STAGED_CASE = "short-write.malbolge"
_STAGED_SOURCE = b"source"


def _malformed_write_count(kind: str, length: int) -> int:
    """Simulate a defective filesystem write acknowledgement.

    Returns:
        An invalid count for a deliberately truncated payload.

    """
    results: dict[str, object] = {
        "short": length - 1,
        "overlong": length + 1,
        "boolean": True,
        "missing": None,
    }
    return cast("int", results[kind])


def _inject_bad_historical_write(
    monkeypatch: pytest.MonkeyPatch,
    *,
    filename: str,
    invalid_count: str,
) -> None:
    real_bytes = Path.write_bytes
    real_text = Path.write_text

    def bad_bytes(path: Path, content: bytes) -> int:
        if path.name == filename:
            _ = real_bytes(path, content[:-1])
            return _malformed_write_count(invalid_count, len(content))
        return real_bytes(path, content)

    def bad_text(
        path: Path,
        content: str,
        *,
        encoding: str,
        newline: str,
    ) -> int:
        if path.name == filename:
            _ = real_text(
                path, content[:-1], encoding=encoding, newline=newline
            )
            return _malformed_write_count(invalid_count, len(content))
        return real_text(path, content, encoding=encoding, newline=newline)

    monkeypatch.setattr(Path, "write_bytes", bad_bytes)
    monkeypatch.setattr(Path, "write_text", bad_text)


@pytest.mark.parametrize(
    "filename", [_STAGED_MAIN_C, _STAGED_HEADER, _STAGED_SHIM]
)
@pytest.mark.parametrize("invalid_count", list(_INVALID_WRITE_COUNTS))
def test_sanitizer_rejects_incomplete_build_file_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    filename: str,
    invalid_count: str,
) -> None:
    """No compiler runs after an incomplete historical C staging write."""
    monkeypatch.setattr(harness, "ROOT", tmp_path)
    monkeypatch.setattr(harness, "is_supported", lambda: True)
    monkeypatch.setattr(harness, "_compiler_identity", lambda: None)
    monkeypatch.setattr(harness, "_verify_source", lambda: _STAGED_SOURCE)

    def unexpected_compile(*args: object, **kwargs: object) -> None:
        pytest.fail(f"unverified C reached compiler: {len(args)} {len(kwargs)}")

    monkeypatch.setattr(harness, "_run", unexpected_compile)
    _inject_bad_historical_write(
        monkeypatch, filename=filename, invalid_count=invalid_count
    )
    with pytest.raises(harness.SanitizerHarnessError, match="write count"):
        _ = harness.run_harness()


@pytest.mark.parametrize("invalid_count", list(_INVALID_WRITE_COUNTS))
def test_sanitizer_rejects_incomplete_case_file_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_count: str,
) -> None:
    """No sanitizer process executes with an incomplete guest fixture."""
    monkeypatch.setattr(harness, "ROOT", tmp_path)
    monkeypatch.setattr(harness, "is_supported", lambda: True)
    monkeypatch.setattr(harness, "_compiler_identity", lambda: None)
    monkeypatch.setattr(harness, "_verify_source", lambda: _STAGED_SOURCE)

    def fake_build(work: Path, *, source_bytes: bytes) -> Path:
        assert work.is_dir()
        assert source_bytes == _STAGED_SOURCE
        return work / "simulated-sanitizer.exe"

    monkeypatch.setattr(harness, "_build", fake_build)
    monkeypatch.setattr(
        harness,
        "load_cases",
        lambda: (
            harness.SanitizerCase(
                identifier="short-write", input_bytes=b"", source_bytes=b"D"
            ),
        ),
    )

    def unexpected_process(*args: object, **kwargs: object) -> None:
        pytest.fail(
            f"unverified guest reached process: {len(args)} {len(kwargs)}"
        )

    monkeypatch.setattr(subprocess, "run", unexpected_process)
    _inject_bad_historical_write(
        monkeypatch, filename=_STAGED_CASE, invalid_count=invalid_count
    )
    with pytest.raises(harness.SanitizerHarnessError, match="write count"):
        _ = harness.run_harness()


@pytest.mark.parametrize(
    "receipt_args",
    [
        None,
        "clang --version",
        ["clang", "--version"],
        ("different-clang", "--version"),
        ("clang", True),
    ],
)
def test_sanitizer_compiler_identity_rejects_foreign_command_receipts(
    monkeypatch: pytest.MonkeyPatch, receipt_args: object
) -> None:
    """A fabricated success for different argv cannot identify pinned Clang."""
    completed = subprocess.CompletedProcess[bytes](
        cast("tuple[str, ...]", receipt_args),
        0,
        stdout=b"clang version 22.1.8 mock\n",
        stderr=b"",
    )
    monkeypatch.setattr(harness, "_run", lambda *_args, **_kwargs: completed)
    with pytest.raises(harness.SanitizerHarnessError, match="process receipt"):
        # ruff: ignore[private-member-access]
        harness._compiler_identity()  # pyright: ignore[reportPrivateUsage]


def test_sanitizer_build_rejects_forged_successful_clang_argv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unrelated successful process cannot certify sanitized executable."""
    monkeypatch.setattr(harness, "ROOT", tmp_path)
    work = tmp_path / "work"
    work.mkdir()
    executable = work / "malbolge-sanitized.exe"
    _ = executable.write_bytes(b"mock executable")
    runtime = tmp_path / "mock-runtime.dll"
    _ = runtime.write_bytes(b"mock runtime")
    monkeypatch.setattr(harness, "ASAN_RUNTIME", runtime)
    completed = subprocess.CompletedProcess[bytes](
        ("clang", "--version"), 0, stdout=b"", stderr=b""
    )
    monkeypatch.setattr(harness, "_run", lambda *_args, **_kwargs: completed)
    with pytest.raises(harness.SanitizerHarnessError, match="process receipt"):
        # ruff: ignore[private-member-access]
        _ = harness._build(  # pyright: ignore[reportPrivateUsage]
            work, source_bytes=b"trusted historical source"
        )
    assert not (work / runtime.name).exists()


def test_sanitizer_case_rejects_forged_successful_execution_argv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A clean result must correspond to this exact executable and fixture."""
    completed = subprocess.CompletedProcess[bytes](
        ("another-executable", "another-fixture"),
        0,
        stdout=b"not the guest",
        stderr=b"",
    )
    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs: completed)
    case = harness.SanitizerCase(
        identifier="correct-case", input_bytes=b"", source_bytes=b"D"
    )
    with pytest.raises(harness.SanitizerHarnessError, match="process receipt"):
        # ruff: ignore[private-member-access]
        _ = harness._execute_case(  # pyright: ignore[reportPrivateUsage]
            tmp_path / "sanitizer.exe", tmp_path, case
        )


@pytest.mark.parametrize("which", ["root", "workspace"])
@pytest.mark.parametrize("receipt", [None, 1, "directory", object()])
def test_sanitizer_temporary_directories_require_native_stat_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    which: str,
    receipt: object,
) -> None:
    """A forged stat object must never certify a temporary build location."""
    root = tmp_path / ".temp"
    root.mkdir()
    work = root / "historical-sanitizer-abcdefgh"
    work.mkdir()
    selected = root if which == "root" else work
    original = Path.lstat

    def fake_lstat(self: Path, *args: object, **kwargs: object) -> object:
        return receipt if self == selected else original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", fake_lstat)
    with pytest.raises(harness.SanitizerHarnessError, match="stat receipt"):
        if which == "root":
            harness._admit_temporary_root(root)  # pyright: ignore[reportPrivateUsage]
        else:
            # ruff: ignore[private-member-access]
            harness._admit_temporary_workspace(  # pyright: ignore[reportPrivateUsage]
                root, str(work)
            )


@pytest.mark.parametrize("which", ["root", "workspace"])
@pytest.mark.parametrize("method", ["is_symlink", "is_junction", "exists", "is_dir"])
@pytest.mark.parametrize("receipt", [None, 0, 1, "redirect"])
def test_sanitizer_temporary_directories_require_native_redirect_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    which: str,
    method: str,
    receipt: object,
) -> None:
    """Host predicates must return exact native booleans before admission."""
    root = tmp_path / ".temp"
    root.mkdir()
    work = root / "historical-sanitizer-abcdefgh"
    work.mkdir()
    selected = root if which == "root" else work
    original = getattr(Path, method)

    def forged_status(self: Path) -> object:
        return receipt if self == selected else original(self)

    monkeypatch.setattr(Path, method, forged_status)
    with pytest.raises(harness.SanitizerHarnessError, match="status receipt"):
        if which == "root":
            harness._admit_temporary_root(root)  # pyright: ignore[reportPrivateUsage]
        else:
            # ruff: ignore[private-member-access]
            harness._admit_temporary_workspace(  # pyright: ignore[reportPrivateUsage]
                root, str(work)
            )


@pytest.mark.parametrize("stage", ["creation", "root-stat", "workspace-stat"])
def test_sanitizer_temporary_directory_errors_preserve_cause_safely(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    """Foreign OS error string hooks must not execute in failure reporting."""

    class HostilePermissionError(PermissionError):
        def __str__(self) -> str:
            raise AssertionError("foreign host error formatter executed")

    root = tmp_path / ".temp"
    root.mkdir()
    work = root / "historical-sanitizer-abcdefgh"
    work.mkdir()
    fault = HostilePermissionError("sensitive host failure")
    original_mkdir = Path.mkdir
    original_lstat = Path.lstat

    def fake_mkdir(
        self: Path, mode: int = 0o777, parents: bool = False, exist_ok: bool = False
    ) -> None:
        if self == root:
            raise fault
        original_mkdir(self, mode=mode, parents=parents, exist_ok=exist_ok)

    def fake_lstat(self: Path, *args: object, **kwargs: object) -> object:
        if self == (work if stage == "workspace-stat" else root):
            raise fault
        return original_lstat(self, *args, **kwargs)

    if stage == "creation":
        monkeypatch.setattr(Path, "mkdir", fake_mkdir)
    else:
        monkeypatch.setattr(Path, "lstat", fake_lstat)
    with pytest.raises(
        harness.SanitizerHarnessError, match="HostilePermissionError"
    ) as failure:
        if stage == "workspace-stat":
            # ruff: ignore[private-member-access]
            harness._admit_temporary_workspace(  # pyright: ignore[reportPrivateUsage]
                root, str(work)
            )
        else:
            harness._admit_temporary_root(root)  # pyright: ignore[reportPrivateUsage]
    assert failure.value.__cause__ is fault


@pytest.mark.parametrize("which", ["root", "workspace"])
@pytest.mark.parametrize("method", ["exists", "is_dir"])
def test_sanitizer_rejects_false_directory_predicate_with_native_stat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, which: str, method: str
) -> None:
    """A forged negative predicate cannot contradict physical stat evidence."""
    root = tmp_path / ".temp"
    root.mkdir()
    work = root / "historical-sanitizer-abcdefgh"
    work.mkdir()
    selected = root if which == "root" else work
    original = getattr(Path, method)

    def lying_status(self: Path) -> bool:
        return False if self == selected else original(self)

    monkeypatch.setattr(Path, method, lying_status)
    with pytest.raises(harness.SanitizerHarnessError, match="physical directory"):
        if which == "root":
            harness._admit_temporary_root(root)  # pyright: ignore[reportPrivateUsage]
        else:
            # ruff: ignore[private-member-access]
            harness._admit_temporary_workspace(  # pyright: ignore[reportPrivateUsage]
                root, str(work)
            )


@pytest.mark.parametrize("mode", [None, True, 1.5, "dir", object()])
def test_sanitizer_rejects_foreign_stat_mode_inside_native_container(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: object
) -> None:
    """An exact stat_result wrapper alone cannot prove a directory mode."""
    root = tmp_path / ".temp"
    root.mkdir()
    fake = os.stat_result((cast("int", mode), 0, 0, 1, 0, 0, 0, 0, 0, 0))
    original = Path.lstat

    def forged_lstat(self: Path, *args: object, **kwargs: object) -> object:
        return fake if self == root else original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", forged_lstat)
    with pytest.raises(harness.SanitizerHarnessError, match="stat receipt"):
        harness._admit_temporary_root(root)  # pyright: ignore[reportPrivateUsage]


def test_sanitizer_source_error_does_not_format_foreign_os_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Historical source failures retain their cause without calling hooks."""

    class HostileOSError(OSError):
        def __str__(self) -> str:
            raise AssertionError("untrusted historical source error formatted")

    fault = HostileOSError("untrusted host receipt")

    def fail_read(*_args: object, **_kwargs: object) -> bytes:
        raise fault

    monkeypatch.setattr(harness, "_read_regular", fail_read)
    with pytest.raises(
        harness.SanitizerHarnessError, match="HostileOSError"
    ) as failure:
        harness._verify_source()  # pyright: ignore[reportPrivateUsage]
    assert failure.value.__cause__ is fault


def test_sanitizer_accepts_exact_native_clang_version_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The exact pinned argv and decoded version remain valid evidence."""
    command = (str(harness.CLANG), "--version")

    def fake_run(
        received: tuple[str, ...], *, cwd: Path
    ) -> subprocess.CompletedProcess[bytes]:
        assert received == command
        assert cwd == harness.ROOT
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=b"clang version 22.1.8 (reviewed)\n",
            stderr=b"",
        )

    monkeypatch.setattr(harness, "_run", fake_run)
    harness._compiler_identity()  # pyright: ignore[reportPrivateUsage]


def test_sanitizer_accepts_exact_clean_case_receipt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A native result from the requested executable and guest stays clean."""
    executable = tmp_path / "sanitizer.exe"
    case = harness.SanitizerCase(
        identifier="native-clean", input_bytes=b"input", source_bytes=b"D"
    )
    command = (str(executable), str(tmp_path / "native-clean.malbolge"))

    def fake_run(
        received: tuple[str, ...], **kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        assert received == command
        assert kwargs["input"] == case.input_bytes
        return subprocess.CompletedProcess(command, 0, stdout=b"ok", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = harness._execute_case(  # pyright: ignore[reportPrivateUsage]
        executable, tmp_path, case
    )
    assert result == {
        "id": case.identifier,
        "status": "clean",
        "stdout_hex": "6f6b",
        "findings": [],
    }


def test_sanitizer_preserves_native_directory_creation_failure_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exact native host failures retain their readable diagnostic and cause."""
    root = tmp_path / ".temp"
    original_mkdir = Path.mkdir
    fault = PermissionError("native creation denied")

    def fake_mkdir(
        self: Path, mode: int = 0o777, parents: bool = False, exist_ok: bool = False
    ) -> None:
        if self == root:
            raise fault
        original_mkdir(self, mode=mode, parents=parents, exist_ok=exist_ok)

    monkeypatch.setattr(Path, "mkdir", fake_mkdir)
    with pytest.raises(harness.SanitizerHarnessError, match="native creation denied") as failure:
        harness._admit_temporary_root(root)  # pyright: ignore[reportPrivateUsage]
    assert failure.value.__cause__ is fault
