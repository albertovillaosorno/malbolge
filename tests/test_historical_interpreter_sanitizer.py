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

from hashlib import sha256
import json
import os
from typing import TYPE_CHECKING
from typing import cast

import pytest

from scripts.validate import historical_interpreter_sanitizer as harness

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

CASE_AUTHORITY = "CASES"
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


def test_sanitizer_harness_reproduces_reviewed_findings() -> None:
    """Pinned Clang reproduces clean output and both H-003 findings."""
    if not harness.is_supported():
        pytest.skip("pinned Windows sanitizer toolchain is unavailable")
    assert harness.run_harness() == harness.load_evidence()
